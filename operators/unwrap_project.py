import bpy
import bmesh
from bpy.props import BoolProperty, EnumProperty
from mathutils import Vector
from ..icons import icons
from ..classes import UVIslandManager, Mio3UVOperator


class MIO3UV_OT_unwrap_project(Mio3UVOperator):
    bl_idname = "uv.mio3_unwrap_project"
    bl_label = "Normal Projection Unwrap"
    bl_description = "Project the UVs based on the normal direction of the selected faces.\nAvailable only when UV Sync Selection is enabled in the UV Editor"
    bl_options = {"REGISTER", "UNDO"}

    link_unwrap: BoolProperty(name="Unwrap linked faces", description="Unwrap linked faces", default=True)
    method: EnumProperty(
        name="Method",
        items=[
            ("ANGLE_BASED", "Angle Based", "Angle based unwrapping method"),
            ("CONFORMAL", "Conformal", "Conformal mapping method"),
            ("MINIMUM_STRETCH", "Minimum Stretch", "Minimum stretch mapping method"),
        ],
        default="CONFORMAL",
    )

    @classmethod
    def poll(cls, context):
        obj = context.active_object
        if context.area.type == "IMAGE_EDITOR":
            return (
                obj is not None
                and obj.type == "MESH"
                and obj.mode == "EDIT"
                and context.scene.tool_settings.use_uv_select_sync
            )
        return obj is not None and obj.type == "MESH" and obj.mode == "EDIT"

    def execute(self, context):
        self.start_time()
        objects = self.get_selected_objects(context)
        if not objects:
            return {"CANCELLED"}

        use_uv_select_sync = context.scene.tool_settings.use_uv_select_sync

        # 3Dモード
        if context.area.type == "VIEW_3D":
            for obj in objects:
                context.view_layer.objects.active = obj
                bm = bmesh.from_edit_mesh(obj.data)
                uv_layer = bm.loops.layers.uv.verify()
                selected_faces = [face for face in bm.faces if face.select]
                if selected_faces:
                    face_groups = self.find_groups(selected_faces)
                    for _, group in enumerate(face_groups):
                        self.project_faces(group, uv_layer)

                bmesh.update_edit_mesh(obj.data)
            if self.link_unwrap:
                if not use_uv_select_sync:
                    bpy.ops.uv.select_all(action="SELECT")
                bpy.ops.uv.pin(clear=False)
                bpy.ops.mesh.select_linked(delimit={"SEAM"})
                bpy.ops.uv.unwrap(method=self.method)
                bpy.ops.uv.pin(clear=True)
            context.view_layer.objects.active = objects[0]
            return {"FINISHED"}

        # UVモード
        island_manager = UVIslandManager(objects, sync=use_uv_select_sync)
        for island in island_manager.islands:
            bm = island.bm
            uv_layer = island.uv_layer
            island.store_selection()

            selected_faces = {face for face in island.faces if face.select and face.uv_select}
            self.project_faces(selected_faces, uv_layer)

            if self.link_unwrap:
                island.uv_select_set_all(True)
                for face in selected_faces:
                    for loop in face.loops:
                        if loop.uv_select_vert:
                            loop[uv_layer].pin_uv = True

                if bm.uv_select_sync_valid:
                    island.bm.uv_select_sync_to_mesh()

        if self.link_unwrap:
            bpy.ops.uv.unwrap(method=self.method)
            bpy.ops.uv.pin(clear=True)

        for island in island_manager.islands:
            bm = island.bm
            island.update_bounds()
            island.restore_selection()
            self.restore_island(island)
            if bm.uv_select_sync_valid:
                island.bm.uv_select_sync_to_mesh()

        island_manager.update_uvmeshes()

        context.view_layer.objects.active = objects[0]
        self.print_time()
        return {"FINISHED"}

    def restore_island(self, island):
        link_unwrap = self.link_unwrap
        current_size = max(island.width, island.height)
        original_size = max(island.original_width, island.original_height)
        move_offset = island.original_center - island.center
        if current_size <= 1e-8 or original_size <= 0:
            return

        scale = original_size / current_size
        center = island.center.copy()
        uv_layer = island.uv_layer

        for face in island.faces:
            if not link_unwrap and not face.uv_select:
                continue
            for loop in face.loops:
                uv = loop[uv_layer].uv
                loop[uv_layer].uv = center + (uv - center) * scale + move_offset

        island.update_bounds()

    def find_groups(self, faces):
        face_groups = []
        remaining_faces = set(faces)

        while remaining_faces:
            group = set()
            stack = [remaining_faces.pop()]

            while stack:
                current_face = stack.pop()
                if current_face in group:
                    continue

                group.add(current_face)

                for edge in current_face.edges:
                    for linked_face in edge.link_faces:
                        if linked_face in remaining_faces:
                            remaining_faces.remove(linked_face)
                            stack.append(linked_face)

            face_groups.append(list(group))

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
        scale = max(0.001, unit_size / 0.1)

        for face in faces:
            for loop in face.loops:
                co = loop.vert.co
                x = (co.dot(right) - min_x) / scale
                y = (co.dot(forward) - min_y) / scale
                loop[uv_layer].uv = (x, y)


def menu_context(self, context):
    self.layout.separator()
    self.layout.operator(MIO3UV_OT_unwrap_project.bl_idname, icon_value=icons.camera)


def register():
    bpy.utils.register_class(MIO3UV_OT_unwrap_project)
    bpy.types.VIEW3D_MT_uv_map.append(menu_context)


def unregister():
    bpy.utils.unregister_class(MIO3UV_OT_unwrap_project)
    bpy.types.VIEW3D_MT_uv_map.remove(menu_context)
