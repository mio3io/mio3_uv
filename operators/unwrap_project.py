import bpy
import bmesh
from bpy.props import BoolProperty, FloatProperty
from bpy.app.translations import pgettext_iface as tt_iface
from mathutils import Vector
from ..icons import preview_collections
from ..classes.uv import UVIslandManager
from ..classes.operator import Mio3UVOperator


class MIO3UV_OT_unwrap_project(Mio3UVOperator):
    bl_idname = "uv.mio3_unwrap_project"
    bl_label = "Projection Unwrap"
    bl_description = "Projection UV Unwrap"
    bl_options = {"REGISTER", "UNDO"}

    units: BoolProperty(name="Unwrap by linked mesh", default=True)
    link_unwrap: BoolProperty(name="Unwrap linked faces", description="Unwrap linked faces", default=True)
    scale_factor: FloatProperty(name="Scale Factor", default=0.1, min=0.01, max=1, step=0.1)

    def execute(self, context):
        self.start_time()
        self.objects = self.get_selected_objects(context)

        if not self.objects:
            return {"CANCELLED"}

        for obj in self.objects:
            context.view_layer.objects.active = obj
            bpy.ops.object.mode_set(mode="EDIT")

            bm = bmesh.from_edit_mesh(obj.data)
            uv_layer = bm.loops.layers.uv.active

            selected_faces = [face for face in bm.faces if face.select]
            if not selected_faces:
                continue

            if not self.units:
                self.project_faces(selected_faces, uv_layer)
            else:
                face_groups = self.find_groups(selected_faces)
                for _, group in enumerate(face_groups):
                    self.project_faces(group, uv_layer)

            bmesh.update_edit_mesh(obj.data)

        if self.link_unwrap:
            bpy.ops.uv.select_all(action="SELECT")
            bpy.ops.uv.pin(clear=False)
            bpy.ops.mesh.select_linked(delimit={"SEAM"})
            bpy.ops.uv.unwrap(method="CONFORMAL")
            # bpy.ops.uv.unwrap(method='ANGLE_BASED')
            bpy.ops.uv.pin(clear=True)

        context.view_layer.objects.active = self.objects[0]

        if self.units:
            island_manager = UVIslandManager(self.objects)
            self.align_islands(island_manager.islands)
            island_manager.update_uvmeshes()

        self.print_time()
        return {"FINISHED"}

    def align_islands(self, islands):
        if not islands:
            return

        islands.sort(key=lambda island: island.width * island.height)
        # islands.sort(key=lambda island: (island.center_3d.x, -island.center_3d.z, island.center_3d.y))

        current_x = 0
        current_y = 0

        for island in islands:
            offset_x = current_x - island.min_uv.x
            offset_y = current_y - island.min_uv.y
            island.move(Vector((offset_x, offset_y)))
            current_x += island.width + 0.01

    def find_groups(self, faces):
        face_groups = []
        used_faces = set()

        for face in faces:
            if face not in used_faces:
                group = set()
                stack = [face]
                while stack:
                    current_face = stack.pop()
                    if current_face not in group:
                        group.add(current_face)
                        stack.extend(
                            linked_face
                            for edge in current_face.edges
                            for linked_face in edge.link_faces
                            if linked_face.select and linked_face not in group
                        )
                face_groups.append(list(group))
                used_faces.update(group)

        return face_groups

    def project_faces(self, faces, uv_layer):
        avg_normal = sum((f.normal.copy() for f in faces), Vector()).normalized()
        if abs(avg_normal.z) > 0.99:
            up = Vector((0, 1, 0))
        else:
            up = Vector((0, 0, 1))
        right = up.cross(avg_normal).normalized()
        forward = avg_normal.cross(right).normalized()

        uv_coords = []
        for face in faces:
            for loop in face.loops:
                co = loop.vert.co
                x = co.dot(right)
                y = co.dot(forward)
                uv_coords.append((x, y))

        min_x = min(uv[0] for uv in uv_coords)
        max_x = max(uv[0] for uv in uv_coords)
        min_y = min(uv[1] for uv in uv_coords)
        max_y = max(uv[1] for uv in uv_coords)

        width = max_x - min_x
        height = max_y - min_y

        unit_size = max(width, height)
        scale = max(0.001, unit_size / self.scale_factor)

        for face in faces:
            for loop in face.loops:
                co = loop.vert.co
                x = (co.dot(right) - min_x) / scale
                y = (co.dot(forward) - min_y) / scale
                loop[uv_layer].uv = (x, y)


classes = [MIO3UV_OT_unwrap_project]


def menu_context(self, context):
    icons = preview_collections["icons"]
    self.layout.separator()
    self.layout.operator(
        MIO3UV_OT_unwrap_project.bl_idname, text=tt_iface("Projection Unwrap"), icon_value=icons["UNWRAP"].icon_id
    )


def register():
    for c in classes:
        bpy.utils.register_class(c)
    bpy.types.VIEW3D_MT_uv_map.append(menu_context)


def unregister():
    for c in classes:
        bpy.utils.unregister_class(c)
    bpy.types.VIEW3D_MT_uv_map.remove(menu_context)
