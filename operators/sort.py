import bpy
import time
import math
from mathutils import Vector
from bpy.props import BoolProperty, FloatProperty, EnumProperty, IntProperty
from ..icons import preview_collections
from ..classes.uv import UVIslandManager
from ..classes.operator import Mio3UVOperator


class MIO3UV_OT_sort_common(Mio3UVOperator):
    bl_options = {"REGISTER", "UNDO"}

    method: EnumProperty(
        name="Sort Method",
        items=[("AXIS", "Single Axis", "Single Axis"), ("RADIAL", "Radial", "Radial"), ("GRID", "Grid", "Grid"), ("UV", "UV Space", "UV Space")],
    )
    aling_mode: EnumProperty(items=[("DEFAULT", "Space", "")])
    align_uv: EnumProperty(name="Align", items=[("X", "Align H", ""), ("Y", "Align V", "")], default="X")
    alignment: EnumProperty(
        name="Alignment",
        items=[("TOP", "Top Align", "Top Align"), ("MIDDLE", "Middle Align", "Middle Align"), ("BOTTOM", "Bottom Align", "Bottom Align")],
        default="TOP",
    )

    reverse: BoolProperty(name="Reverse Order", description="Reverse Order", default=False)
    axis: EnumProperty(name="3D Axis", items=[("AUTO", "Auto", "Auto"), ("X", "X", "X"), ("Y", "Y", "Y"), ("Z", "Z", "Z")])
    group_spacing: FloatProperty(name="Margin", default=0.01, min=0.0, max=0.5, step=0.1, precision=3)
    item_spacing: FloatProperty(name="Margin", default=0.01, min=0.0, max=0.5, step=0.1, precision=3)
    line_spacing: FloatProperty(name="Line Spacing", default=0.0, min=-0.5, max=0.5, step=0.1, precision=3)

    grid_x: FloatProperty(name="Grid Size X", default=0.125, min=0.01, step=0.1, precision=3)
    grid_y: FloatProperty(name="Grid Size Y", default=0.125, min=0.01, step=0.1, precision=3)

    grid_threshold: FloatProperty(name="Grid Threshold", default=0.2, min=0.01, max=1, step=1)

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
    by_group: BoolProperty(name="By Group", default=False)
    group_unit: BoolProperty(name="Groups as Unit", default=False, options={"HIDDEN"})

    @property
    def start_angle_radian(self):
        hour = self.start_angle
        adjusted_hour = (hour - 3) % 12
        angle = -adjusted_hour * (math.pi / 6)
        return angle

    def execute(self, context):
        self.start_time()
        self.objects = self.get_selected_objects(context)
        use_uv_select_sync = context.tool_settings.use_uv_select_sync

        if use_uv_select_sync:
            self.sync_uv_from_mesh(context, self.objects)
            island_manager = UVIslandManager(self.objects, mesh_link_uv=True, mesh_keep=True)
        else:
            island_manager = UVIslandManager(self.objects)

        if not island_manager.islands:
            return {"CANCELLED"}

        if self.method == "RADIAL":
            self.sort_cylinder(island_manager)
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

        island_manager.update_uvmeshes()

        self.print_time()
        return {"FINISHED"}

    def find_groups(self, island_manager):
        groups = []
        if self.group_type == "NONE":
            return [island_manager.islands]
        elif self.group_type == "OBJECT":
            for obj, islands in island_manager.islands_by_object.items():
                groups.append(islands)
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
            groups.sort(key=lambda x: len(x[0].center), reverse=self.reverse)
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

            material_groups = {}
            for island in island_manager.islands:
                material = get_island_material(island)
                if material not in material_groups:
                    material_groups[material] = []
                material_groups[material].append(island)
            groups = list(material_groups.values())
            groups.sort(key=lambda x: get_island_material(x[0]).name if get_island_material(x[0]) else "")
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

    def sort_uv_space(self, island_manager):
        axis = self.axis if self.axis in {"X", "Y"} else island_manager.get_axis_uv()

        def sort_func(island):
            axis_index = {"X": 0, "Y": 1}[axis]
            return island.center[axis_index]

        if axis == "Y":
            island_manager.sort_all_islands(key=sort_func, reverse=not self.reverse)
        else:
            island_manager.sort_all_islands(key=sort_func, reverse=self.reverse)

    def sort_axis(self, island_manager):
        axis = self.axis if self.axis != "AUTO" else island_manager.get_axis_3d()
        axis_orders = {
            "X": ["+X", "+Y", "-Z"],
            "Y": ["+Y", "+X", "-Z"],
            "Z": ["-Z", "+X", "+Y"],
        }
        sort_order = axis_orders[axis]

        def sort_func(island):
            return tuple(
                island.center_3d["XYZ".index(axis[-1])] * (-1 if axis.startswith("-") else 1) for axis in sort_order
            )

        island_manager.sort_all_islands(key=sort_func, reverse=self.reverse)

    def sort_cylinder(self, island_manager):
        all_centers = [island.center_3d for island in island_manager.islands]
        min_coords = [min(center[i] for center in all_centers) for i in range(3)]
        max_coords = [max(center[i] for center in all_centers) for i in range(3)]
        axis_widths = [max_coords[i] - min_coords[i] for i in range(3)]
        if self.axis == "AUTO":
            narrowest_axis_index = axis_widths.index(min(axis_widths))
            axis = ["X", "Y", "Z"][narrowest_axis_index]
        else:
            axis = self.axis

        center_3d = sum(all_centers, Vector()) / len(all_centers)

        def sort_func(island):
            if axis == "X":
                relative_pos = Vector((island.center_3d.y, island.center_3d.z)) - Vector((center_3d.y, center_3d.z))
            elif axis == "Y":
                relative_pos = Vector((island.center_3d.x, island.center_3d.z)) - Vector((center_3d.x, center_3d.z))
            else:
                relative_pos = Vector((island.center_3d.x, island.center_3d.y)) - Vector((center_3d.x, center_3d.y))
            angle = math.atan2(relative_pos.y, relative_pos.x)
            adjusted_angle = (angle - self.start_angle_radian) % (2 * math.pi)
            return adjusted_angle

        island_manager.sort_all_islands(key=sort_func, reverse=self.reverse)

    def sort_grid(self, island_manager):
        all_centers = [island.center_3d for island in island_manager.islands]
        min_coords = [min(center[i] for center in all_centers) for i in range(3)]
        max_coords = [max(center[i] for center in all_centers) for i in range(3)]
        overall_size = max(max_coords[i] - min_coords[i] for i in range(3))
        base_size = 1.0  # 1が基準
        scale_factor = overall_size / base_size
        cell_size = self.grid_threshold * scale_factor
        axis_widths = [max_coords[i] - min_coords[i] for i in range(3)]
        if self.axis == "AUTO":
            narrowest_axis_index = axis_widths.index(min(axis_widths))
            axis = ["X", "Y", "Z"][narrowest_axis_index]
        else:
            axis = self.axis

        def sort_func(island):
            if axis == "Y":  # Z軸が行（大きい順）、X軸が列（小さい順）
                z_size = round((max_coords[2] - island.center_3d[2]) / cell_size)
                x = island.center_3d[0]
                return (z_size, x)
            elif axis == "Z":  # Y軸が行（大きい順）、X軸が列（小さい順）
                y_size = round((max_coords[1] - island.center_3d[1]) / cell_size)
                x = island.center_3d[0]
                return (y_size, x)
            elif axis == "X":  # Z軸が行（大きい順）、Y軸が列（小さい順）
                z_size = round((max_coords[2] - island.center_3d[2]) / cell_size)
                y = island.center_3d[1]
                return (z_size, y)

        island_manager.sort_all_islands(key=sort_func, reverse=self.reverse)

    def align_groups(self, groups):
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
            group_offset, group_size = self.align_items(group, offset)

            if self.align_uv == "X":
                offset.x = group_offset.x + spacing
            else:
                offset.y = group_offset.y - spacing

    def align_items(self, islands, group_offset):
        # グループ全体を移動
        if self.group_unit:
            group_min = Vector(
                (min(island.min_uv[0] for island in islands), min(island.min_uv[1] for island in islands))
            )
            group_max = Vector(
                (max(island.max_uv[0] for island in islands), max(island.max_uv[1] for island in islands))
            )
            group_size = group_max - group_min
            move_offset = Vector((group_offset.x - group_min.x, group_offset.y - group_max.y))
            for island in islands:
                island.move(move_offset)
            # 次のグループのオフセットとサイズ
            if self.align_uv == "X":
                new_offset = Vector((group_offset.x + group_size.x + self.group_spacing, group_offset.y))
            else:
                new_offset = Vector((group_offset.x, group_offset.y - group_size.y - self.group_spacing))

            return new_offset, group_size

        offset = group_offset.copy()
        max_size = Vector((0, 0))
        spacing = 0 if self.aling_mode == "FIXED" else self.item_spacing
        line_spacing = self.line_spacing

        row_size = Vector((0, 0))
        row_start = offset.copy()
        items_in_row = 0
        row_islands = []

        for island in islands:
            original_size = Vector((island.width, island.height))
            if self.aling_mode == "FIXED":
                island_size = Vector((self.grid_x, self.grid_y))
            else:
                if self.align_uv == "X":
                    island_size = Vector((island.width + spacing, island.height))
                else:
                    island_size = Vector((island.width, island.height + spacing))

            # Wrap check
            if self.use_wrap and items_in_row >= self.wrap_count:
                self._align_row(row_islands, row_start, row_size)
                row_islands = []

                if self.align_uv == "X":
                    offset.x = group_offset.x
                    offset.y -= row_size.y + line_spacing
                    max_size.y = max(max_size.y, group_offset.y - offset.y)
                    row_size.y = 0
                else:
                    offset.y = group_offset.y
                    offset.x += row_size.x + line_spacing
                    max_size.x = max(max_size.x, offset.x - group_offset.x)
                    row_size.x = 0
                items_in_row = 0
                row_start = offset.copy()

            if self.align_uv == "X":
                offset.x += island_size.x
                row_size.y = max(row_size.y, island_size.y)
                max_size.x = max(max_size.x, offset.x - row_start.x)
            else:
                offset.y -= island_size.y
                row_size.x = max(row_size.x, island_size.x)
                max_size.y = max(max_size.y, row_start.y - offset.y)

            row_islands.append((island, island_size, original_size))
            items_in_row += 1

        if row_islands:
            self._align_row(row_islands, row_start, row_size)

        if self.align_uv == "X":
            max_size.y = max(max_size.y, row_start.y - offset.y + row_size.y)
        else:
            max_size.x = max(max_size.x, offset.x - row_start.x + row_size.x)

        return offset, max_size

    def _align_row(self, row_islands, row_start, row_size):
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
                island_offset = Vector((row_start.x, row_start.y))

            island_offset -= Vector((island.min_uv[0], island.max_uv[1]))
            island.move(island_offset)

            if self.align_uv == "X":
                row_start.x += island_size.x
            else:
                row_start.y -= island_size.y


