import bpy
import bmesh
import math
import time
from mathutils import Vector
from bpy.props import BoolProperty, FloatProperty, EnumProperty
from bpy.app.translations import pgettext_iface as tt_iface
from ..icons import preview_collections
from ..classes.operator import Mio3UVOperator


class MIO3UV_OT_seam(Mio3UVOperator):
    bl_idname = "uv.mio3_seam"
    bl_label = "Mark Seam by Angle"
    bl_description = "Mark Seam by Angle"
    bl_options = {"REGISTER", "UNDO"}

    radian_threshold: FloatProperty(
        name="Angle",
        default=math.radians(50.0),
        min=math.radians(1.0),
        max=math.pi,
        subtype="ANGLE",
        step=100,
    )

    unseam_front: BoolProperty(
        name="Exclude Angle",
        default=False,
    )

    unfront_sharpness: FloatProperty(
        name="Front Angle Threshold",
        default=math.radians(10.0),
        min=math.radians(1.0),
        max=math.pi,
        subtype="ANGLE",
        step=100,
    )

    wrap: EnumProperty(
        name="Box Wrap Point",
        items=[
            ("NONE", "None", ""),
            ("LEFT", "Left", ""),
            ("RIGHT", "Right", ""),
            ("TOP", "Top", ""),
            ("BOTTOM", "Bottom", ""),
        ],
        default="NONE",
    )

    remove_seam: BoolProperty(
        name="Clear Original Seam",
        default=False,
    )
    unwrap: BoolProperty(
        name="UV Unwrap",
        default=False,
    )

    def execute(self, context):
        self.start_time = time.time()
        self.objects = self.get_selected_objects(context)

        obj = context.active_object

        bm = bmesh.from_edit_mesh(obj.data)
        bm.select_mode = {"EDGE"}

        selected_faces = {face for face in bm.faces if face.select}

        if self.remove_seam:
            bpy.ops.mesh.mark_seam(clear=True)

        bpy.ops.mesh.select_all(action="DESELECT")

        bpy.ops.mesh.edges_select_sharp(sharpness=self.radian_threshold)
        for edge in bm.edges:
            if edge.select:
                if any(face in selected_faces for face in edge.link_faces):
                    edge.seam = True

        view_matrix = context.space_data.region_3d.view_matrix
        view_direction = Vector((0, 0, -1)) @ view_matrix.to_3x3()
        view_position = view_matrix.inverted().translation
        world_matrix = obj.matrix_world

        front_face = None
        back_face = None
        best_front_score = float("-inf")
        best_back_score = float("-inf")

        if self.unseam_front or self.wrap != "NONE":
            for face in selected_faces:
                face_center_local = face.calc_center_median()
                face_center_world = world_matrix @ face_center_local

                distance = (face_center_world - view_position).length
                face_normal_world = (world_matrix.to_3x3() @ face.normal).normalized()
                dot_product = face_normal_world.dot(-view_direction)

                score = dot_product / (distance + 1)
                if score > best_front_score:
                    best_front_score = score
                    front_face = face

                back_score = -dot_product / (distance + 1)
                if back_score > best_back_score:
                    best_back_score = back_score
                    back_face = face

            # 正面のシームを解除
            if self.unseam_front:
                if front_face:
                    for face in bm.faces:
                        face.select = face == front_face

                bpy.ops.mesh.faces_select_linked_flat(sharpness=self.unfront_sharpness)

                selected_faces2 = {face for face in bm.faces if face.select}
                for face in selected_faces2:
                    if face.select:
                        for edge in face.edges:
                            edge.seam = False

            if self.wrap != "NONE":
                view_matrix = context.space_data.region_3d.view_matrix

                target_edge = None
                extreme_value = float("inf") if self.wrap in ["LEFT", "BOTTOM"] else float("-inf")

                edges_to_check = set()
                if back_face:
                    for face in bm.faces:
                        face.select = face == back_face

                bpy.ops.mesh.faces_select_linked_flat(sharpness=self.unfront_sharpness)

                for face in bm.faces:
                    if face.select:
                        edges_to_check.update(face.edges)
                for edge in bm.edges:
                    edge.select = False

                for edge in edges_to_check:
                    v1_screen = view_matrix @ obj.matrix_world @ edge.verts[0].co
                    v2_screen = view_matrix @ obj.matrix_world @ edge.verts[1].co

                    if self.wrap == "LEFT":
                        x_coord = max(v1_screen.x, v2_screen.x)
                        if x_coord < extreme_value:
                            extreme_value = x_coord
                            target_edge = edge
                    elif self.wrap == "RIGHT":
                        x_coord = min(v1_screen.x, v2_screen.x)
                        if x_coord > extreme_value:
                            extreme_value = x_coord
                            target_edge = edge
                    elif self.wrap == "TOP":
                        y_coord = min(v1_screen.y, v2_screen.y)
                        if y_coord > extreme_value:
                            extreme_value = y_coord
                            target_edge = edge
                    elif self.wrap == "BOTTOM":
                        y_coord = max(v1_screen.y, v2_screen.y)
                        if y_coord < extreme_value:
                            extreme_value = y_coord
                            target_edge = edge

                if target_edge:
                    target_edge.select = True

                    bpy.ops.mesh.loop_multi_select(ring=False)

                for edge in bm.edges:
                    if edge.select:
                        edge.seam = False

        bpy.ops.mesh.select_all(action="DESELECT")

        for face in selected_faces:
            face.select = True
        if self.unwrap:
            bpy.ops.uv.unwrap(method="ANGLE_BASED", margin=0)
            bpy.ops.uv.align_rotation(method="GEOMETRY", axis="Z")

        bmesh.update_edit_mesh(obj.data)
        self.print_time(time.time() - self.start_time)
        return {"FINISHED"}

    def draw(self, context):
        layout = self.layout
        layout.prop(self, "radian_threshold")
        layout.prop(self, "unseam_front")

        row = layout.row()
        row.prop(self, "unfront_sharpness")
        if not self.unseam_front:
            row.enabled = False

        layout.label(text="Wrap Box Point")
        row = layout.row()
        row.prop(self, "wrap", expand=True)
        layout.prop(self, "unwrap")
        layout.prop(self, "remove_seam")


