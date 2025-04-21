import bpy
import bmesh
import math
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

    threshold_rad: FloatProperty(
        name="Angle",
        default=math.radians(50.0),
        min=math.radians(1.0),
        max=math.radians(160.0),
        subtype="ANGLE",
        step=100,
    )
    use_box_mode: BoolProperty(name="Box Mode")
    cancel_type: EnumProperty(
        name="Cancel Type",
        items=[
            ("FRONT", "Front", ""),
            ("REAR", "Rear", ""),
        ],
    )
    flat_sharpness: FloatProperty(
        name="Flat Angle Threshold",
        default=math.radians(15),
        min=math.radians(1),
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
        default="BOTTOM",
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
        self.start_time()
        self.objects = self.get_selected_objects(context)

        view_matrix = context.space_data.region_3d.view_matrix
        view_direction = Vector((0, 0, -1)) @ view_matrix.to_3x3()
        view_position = view_matrix.inverted().translation

        for obj in self.objects:
            world_matrix = obj.matrix_world
            bm = bmesh.from_edit_mesh(obj.data)
            selected_faces = {face for face in bm.faces if face.select}

            if self.remove_seam:
                for face in selected_faces:
                    for edge in face.edges:
                        edge.seam = False

            self.mark_seam_by_angle(selected_faces, angle_rad=self.threshold_rad)

            if self.use_box_mode:
                front_face, back_face = self.get_key_faces(selected_faces, view_position, view_direction, world_matrix)
                cancel_face, sub_face = (
                    (front_face, back_face) if self.cancel_type == "FRONT" else (back_face, front_face)
                )
                # キャンセル側のシームを解除
                selected_faces2 = self.find_linked_flat([cancel_face], selected_faces, self.flat_sharpness)
                for face in selected_faces2:
                    for edge in face.edges:
                        edge.seam = False

                if self.wrap != "NONE":
                    view_matrix = context.space_data.region_3d.view_matrix

                    extreme_value = float("inf") if self.wrap in ["LEFT", "BOTTOM"] else float("-inf")

                    selected_faces2 = self.find_linked_flat([sub_face], selected_faces, self.flat_sharpness)
                    edges_to_check = set()
                    for face in selected_faces2:
                        edges_to_check.update(face.edges)

                    target_edge = None
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
                        edge_loop = self.get_edge_loop(target_edge)
                        for edge in edge_loop:
                            edge.seam = False

            bm.select_flush_mode()
            bmesh.update_edit_mesh(obj.data)

        if self.unwrap:
            bpy.ops.uv.unwrap(method="ANGLE_BASED", margin=0)
            bpy.ops.uv.align_rotation(method="GEOMETRY", axis="Z")

        self.print_time()
        return {"FINISHED"}

    @staticmethod
    def get_edge_loop(target_edge):
        edge_loop = [target_edge]
        visited = {target_edge}

        for direction in range(2):
            current_edge = target_edge
            while True:
                v1, v2 = current_edge.verts
                next_edge = None
                vert_to_check = v2 if direction == 0 else v1

                if len(vert_to_check.link_edges) != 4:
                    break

                connected_edges = [e for e in vert_to_check.link_edges if e != current_edge]
                for e in connected_edges:
                    if e in visited:
                        continue

                    shared_faces = set(current_edge.link_faces) & set(e.link_faces)
                    if not shared_faces:
                        edge_verts = set(e.verts)
                        if vert_to_check in edge_verts:
                            next_edge = e
                            break

                if next_edge is None:
                    break

                visited.add(next_edge)
                if direction == 0:
                    edge_loop.append(next_edge)
                else:
                    edge_loop.insert(0, next_edge)

                current_edge = next_edge

        return edge_loop

    @staticmethod
    def get_key_faces(faces, view_position, view_direction, world_matrix):
        rot = world_matrix.to_3x3()
        front_face = back_face = None
        best_front_score = best_back_score = float("-inf")

        for face in faces:
            center_world = world_matrix @ face.calc_center_median()
            normal_world = (rot @ face.normal).normalized()
            distance = (center_world - view_position).length
            dot = normal_world.dot(-view_direction)

            front_score = dot / (distance + 1)
            back_score = -dot / (distance + 1)

            if front_score > best_front_score:
                best_front_score = front_score
                front_face = face

            if back_score > best_back_score:
                best_back_score = back_score
                back_face = face

        return front_face, back_face

    @staticmethod
    def mark_seam_by_angle(selected_faces, angle_rad):
        target_edges = set()
        for face in selected_faces:
            for edge in face.edges:
                target_edges.add(edge)

        for edge in target_edges:
            if not edge.is_manifold:
                continue
            linked_faces = [f for f in edge.link_faces if f in selected_faces]
            if len(linked_faces) != 2:
                continue
            normal1 = linked_faces[0].normal
            normal2 = linked_faces[1].normal
            angle = normal1.angle(normal2)
            if angle >= angle_rad:
                edge.seam = True

    @staticmethod
    def find_linked_flat(base_face, selected_faces, threshold):
        visited = set()
        if not base_face or not selected_faces:
            return visited
        stack = list(base_face)
        while stack:
            face = stack.pop()
            if face in visited:
                continue
            visited.add(face)
            for edge in face.edges:
                for linked in edge.link_faces:
                    if linked in visited:
                        continue
                    if linked not in selected_faces:
                        continue
                    if face.normal.angle(linked.normal) <= threshold:
                        stack.append(linked)
        return visited

    def draw(self, context):
        layout = self.layout
        layout.prop(self, "threshold_rad")
        layout.prop(self, "remove_seam")

        layout.prop(self, "use_box_mode")
        box = layout.box()
        col = box.column(align=False)

        split = col.split(factor=0.5)
        split.label(text="Type")
        split.row().prop(self, "cancel_type", expand=True)
        if not self.use_box_mode:
            col.enabled = False
        split = col.split(factor=0.5)
        split.label(text="Flat Angle Threshold")
        split.prop(self, "flat_sharpness", text="")

        col.label(text="Box Wrap Point")
        row = col.row()
        row.prop(self, "wrap", expand=True)

        layout.prop(self, "unwrap")


class MIO3UV_OT_seam_boundary(Mio3UVOperator):
    bl_idname = "uv.mio3_seam_boundary"
    bl_label = "Mark Seam by Boundary"
    bl_description = "Mark Seam by Boundary"
    bl_options = {"REGISTER", "UNDO"}
    clear_seams: BoolProperty(name="Clear Seam", description="Clear Seam", default=False)

    def execute(self, context):
        self.objects = self.get_selected_objects(context)
        for obj in self.objects:
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