class MIO3UV_OT_sort(MIO3UV_OT_sort_common):
    bl_idname = "uv.mio3_sort"
    bl_label = "Sort"
    bl_description = "Reorder islands based on coordinates in 3D space"

    def draw(self, context):
        icons = preview_collections["icons"]
        layout = self.layout

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
            row_sub.label(text="Grid Threshold")
            row_sub.prop(self, "grid_threshold", text="")

        row_axis = layout.row()
        row_axis.scale_x = 1.2
        row_axis.label(text="Base Axis")
        row_axis.prop(self, "axis", expand=True)

        row_align_uv = layout.row()
        row_align_uv.label(text="Align", icon_value=icons["ALIGN_L"].icon_id)
        row_align_uv = layout.row()
        row_align_uv.prop(self, "align_uv", expand=True)
        row_aling_mode = layout.row()
        row_aling_mode.prop(self, "alignment", expand=True)

        row = layout.row()
        row.label(text="Island Margin", text_ctxt="Operator")
        row.prop(self, "item_spacing", text="")

        wrap_box = layout.box()
        row = wrap_box.row()
        col = row.column()
        col.prop(self, "use_wrap", text="Wrap Count")
        col = row.column()
        row_wrap = col.row(align=True)
        row_wrap.prop(self, "wrap_count", text="")

        if not self.use_wrap:
            col.enabled = False
        row_wrap = wrap_box.row()
        row_wrap.label(text="Line Spacing")
        row_wrap.prop(self, "line_spacing", text="")
        if not self.use_wrap:
            row_wrap.enabled = False

        group_box = layout.box()
        row = group_box.row(align=True)
        row.label(text="Group")
        row.prop(self, "group_type", text="")

        group_content = group_box.column()
        if not self.group_type != "NONE":
            group_content.enabled = False

        row_s = group_content.row(align=True)
        row_s.label(text="Group Margin")
        row_s.prop(self, "group_spacing", text="")

        row_reverse = layout.row()
        row_reverse.prop(self, "reverse")

