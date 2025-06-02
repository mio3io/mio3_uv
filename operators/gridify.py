import bpy
import math
from bpy.props import BoolProperty, EnumProperty
from mathutils import Vector, Matrix
from ..classes import UVIslandManager, Mio3UVOperator
import mathutils


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
        self.objects = self.get_selected_objects(context)
        use_uv_select_sync = tool_settings.use_uv_select_sync
        if use_uv_select_sync:
            self.sync_uv_from_mesh(context, self.objects)
        island_manager = UVIslandManager(self.objects, extend=False, sync=use_uv_select_sync)

        for island in island_manager.islands:
            island.store_selection()
            island.deselect_all_uv()

        for colle in island_manager.collections:
            bm = colle.bm
            uv_layer = colle.uv_layer

            for island in colle.islands:
                island.restore_selection()

                quad = self.get_base_face(uv_layer, island.faces)
                if not quad:
                    island.deselect_all_uv()
                    continue
                bm.faces.active = quad

                self.align_rect(uv_layer, bm.faces.active)

                for face in island.faces:
                    if all(loop[uv_layer].select for loop in face.loops):
                        for loop in face.loops:
                            loop[uv_layer].pin_uv = True
                    else:
                        for loop in face.loops:
                            loop[uv_layer].pin_uv = False
                try:
                    bpy.ops.uv.follow_active_quads(mode=self.mode)
                except:
                    pass

        # Sync アイランドのメッシュだけ全選択
        if use_uv_select_sync:
            context.scene.mio3uv.auto_uv_sync_skip = True
            context.tool_settings.use_uv_select_sync = False

            for colle in island_manager.collections:
                bm = colle.bm
                for face in bm.faces:
                    face.select = False
                for island in colle.islands:
                    for face in island.faces:
                        face.select = True
                bm.select_flush(True)

        bpy.ops.uv.unwrap(method="ANGLE_BASED", margin=0)
        bpy.ops.uv.pin(clear=True)

        # Sync 選択を戻す
        if use_uv_select_sync:
            island_manager.restore_vertex_selection()
            context.tool_settings.use_uv_select_sync = True

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
            if len(face.loops) == 4 and all(loop[uv_layer].select for loop in face.loops):
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

        uv_coords = [loop[uv_layer].uv for loop in active_face.loops]
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

        min_x = min(uv.x for uv in rotated_uvs)
        max_x = max(uv.x for uv in rotated_uvs)
        min_y = min(uv.y for uv in rotated_uvs)
        max_y = max(uv.y for uv in rotated_uvs)

        new_uvs = [
            Vector((min_x, min_y)),
            Vector((max_x, min_y)),
            Vector((max_x, max_y)),
            Vector((min_x, max_y)),
        ]

        center = Vector(((min_x + max_x) / 2, (min_y + max_y) / 2))
        sorted_pairs = sorted(
            zip(rotated_uvs, active_face.loops),
            key=lambda pair: ((pair[0] - center).angle_signed(Vector((1, 0))) if (pair[0] - center).length > 0 else 0),
        )

        for (_, loop), new_uv in zip(sorted_pairs, new_uvs):
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
