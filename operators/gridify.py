import bpy
import math
from bpy.props import BoolProperty, EnumProperty
from mathutils import Vector
from ..classes.uv import UVIslandManager
from ..classes.operator import Mio3UVOperator


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

        self.objects = self.get_selected_objects(context)
        use_uv_select_sync = context.tool_settings.use_uv_select_sync
        if use_uv_select_sync:
            self.sync_uv_from_mesh(context, self.objects)
            context.tool_settings.use_uv_select_sync = False
            context.scene.mio3uv.auto_uv_sync_skip = True
            island_manager = UVIslandManager(self.objects, mesh_link_uv=True)
        else:
            island_manager = UVIslandManager(self.objects, extend=False)

        for island in island_manager.islands:
            island.store_selection()
            island.deselect_all_uv()

        for obj in self.objects:
            islands = island_manager.islands_by_object[obj]
            for island in islands:
                island.restore_selection()
                bm = island.bm
                uv_layer = island.uv_layer

                quad = self.get_base_face(uv_layer, island.faces)
                if not quad:
                    island.deselect_all_uv()
                    continue
                bm.faces.active = quad

                self.align_square(uv_layer, bm.faces.active)

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

        bpy.ops.uv.unwrap(method="ANGLE_BASED", margin=0)
        bpy.ops.uv.pin(clear=True)

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

    # 四角形にする
    def align_square(self, uv_layer, active_face):
        uv_coords = [loop[uv_layer].uv for loop in active_face.loops]
        min_uv = Vector((min(uv.x for uv in uv_coords), min(uv.y for uv in uv_coords)))
        max_uv = Vector((max(uv.x for uv in uv_coords), max(uv.y for uv in uv_coords)))
        center_uv = (min_uv + max_uv) / 2

        # 角度
        edge_uv = uv_coords[1] - uv_coords[0]
        current_angle = math.atan2(edge_uv.y, edge_uv.x)
        rotation_angle = (round(math.degrees(current_angle) / 90) * 90 - math.degrees(current_angle) + 45) % 90 - 45
        rotation_rad = math.radians(rotation_angle)
        sin_rot, cos_rot = math.sin(rotation_rad), math.cos(rotation_rad)

        rotated_uvs = []
        for uv in uv_coords:
            uv_local = uv - center_uv
            uv_rotated = (
                Vector(
                    (
                        uv_local.x * cos_rot - uv_local.y * sin_rot,
                        uv_local.x * sin_rot + uv_local.y * cos_rot,
                    )
                )
                + center_uv
            )
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


classes = [
    MIO3UV_OT_grid,
]


def register():
    for c in classes:
        bpy.utils.register_class(c)


def unregister():
    for c in classes:
        bpy.utils.unregister_class(c)
