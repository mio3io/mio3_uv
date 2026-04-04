import bpy
import math
import gpu
from mathutils import Vector
from bpy.types import SpaceView3D
from bpy.props import BoolProperty, FloatProperty, EnumProperty, IntProperty
from gpu_extras.batch import batch_for_shader
from ..classes import Mio3UVOperator, UVIslandManager, UVIsland
from ..globals import get_preferences
from ..icons import icons

IslandList = list[UVIsland]
IslandGroups = list[IslandList]


class DrawState:
    def __init__(self):
        self.line_data = None
        self.arrow_data = None


class UV_OT_mio3_sort(Mio3UVOperator):
    bl_idname = "uv.mio3_sort"
    bl_label = "Sort"
    bl_description = "Rearrange islands based on coordinates in 3D space"
    bl_options = {"REGISTER", "UNDO"}

    def get_alignment_items(self, context):
        if self.align_uv == "X":
            return [
                ("TOP", "Top Align", "Top Align"),
                ("MIDDLE", "Middle Align", "Middle Align"),
                ("BOTTOM", "Bottom Align", "Bottom Align"),
            ]
        else:
            return [
                ("TOP", "Left Align", "Left Align"),
                ("MIDDLE", "Middle Align", "Middle Align"),
                ("BOTTOM", "Right Align", "Right Align"),
            ]

    def callback_grid_x(self, context):
        if self.grid_link:
            self["grid_y"] = self.grid_x
            self["grid_y_px"] = self.grid_x_px

    def callback_grid_y(self, context):
        if self.grid_link:
            self["grid_x"] = self.grid_y
            self["grid_x_px"] = self.grid_y_px

    method: EnumProperty(
        name="Sort Method",
        items=[
            ("AXIS", "Single Axis", ""),
            ("RADIAL", "Radial", ""),
            ("GRID", "Grid", ""),
            ("UV", "UV Space", ""),
        ],
    )
    aling_mode: EnumProperty(
        items=[
            ("STANDARD", "Standard", "Rearrange islands based on coordinates in 3D space"),
            ("FIXED", "Fixed Width", "Gridding island based on coordinates in 3D space"),
        ]
    )
    align_uv: EnumProperty(name="Align", items=[("X", "Align H", ""), ("Y", "Align V", "")], default="X")
    alignment: EnumProperty(name="Alignment", items=get_alignment_items, default=0)
    reverse: BoolProperty(name="Reverse Order", description="Reverse Order", default=False)
    axis: EnumProperty(name="3D Axis", items=[("AUTO", "Auto", ""), ("X", "X", ""), ("Y", "Y", ""), ("Z", "Z", "")])
    coordinate_space: EnumProperty(
        name="Coordinate Space",
        items=[
            ("WORLD", "World", "Based on world coordinates"),
            ("LOCAL", "Local", "Based on active object local coordinates"),
        ],
    )
    group_spacing: FloatProperty(name="Spacing", default=0.01, min=0.0, max=0.5, step=0.1, precision=3)
    item_spacing: FloatProperty(name="Spacing", default=0.01, min=0.0, max=0.5, step=0.1, precision=3)
    line_spacing: FloatProperty(name="Line Spacing", default=0.0, min=-0.5, max=0.5, step=0.1, precision=3)
    grid_x: FloatProperty(name="Grid Size X", default=0.125, min=0.01, step=0.1, precision=3, update=callback_grid_x)
    grid_y: FloatProperty(name="Grid Size Y", default=0.125, min=0.01, step=0.1, precision=3, update=callback_grid_y)
    grid_x_px: FloatProperty(name="Grid Size X", default=64, min=1, step=100, precision=1, update=callback_grid_x)
    grid_y_px: FloatProperty(name="Grid Size Y", default=64, min=1, step=100, precision=1, update=callback_grid_y)
    grid_units: EnumProperty(name="Units", items=[("RELATIVE", "Relative", "Relative"), ("PIXEL", "Pixel", "Pixel")])
    grid_link: BoolProperty(name="Grid Link", default=True)
    grid_divisions: IntProperty(
        name="Divisions",
        description="Number of grid divisions along the longer axis",
        default=10,
        min=2,
        max=50,
    )
    start_angle: FloatProperty(
        name="Start Angle(Clock)",
        description="Enter time (0-12). 3 o'clock is 0°, 6 is -90°, 9 is -180°, 12 is -270°",
        default=9,
        min=0,
        max=12,
        step=10,
        precision=2,
    )
    wrap_count: IntProperty(
        name="Wrap Count", description="Number of islands before wrapping", default=5, min=1, max=20
    )
    use_wrap: BoolProperty(name="Wrap", default=False)
    group_type: EnumProperty(
        name="Group",
        items=[
            ("NONE", "None", ""),
            ("SCALE", "UV Scale", ""),
            ("SIMILAR", "UV Similar", ""),
            ("DISTANCE", "UV Distance", ""),
            ("OBJECT", "Object", ""),
            ("MATERIAL", "Material", ""),
        ],
        default="NONE",
    )
    by_group: BoolProperty(name="By Group", default=False, options={"SKIP_SAVE"})

    WATCH_INTERVAL = 1.0
    GUIDE_LINE_LENGTH = 1000.0
    GUIDE_CIRCLE_SEGMENTS = 64
    GUIDE_CIRCLE_DIAMETER_RATIO = 1
    GUIDE_ARROW_SCALE = 0.1
    _handle_3d = None

    @property
    def start_angle_radian(self):
        return (3 - self.start_angle) * (math.pi / 6)

    @staticmethod
    def redraw(context=None):
        ctx = context or bpy.context
        window_manager = getattr(ctx, "window_manager", None)
        if window_manager is None:
            return

        for window in window_manager.windows:
            if window.screen:
                for area in window.screen.areas:
                    if area.type == "VIEW_3D":
                        area.tag_redraw()

    @classmethod
    def remove_handler(cls, context=None):
        if cls._handle_3d is not None:
            SpaceView3D.draw_handler_remove(cls._handle_3d, "WINDOW")
            cls._handle_3d = None
            cls.redraw(context)
        if bpy.app.timers.is_registered(cls.watch_operator):
            bpy.app.timers.unregister(cls.watch_operator)

    @classmethod
    def watch_operator(cls):
        context = bpy.context
        if cls._handle_3d is None:
            cls.remove_handler(context)
            return None

        obj = getattr(context, "active_object", None)
        if obj is None or obj.mode != "EDIT":
            cls.remove_handler(context)
            return None

        window_manager = getattr(context, "window_manager", None)
        if window_manager is None:
            cls.remove_handler(context)
            return None

        if window_manager.is_interface_locked:
            return cls.WATCH_INTERVAL

        operators = window_manager.operators
        last_operator_id = getattr(getattr(operators[-1], "bl_rna", None), "identifier", "") if operators else ""
        if last_operator_id != cls.__name__:
            cls.remove_handler(context)
            return None

        return cls.WATCH_INTERVAL

    def cancel(self, context):
        self.__class__.remove_handler(context)

    @staticmethod
    def draw_3d(draw_state, prefs):
        if draw_state.line_data is None and draw_state.arrow_data is None or not prefs.ui_guide:
            return

        line_shader = gpu.shader.from_builtin("POLYLINE_UNIFORM_COLOR")
        line_shader.uniform_float("viewportSize", gpu.state.viewport_get()[2:])
        line_shader.uniform_float("lineWidth", 2.0)
        arrow_shader = gpu.shader.from_builtin("UNIFORM_COLOR")

        if draw_state.line_data is not None:
            line_shader.bind()
            line_shader.uniform_float("color", prefs.ui_guide_col)
            batch = batch_for_shader(line_shader, "LINES", {"pos": draw_state.line_data})
            batch.draw(line_shader)
        if draw_state.arrow_data is not None:
            arrow_shader.bind()
            arrow_shader.uniform_float("color", prefs.ui_guide_col)
            batch = batch_for_shader(arrow_shader, "TRIS", {"pos": draw_state.arrow_data})
            batch.draw(arrow_shader)

    @staticmethod
    def create_arrow(
        tip: Vector,
        direction: Vector,
        size: float,
        up_hint: Vector | None = None,
        base_center: Vector | None = None,
    ):
        direction = direction.normalized()
        if direction.length_squared == 0:
            return None

        if up_hint is None or abs(direction.dot(up_hint.normalized())) > 0.999:
            up_hint = Vector((0.0, 0.0, 1.0))
            if abs(direction.dot(up_hint)) > 0.999:
                up_hint = Vector((1.0, 0.0, 0.0))

        side_a = direction.cross(up_hint).normalized()
        if side_a.length_squared == 0:
            return None
        side_b = direction.cross(side_a).normalized()

        if base_center is None:
            base_center = tip - direction * (size * 0.9)
        base_radius = size * 0.4
        base_segments = 16
        base_points = []
        for index in range(base_segments):
            angle = (math.tau * index) / base_segments
            radial_dir = side_a * math.cos(angle) + side_b * math.sin(angle)
            base_points.append(base_center + radial_dir * base_radius)

        faces = []
        for index in range(base_segments):
            faces.extend([tip, base_points[index], base_points[(index + 1) % base_segments]])

        for index in range(1, base_segments - 1):
            faces.extend([base_points[0], base_points[index], base_points[index + 1]])
        return faces

    def update_guide(self, context, island_manager: UVIslandManager):
        obj = context.active_object
        use_local = self.coordinate_space == "LOCAL"

        if self._draw_state is None:
            self._draw_state = DrawState()

        # 中心・矢印サイズ用にしか使用していない
        all_centers = [island.center_3d_world for island in island_manager.islands]
        bbox_min = Vector(tuple(min(center[i] for center in all_centers) for i in range(3)))
        bbox_max = Vector(tuple(max(center[i] for center in all_centers) for i in range(3)))
        center = (bbox_min + bbox_max) / 2
        bbox_extent = bbox_max - bbox_min
        arrow_size = max(max(bbox_extent), 0.001) * self.GUIDE_ARROW_SCALE

        basis_vectors = {
            "X": Vector((1.0, 0.0, 0.0)),
            "Y": Vector((0.0, 1.0, 0.0)),
            "Z": Vector((0.0, 0.0, 1.0)),
        }
        if use_local and obj is not None:
            rotation = obj.matrix_world.to_3x3().normalized()
            basis_vectors = {axis_name: (rotation @ vector).normalized() for axis_name, vector in basis_vectors.items()}

        if self.method == "RADIAL":
            plane = {"X": (1, 2), "Y": (0, 2), "Z": (0, 1)}[self.target_axis]
            radial_center = obj.matrix_world.translation if use_local and obj is not None else center
            arrow_size = arrow_size * 0.8  # 放射の場合はサイズ小さめ

            def plane_vec(cos_val, sin_val):
                return basis_vectors["XYZ"[plane[0]]] * cos_val + basis_vectors["XYZ"[plane[1]]] * sin_val

            def point_on_circle(angle):
                return radial_center + plane_vec(math.cos(angle), math.sin(angle)) * radius

            radius = max(max(bbox_extent), 0.001) * self.GUIDE_CIRCLE_DIAMETER_RATIO * 0.5

            circle_points = []
            for index in range(self.GUIDE_CIRCLE_SEGMENTS):
                circle_points.append(point_on_circle(index / self.GUIDE_CIRCLE_SEGMENTS * math.tau))
                circle_points.append(point_on_circle((index + 1) / self.GUIDE_CIRCLE_SEGMENTS * math.tau))

            angle = self.start_angle_radian
            sign = -1 if self.reverse else 1
            angle_step = min(arrow_size / max(radius, 0.001), math.pi / 3)
            start_point = point_on_circle(angle)
            base_angle = angle + angle_step * 0.6 * sign
            tip_angle = angle + angle_step * 1.6 * sign
            base_center = point_on_circle(base_angle)
            tip = point_on_circle(tip_angle)

            bar_offset = plane_vec(math.cos(angle), math.sin(angle)) * (radius * 0.15)  # バーの長さ
            circle_points.append(start_point - bar_offset)
            circle_points.append(start_point + bar_offset)

            direction = (tip - base_center).normalized()
            self._draw_state.line_data = circle_points
            plane_normal = basis_vectors[self.target_axis]
            self._draw_state.arrow_data = self.create_arrow(
                tip,
                direction,
                arrow_size,
                plane_normal,
                base_center,
            )

        elif self.method == "AXIS":
            axis_vector = basis_vectors[self.target_axis]
            up_hint = basis_vectors["Y"] if self.target_axis == "X" else basis_vectors["X"]
            sign = -1.0 if self.target_axis == "Z" else 1.0
            direction = axis_vector * (-sign if self.reverse else sign)

            self._draw_state.line_data = [
                center - axis_vector * self.GUIDE_LINE_LENGTH,
                center + axis_vector * self.GUIDE_LINE_LENGTH,
            ]
            self._draw_state.arrow_data = self.create_arrow(
                center + direction * arrow_size,
                direction,
                arrow_size,
                up_hint,
            )

        else:
            self._draw_state.line_data = None
            self._draw_state.arrow_data = None

        self.redraw(context)

    def invoke(self, context, event):
        cls = self.__class__
        prefs = get_preferences()

        if self.aling_mode == "FIXED" and self.grid_units == "PIXEL":
            if context.area.type == "IMAGE_EDITOR":
                space = context.area.spaces.active
                if space.image:
                    return self.execute(context)
            self.report({"WARNING"}, "Please display an image if you want to use pixel units")
            return {"CANCELLED"}

        if cls._handle_3d is not None:
            cls.remove_handler(context)

        self._draw_state = DrawState()
        if prefs.ui_guide:
            cls._handle_3d = SpaceView3D.draw_handler_add(
                self.draw_3d, (self._draw_state, prefs), "WINDOW", "POST_VIEW"
            )
            bpy.app.timers.register(cls.watch_operator, first_interval=cls.WATCH_INTERVAL)

        return self.execute(context)

    def execute(self, context):
        self.start_time()
        prefs = get_preferences()
        objects = self.get_selected_objects(context)

        use_uv_select_sync = context.tool_settings.use_uv_select_sync

        self.by_group = self.aling_mode == "FIXED"

        grid_x = None
        if self.aling_mode == "FIXED" and self.grid_units == "PIXEL":
            if context.area.type == "IMAGE_EDITOR":
                space = context.area.spaces.active
                if space.image:
                    grid_x = self.grid_x_px / space.image.size[0]
                    grid_y = self.grid_y_px / space.image.size[1]
            if not grid_x:
                self.remove_handler(context)
                self.report({"WARNING"}, "Please display an image if you want to use pixel units")
                return {"CANCELLED"}
        else:
            grid_x = self.grid_x
            grid_y = self.grid_y

        self.calc_grid_x = grid_x
        self.calc_grid_y = grid_y

        island_manager = UVIslandManager(objects, sync=use_uv_select_sync)
        if not island_manager.islands:
            self.remove_handler(context)
            return {"CANCELLED"}

        if self.method != "UV":
            island_manager.set_orientation_mode(self.coordinate_space)

        if self.method == "RADIAL":
            self.sort_radial(island_manager)
        elif self.method == "UV":
            self.sort_uv_space(island_manager)
        elif self.method == "GRID":
            self.sort_grid(island_manager)
        else:
            self.sort_axis(island_manager)

        groups = self.find_groups(island_manager)
        if self.by_group:
            for group in groups:
                self.align_groups([group])
        else:
            self.align_groups(groups)

        if prefs.ui_guide:
            self.update_guide(context, island_manager)

        island_manager.update_uvmeshes(True)

        self.print_time()
        return {"FINISHED"}

    def find_groups(self, island_manager: UVIslandManager):
        groups = []
        if self.group_type == "NONE":
            return [island_manager.islands]
        elif self.group_type == "OBJECT":
            for oi in island_manager.collections:
                obj_islands = [island for island in island_manager.islands if island.obj_info == oi]
                if obj_islands:
                    groups.append(obj_islands)
            groups.sort(key=lambda x: x[0].obj.name, reverse=self.reverse)
        elif self.group_type == "DISTANCE":

            def distance(point1, point2=(0, 0)):
                return math.sqrt((point1[0] - point2[0]) ** 2 + (point1[1] - point2[1]) ** 2)

            sorted_islands = sorted(island_manager.islands, key=lambda island: distance(island.center))
            groups = []
            current_group = []
            prev_distance = distance(sorted_islands[0].center)
            for island in sorted_islands:
                current_distance = distance(island.center)
                if current_distance - prev_distance > 0.001:
                    groups.append(current_group)
                    current_group = []
                current_group.append(island)
                prev_distance = current_distance
            if current_group:
                groups.append(current_group)
            groups.sort(key=lambda x: distance(x[0].center), reverse=self.reverse)
        elif self.group_type == "MATERIAL":

            def get_island_material(island):
                if not island.faces:
                    return None

                material_count = {}
                for face in island.faces:
                    material_index = face.material_index
                    obj = island.obj
                    if material_index < len(obj.material_slots):
                        material = obj.material_slots[material_index].material
                        material_count[material] = material_count.get(material, 0) + 1

                if not material_count:
                    return None

                return max(material_count, key=material_count.get)

            mat_groups = {}
            mat_islands = {}
            for island in island_manager.islands:
                material = get_island_material(island)
                mat_islands[island] = material
                mat_groups.setdefault(material, []).append(island)
            groups = list(mat_groups.values())
            groups.sort(key=lambda x: mat_islands[x[0]].name if mat_islands[x[0]] else "", reverse=self.reverse)
        elif self.group_type == "SIMILAR":

            def get_island_uv_count(island):
                return sum(len(face.loops) for face in island.faces)

            def get_island_edge_count(island):
                return len({edge for face in island.faces for edge in face.edges})

            def is_similar(island1, island2):
                if len(island1.faces) != len(island2.faces):
                    return False
                if get_island_uv_count(island1) != get_island_uv_count(island2):
                    return False
                if get_island_edge_count(island1) != get_island_edge_count(island2):
                    return False
                return True

            groups = []
            for island in island_manager.islands:
                found_group = False
                for group in groups:
                    if is_similar(island, group[0]):
                        group.append(island)
                        found_group = True
                        break
                if not found_group:
                    groups.append([island])
            groups.sort(key=lambda x: len(x[0].faces), reverse=self.reverse)
        elif self.group_type == "SCALE":

            def get_island_scale(island):
                return max(island.width, island.height)

            scale_threshold = 0.2  # 20% 以内
            groups = []
            for island in island_manager.islands:
                island_scale = get_island_scale(island)
                found_group = False
                for group in groups:
                    group_scale = get_island_scale(group[0])
                    scale_difference = abs(island_scale - group_scale) / max(island_scale, group_scale)
                    if scale_difference <= scale_threshold:
                        group.append(island)
                        found_group = True
                        break
                if not found_group:
                    groups.append([island])
            groups.sort(key=lambda x: get_island_scale(x[0]), reverse=self.reverse)
        return groups

    def sort_uv_space(self, island_manager: UVIslandManager):
        self.target_axis = self.axis if self.axis in {"X", "Y"} else island_manager.get_axis_uv()

        def sort_func(island):
            axis_index = {"X": 0, "Y": 1}[self.target_axis]
            return island.center[axis_index]

        if self.target_axis == "Y":
            island_manager.sort_all_islands(key=sort_func, reverse=not self.reverse)
        else:
            island_manager.sort_all_islands(key=sort_func, reverse=self.reverse)

    def sort_axis(self, island_manager: UVIslandManager):
        self.target_axis = self.axis if self.axis != "AUTO" else island_manager.get_axis_3d()
        axis_orders = {
            "X": ["+X", "+Y", "-Z"],
            "Y": ["+Y", "+X", "-Z"],
            "Z": ["-Z", "+X", "+Y"],
        }
        sort_order = axis_orders[self.target_axis]

        def sort_func(island):
            return tuple(
                island.center_3d["XYZ".index(axis[-1])] * (-1 if axis.startswith("-") else 1) for axis in sort_order
            )

        island_manager.sort_all_islands(key=sort_func, reverse=self.reverse)

    def sort_radial(self, island_manager: UVIslandManager):
        all_centers = [island.center_3d for island in island_manager.islands]
        min_coords = Vector(tuple(min(center[i] for center in all_centers) for i in range(3)))
        max_coords = Vector(tuple(max(center[i] for center in all_centers) for i in range(3)))
        axis_widths = max_coords - min_coords
        if self.axis == "AUTO":
            self.target_axis = min(zip(("X", "Y", "Z"), axis_widths), key=lambda item: item[1])[0]
        else:
            self.target_axis = self.axis

        if self.coordinate_space == "LOCAL":
            center_3d = Vector((0.0, 0.0, 0.0))
        else:
            center_3d = sum(all_centers, Vector()) / len(all_centers)

        start_angle_radian = self.start_angle_radian

        def sort_func(island):
            if self.target_axis == "X":
                relative_pos = Vector((island.center_3d.y, island.center_3d.z)) - Vector((center_3d.y, center_3d.z))
            elif self.target_axis == "Y":
                relative_pos = Vector((island.center_3d.x, island.center_3d.z)) - Vector((center_3d.x, center_3d.z))
            else:
                relative_pos = Vector((island.center_3d.x, island.center_3d.y)) - Vector((center_3d.x, center_3d.y))
            angle = math.atan2(relative_pos.y, relative_pos.x)
            adjusted_angle = (angle - start_angle_radian) % (2 * math.pi)
            return adjusted_angle

        island_manager.sort_all_islands(key=sort_func, reverse=self.reverse)

    def sort_grid(self, island_manager: UVIslandManager):
        all_centers = [island.center_3d for island in island_manager.islands]
        min_coords = Vector(tuple(min(center[i] for center in all_centers) for i in range(3)))
        max_coords = Vector(tuple(max(center[i] for center in all_centers) for i in range(3)))
        axis_widths = max_coords - min_coords
        if self.axis == "AUTO":
            self.target_axis = min(zip(("X", "Y", "Z"), axis_widths), key=lambda item: item[1])[0]
        else:
            self.target_axis = self.axis

        divisions = max(self.grid_divisions, 1)

        def build_axis_ranks(axis_index, reverse=False):
            sorted_islands = sorted(
                island_manager.islands,
                key=lambda island: island.center_3d[axis_index],
                reverse=reverse,
            )
            if not sorted_islands:
                return {}

            axis_span = max(axis_widths[axis_index], 0.0)
            expected_step = axis_span / max(divisions - 1, 1)
            axis_tolerance = max(min(expected_step * 0.25, max(axis_span, 1.0) * 0.25), 1e-6)
            ranks = {}
            current_rank = 0
            cluster_center = sorted_islands[0].center_3d[axis_index]
            ranks[sorted_islands[0]] = current_rank

            for island in sorted_islands[1:]:
                value = island.center_3d[axis_index]
                if abs(value - cluster_center) > axis_tolerance:
                    current_rank += 1
                    cluster_center = value
                else:
                    cluster_center = (cluster_center + value) * 0.5
                ranks[island] = current_rank

            return ranks

        if self.target_axis == "Y":
            row_axis, col_axis = 2, 0
        elif self.target_axis == "Z":
            row_axis, col_axis = 1, 0
        else:
            row_axis, col_axis = 2, 1

        row_ranks = build_axis_ranks(row_axis, reverse=True)
        col_ranks = build_axis_ranks(col_axis)

        def sort_func(island):
            return (row_ranks[island], col_ranks[island], -island.center_3d[row_axis], island.center_3d[col_axis])

        island_manager.sort_all_islands(key=sort_func, reverse=self.reverse)

    def align_groups(self, groups: list[IslandList]):
        all_islands = [island for group in groups for island in group]
        all_min = Vector(
            (min(island.min_uv[0] for island in all_islands), min(island.min_uv[1] for island in all_islands))
        )
        all_max = Vector(
            (max(island.max_uv[0] for island in all_islands), max(island.max_uv[1] for island in all_islands))
        )

        offset = Vector((all_min.x, all_max.y))
        spacing = 0 if self.aling_mode == "FIXED" else self.group_spacing

        for i, group in enumerate(groups):
            group_end = self.align_items(group, offset)
            if self.align_uv == "X":
                offset.x = group_end.x + spacing
            else:
                offset.y = group_end.y - spacing

    def align_items(self, islands: IslandList, group_offset: Vector):
        offset = group_offset.copy()
        spacing = 0 if self.aling_mode == "FIXED" else self.item_spacing
        line_spacing = self.line_spacing

        row_size = Vector((0, 0))
        row_start = offset.copy()
        items_in_row = 0
        row_islands = []

        max_x = offset.x
        min_y = offset.y

        for island in islands:
            original_size = Vector((island.width, island.height))
            if self.aling_mode == "FIXED":
                island_size = Vector((self.calc_grid_x, self.calc_grid_y))
            else:
                if self.align_uv == "X":
                    island_size = Vector((island.width + spacing, island.height))
                else:
                    island_size = Vector((island.width, island.height + spacing))

            # Wrap check
            if self.use_wrap and items_in_row >= self.wrap_count:
                self.align_row(row_islands, row_start, row_size)
                row_islands = []

                if self.align_uv == "X":
                    offset.x = group_offset.x
                    offset.y -= row_size.y + line_spacing
                    row_size.y = 0
                else:
                    offset.y = group_offset.y
                    offset.x += row_size.x + line_spacing
                    row_size.x = 0
                items_in_row = 0
                row_start = offset.copy()

            if self.align_uv == "X":
                offset.x += island_size.x
                row_size.y = max(row_size.y, island_size.y)
                max_x = max(max_x, offset.x)
            else:
                offset.y -= island_size.y
                row_size.x = max(row_size.x, island_size.x)
                min_y = min(min_y, offset.y)

            row_islands.append((island, island_size, original_size))
            items_in_row += 1

        if row_islands:
            self.align_row(row_islands, row_start, row_size)

        if self.align_uv == "X":
            group_end = Vector((max_x, group_offset.y))
        else:
            group_end = Vector((group_offset.x, min_y))
        return group_end

    def align_row(self, row_islands: list[tuple[UVIsland, Vector, Vector]], row_start: Vector, row_size: Vector):
        max_height = max(original_size.y for _, _, original_size in row_islands)

        for island, island_size, original_size in row_islands:
            if self.align_uv == "X":
                if self.alignment == "BOTTOM":
                    island_offset = Vector((row_start.x, row_start.y - row_size.y + original_size.y))
                elif self.alignment == "MIDDLE":
                    island_offset = Vector((row_start.x, row_start.y - (max_height - original_size.y) / 2))
                else:
                    island_offset = Vector((row_start.x, row_start.y))
            else:
                if self.alignment == "BOTTOM":
                    island_offset = Vector((row_start.x + row_size.x - original_size.x, row_start.y))
                elif self.alignment == "MIDDLE":
                    island_offset = Vector((row_start.x + (row_size.x - original_size.x) / 2, row_start.y))
                else:
                    island_offset = Vector((row_start.x, row_start.y))

            island_offset -= Vector((island.min_uv[0], island.max_uv[1]))
            island.move(island_offset)

            if self.align_uv == "X":
                row_start.x += island_size.x
            else:
                row_start.y -= island_size.y

    def draw(self, context):
        layout = self.layout

        layout.row().prop(self, "aling_mode", text="Align Mode", expand=True)
        layout.separator()

        row_method = layout.row()
        row_method.label(text="Sort Method")
        row_method.prop(self, "method", text="")

        if self.method == "RADIAL":
            row_sub = layout.row()
            row_sub.label(text="Start Angle (Clock)")
            row_sub.alignment = "RIGHT"
            row_sub.scale_x = 3
            row_sub.prop(self, "start_angle", text="")
            row_sub.scale_x = 1
            row_sub.label(text="Hours")
        if self.method == "GRID":
            row_sub = layout.row()
            row_sub.label(text="Divisions")
            row_sub.prop(self, "grid_divisions", text="")

        split = layout.split(factor=0.35)
        split.label(text="Base Axis")
        split.row().prop(self, "axis", expand=True)

        split = layout.split(factor=0.35)
        split.label(text="Coordinates")
        split.row().prop(self, "coordinate_space", expand=True)
        if self.method == "UV":
            split.enabled = False

        # 整列
        layout.label(text="Align", icon_value=icons.align_left)
        layout.row().prop(self, "align_uv", expand=True)
        layout.row().prop(self, "alignment", expand=True)

        if self.aling_mode == "FIXED":
            layout.separator()
            split = layout.split(factor=0.3)
            split.label(text="Grid Size")
            row = split.row(align=True)
            if self.grid_units == "PIXEL":
                row.prop(self, "grid_x_px", text="")
                row.prop(self, "grid_link", text="", icon="LINKED", toggle=True)
                row.prop(self, "grid_y_px", text="")
            else:
                row.prop(self, "grid_x", text="")
                row.prop(self, "grid_link", text="", icon="LINKED", toggle=True)
                row.prop(self, "grid_y", text="")

            split = layout.split(factor=0.3)
            split.label(text="Units")
            split.row().prop(self, "grid_units", expand=True)
            layout.separator(factor=4.2)
        else:
            layout.separator()
            row = layout.row()
            row.label(text="Island Spacing", text_ctxt="Operator")
            row.prop(self, "item_spacing", text="")
            layout.separator(factor=1)

        wrap_box = layout.box()
        col = wrap_box.column()
        split = col.split(factor=0.5)
        split.prop(self, "use_wrap", text="Wrap Count")
        row = split.row()
        row.prop(self, "wrap_count", text="")
        if not self.use_wrap:
            row.enabled = False
        split = col.split(factor=0.5)
        if not self.use_wrap:
            split.enabled = False
        if self.aling_mode != "FIXED":
            row = split.row()
            row.enabled = self.aling_mode != "FIXED"
            row.label(text="Line Spacing")
            split.prop(self, "line_spacing", text="")

        group_box = layout.box()
        col = group_box.column()
        split = col.split(factor=0.5)
        split.label(text="Group")
        split.prop(self, "group_type", text="")
        split = col.split(factor=0.5)
        if not self.group_type != "NONE":
            split.enabled = False

        if self.aling_mode != "FIXED":
            split.label(text="Group Spacing")
            split.prop(self, "group_spacing", text="")

        layout.prop(self, "reverse")


@bpy.app.handlers.persistent
def load_handler(dummy):
    UV_OT_mio3_sort.remove_handler()


def register():
    if load_handler not in bpy.app.handlers.load_post:
        bpy.app.handlers.load_post.append(load_handler)
    bpy.utils.register_class(UV_OT_mio3_sort)


def unregister():
    if load_handler in bpy.app.handlers.load_post:
        bpy.app.handlers.load_post.remove(load_handler)
    UV_OT_mio3_sort.remove_handler()
    bpy.utils.unregister_class(UV_OT_mio3_sort)