class MIO3UV_OT_sort_grid(MIO3UV_OT_sort_common):
    bl_idname = "uv.mio3_sort_grid"
    bl_label = "Grid Sort"
    bl_description = "Gridding island based on coordinates in 3D space"

    aling_mode: EnumProperty(items=[("FIXED", "Grid Size", "")])
    by_group: BoolProperty(name="By Group", default=True, options={"HIDDEN"})
    group_unit: BoolProperty(name="Groups as Unit", default=False, options={"HIDDEN"})

    def invoke(self, context, event):
        grid_link = context.scene.mio3uv.grid_link
        if grid_link:
            self.grid_y = self.grid_x
        return self.execute(context)

    def check(self, context):
        grid_link = context.scene.mio3uv.grid_link
        if grid_link:
            self.grid_y = self.grid_x
        return True

    def draw(self, context):
        icons = preview_collections["icons"]
        layout = self.layout

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
            row_sub.label(text="Grid Threshold")
            row_sub.prop(self, "grid_threshold", text="")

        row_axis = layout.row()
        row_axis.scale_x = 1.2
        row_axis.label(text="Base Axis")
        row_axis.prop(self, "axis", expand=True)

        row_align_uv = layout.row()
        row_align_uv.label(text="Align", icon_value=icons["ALIGN_L"].icon_id)
        row_align_uv.prop(self, "align_uv", expand=True)

        row = layout.row(align=True)
        row.label(text="Grid Size")
        row.scale_x = 0.8
        row.prop(self, "grid_x", text="")
        row.scale_x = 1.25
        row.prop(context.scene.mio3uv, "grid_link", text="", icon="LINKED", toggle=True)
        row.scale_x = 0.8
        row.prop(self, "grid_y", text="")

        row = layout.row()
        col = row.column()
        col.prop(self, "use_wrap", text="Wrap Count")
        col = row.column()
        row_wrap = col.row(align=True)
        row_wrap.prop(self, "wrap_count", text="")
        if not self.use_wrap:
            col.enabled = False

        row = layout.row(align=True)
        row.label(text="Group")
        row.prop(self, "group_type", text="")

        row_reverse = layout.row()
        row_reverse.prop(self, "reverse")


classes = [MIO3UV_OT_sort, MIO3UV_OT_sort_grid]


def register():
    for c in classes:
        bpy.utils.register_class(c)


def unregister():
    for c in classes:
        bpy.utils.unregister_class(c)
