import bpy
import math
from bpy.props import BoolProperty, EnumProperty
from mathutils import Vector
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

    def align_rect(self, uv_layer, face):
        uvs = [loop[uv_layer].uv.copy() for loop in face.loops]
        center = sum(uvs, Vector((0, 0))) / 4
        edge0 = (uvs[1] - uvs[0]).length
        edge1 = (uvs[2] - uvs[1]).length
        edge2 = (uvs[3] - uvs[2]).length
        edge3 = (uvs[0] - uvs[3]).length
        right_angle_thresh = 1 
        length_ratio_thresh = 0.01
        is_rect = True
        for i in range(4):
            v1 = uvs[i] - uvs[(i - 1) % 4]
            v2 = uvs[(i + 1) % 4] - uvs[i]
            angle = abs(math.degrees(math.atan2(v1.x * v2.y - v1.y * v2.x, v1.dot(v2))))
            if abs(angle - 90) > right_angle_thresh:
                is_rect = False
                break
        if is_rect:
            w1 = edge0
            w2 = edge2
            h1 = edge1
            h2 = edge3
            if abs(w1 - w2) / max(w1, w2) > length_ratio_thresh or abs(h1 - h2) / max(h1, h2) > length_ratio_thresh:
                is_rect = False
        if is_rect:
            return
        width = (edge0 + edge2) / 2
        height = (edge1 + edge3) / 2
        angle = 0
        half_w = width / 2
        half_h = height / 2
        rect = [
            Vector((-half_w, -half_h)),
            Vector((half_w, -half_h)),
            Vector((half_w, half_h)),
            Vector((-half_w, half_h)),
        ]
        rot = mathutils.Matrix.Rotation(angle, 2)
        rect = [rot @ v + center for v in rect]
        pairs = sorted(zip(uvs, face.loops), key=lambda p: (p[0] - center).angle_signed(Vector((1, 0))))
        for (_, loop), new_uv in zip(pairs, rect):
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
