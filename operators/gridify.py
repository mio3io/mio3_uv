import bpy
import math
from bpy.props import BoolProperty, EnumProperty
from mathutils import Vector, Matrix
from ..classes import UVIslandManager, Mio3UVOperator
from ..utils.uv_follow import uv_follow, build_uv_loop_index, collect_shared_uv_loops


def calculate_uv_area(uv_coords):
    area = 0.0
    for index, uv in enumerate(uv_coords):
        next_uv = uv_coords[(index + 1) % len(uv_coords)]
        area += uv.x * next_uv.y - next_uv.x * uv.y
    return abs(area) * 0.5


class MIO3UV_OT_grid(Mio3UVOperator):
    bl_idname = "uv.mio3_gridify"
    bl_label = "Gridify"
    bl_description = "Align UVs of a quadrangle in a grid"
    bl_options = {"REGISTER", "UNDO"}

    normalize: BoolProperty(name="Normalize", default=False)
    keep_aspect: BoolProperty(name="Keep Aspect Ratio", default=False)
    even: BoolProperty(name="Even", default=False)
    mode: EnumProperty(
        name="Method",
        items=[
            ("LENGTH_AVERAGE", "Standard", ""),
            ("EVEN", "Even", ""),
        ],
    )

    def execute(self, context):
        self.start_time()
        tool_settings = context.tool_settings
        use_uv_select_sync = tool_settings.use_uv_select_sync
        objects = self.get_selected_objects(context)

        island_manager = UVIslandManager(objects, sync=use_uv_select_sync, extend=False)
        if not island_manager.islands:
            self.report({"WARNING"}, "No UV islands found")
            return {"CANCELLED"}

        uv_loop_index_cache = {}
        for island in island_manager.islands:
            bm = island.bm
            uv_layer = island.uv_layer
            obj = island.obj

            if obj not in uv_loop_index_cache:
                uv_loop_index_cache[obj] = build_uv_loop_index(bm, uv_layer)

            f_act = self.get_base_face(uv_layer, island.faces)
            if not f_act:
                continue

            shared_uvs = collect_shared_uv_loops(uv_layer, island.faces, uv_loop_index_cache[obj])
            self.align_rect(uv_layer, f_act)
            uv_follow(self.mode, island, f_act, shared_uvs)

        island_manager.update_uvmeshes()

        if self.normalize:
            bpy.ops.uv.mio3_normalize(keep_aspect=self.keep_aspect)

        self.print_time()
        return {"FINISHED"}

    def get_base_face(self, uv_layer, selected_faces):
        best_face = None
        best_score = float("inf")

        total_area = sum(face.calc_area() for face in selected_faces)
        avg_area = total_area / len(selected_faces)

        for face in selected_faces:
            if len(face.loops) == 4 and all(loop.uv_select_vert for loop in face.loops):
                max_angle_diff = 0
                for i in range(4):
                    v1 = face.loops[i][uv_layer].uv - face.loops[(i - 1) % 4][uv_layer].uv
                    v2 = face.loops[(i + 1) % 4][uv_layer].uv - face.loops[i][uv_layer].uv
                    angle_diff = abs(math.degrees(math.atan2(v1.x * v2.y - v1.y * v2.x, v1.dot(v2))) - 90)
                    if angle_diff > max_angle_diff:
                        max_angle_diff = angle_diff

                area_diff = abs(face.calc_area() - avg_area)

                angle_weight = 0.5
                area_weight = 1.0
                score = angle_weight * max_angle_diff + area_weight * (area_diff / avg_area)

                if score < best_score:
                    best_score = score
                    best_face = face

        return best_face

    def align_rect(self, uv_layer, active_face):

        uv_coords = [loop[uv_layer].uv.copy() for loop in active_face.loops]
        original_area = calculate_uv_area(uv_coords)
        min_uv = Vector((min(uv.x for uv in uv_coords), min(uv.y for uv in uv_coords)))
        max_uv = Vector((max(uv.x for uv in uv_coords), max(uv.y for uv in uv_coords)))
        center_uv = (min_uv + max_uv) / 2

        # 特定のエッジを基準に水平 or 垂直にする
        edge_uv = uv_coords[1] - uv_coords[0]
        current_angle = math.atan2(edge_uv.y, edge_uv.x)
        target_angle = round(current_angle / (math.pi / 2)) * (math.pi / 2)  # 90度単位
        angle_diff = target_angle - current_angle
        sin_a = math.sin(angle_diff)
        cos_a = math.cos(angle_diff)

        rot_matrix = Matrix(((cos_a, -sin_a), (sin_a, cos_a)))
        rotated_uvs = []
        for uv in uv_coords:
            local = uv - center_uv
            uv_rotated = rot_matrix @ local + center_uv
            rotated_uvs.append(uv_rotated)

        sorted_by_y = sorted(zip(rotated_uvs, active_face.loops), key=lambda pair: (pair[0].y, pair[0].x))
        bottom_pairs = sorted(sorted_by_y[:2], key=lambda pair: pair[0].x)
        top_pairs = sorted(sorted_by_y[2:], key=lambda pair: pair[0].x)
        corner_pairs = [bottom_pairs[0], bottom_pairs[1], top_pairs[1], top_pairs[0]]
        ordered_uvs = [uv for uv, _loop in corner_pairs]

        width_average = ((ordered_uvs[1] - ordered_uvs[0]).length + (ordered_uvs[2] - ordered_uvs[3]).length) / 2
        height_average = ((ordered_uvs[2] - ordered_uvs[1]).length + (ordered_uvs[3] - ordered_uvs[0]).length) / 2

        if width_average <= 0 or height_average <= 0:
            width = max(max(uv.x for uv in rotated_uvs) - min(uv.x for uv in rotated_uvs), 1e-8)
            height = max(max(uv.y for uv in rotated_uvs) - min(uv.y for uv in rotated_uvs), 1e-8)
        else:
            aspect_ratio = width_average / height_average
            if original_area > 0:
                width = math.sqrt(original_area * aspect_ratio)
                height = math.sqrt(original_area / aspect_ratio)
            else:
                width = width_average
                height = height_average

        half_width = width / 2
        half_height = height / 2
        new_uvs = [
            Vector((center_uv.x - half_width, center_uv.y - half_height)),
            Vector((center_uv.x + half_width, center_uv.y - half_height)),
            Vector((center_uv.x + half_width, center_uv.y + half_height)),
            Vector((center_uv.x - half_width, center_uv.y + half_height)),
        ]

        for (_old_uv, loop), new_uv in zip(corner_pairs, new_uvs):
            loop[uv_layer].uv = new_uv

    def draw(self, context):
        layout = self.layout
        layout.use_property_decorate = False
        layout.use_property_split = True
        row = layout.row()
        row.prop(self, "mode", expand=True)
        layout.prop(self, "normalize")

        row = layout.row()
        row.enabled = self.normalize
        row.prop(self, "keep_aspect")


def register():
    bpy.utils.register_class(MIO3UV_OT_grid)


def unregister():
    bpy.utils.unregister_class(MIO3UV_OT_grid)