class MIO3UV_OT_seam_boundary(Mio3UVOperator):
    bl_idname = "uv.mio3_seam_boundary"
    bl_label = "Mark Seam by Boundary"
    bl_description = "Mark Seam by Boundary"
    bl_options = {"REGISTER", "UNDO"}

    clear_seams: BoolProperty(name="Celar Seam", description="Celar Seam", default=False)

    def execute(self, context):
        obj = context.active_object

        bm = bmesh.from_edit_mesh(obj.data)

        original_selection = {e for e in bm.edges if e.select}
        original_face_selection = {f for f in bm.faces if f.select}

        bpy.ops.mesh.region_to_loop()

        for edge in bm.edges:
            if edge.select:
                if self.clear_seams:
                    edge.seam = False
                else:
                    edge.seam = True

        for e in bm.edges:
            e.select = e in original_selection
        for f in bm.faces:
            f.select = f in original_face_selection

        bmesh.update_edit_mesh(obj.data)
        bpy.ops.mesh.select_mode(type="FACE")
        return {"FINISHED"}


classes = [
    MIO3UV_OT_seam,
    MIO3UV_OT_seam_boundary,
]


def menu_context(self, context):
    icons = preview_collections["icons"]
    self.layout.operator(
        "uv.mio3_seam",
        text=tt_iface(MIO3UV_OT_seam.bl_label),
        icon_value=icons["SEAM"].icon_id,
    )
    self.layout.operator(
        "uv.mio3_seam_boundary",
        text=tt_iface(MIO3UV_OT_seam_boundary.bl_label),
        icon_value=icons["SEAM"].icon_id,
    )


def register():
    for c in classes:
        bpy.utils.register_class(c)
    bpy.types.VIEW3D_MT_uv_map.append(menu_context)


def unregister():
    for c in classes:
        bpy.utils.unregister_class(c)
    bpy.types.VIEW3D_MT_uv_map.remove(menu_context)
