import bpy
from mathutils import Vector
from bpy.props import BoolProperty, FloatProperty
from ..classes.uv import UVIslandManager
from ..classes.operator import Mio3UVOperator


class MIO3UV_OT_offset(Mio3UVOperator):
    bl_idname = "uv.mio3_offset"
    bl_label = "Offset"
    bl_description = "Expand/Shrink UV Borders"
    bl_options = {"REGISTER", "UNDO"}

    offset: FloatProperty(
        name="Offset", description="Offset to expand UV boundary", default=0.001, min=-1.0, max=1.0, step=0.01
    )
    keep_pin: BoolProperty(name="Keep Pin", default=False)
    use_seam: BoolProperty(name="Seam", default=True)
    use_mesh_boundary: BoolProperty(name="Mesh Boundary", default=True)
    use_uv_boundary: BoolProperty(name="UV Space Boundary", default=False)

    def execute(self, context):
        self.start_time()
        self.objects = self.get_selected_objects(context)

        if context.tool_settings.uv_select_mode in {"FACE", "ISLAND"}:
            context.tool_settings.uv_select_mode = "VERTEX"

        if not context.tool_settings.use_uv_select_sync:
            bpy.ops.uv.mio3_select_boundary(
                "INVOKE_DEFAULT",
                use_mesh_boundary=self.use_mesh_boundary,
                use_seam=self.use_seam,
                use_uv_boundary=self.use_uv_boundary,
            )

        use_uv_select_sync = context.tool_settings.use_uv_select_sync
        if use_uv_select_sync:
            self.sync_uv_from_mesh(context, self.objects)
            context.tool_settings.mesh_select_mode = (True, False, False)

        island_manager = UVIslandManager(self.objects)

        for island in island_manager.islands:
            self.expand_uv_boundary_outward(island, self.offset)

        island_manager.update_uvmeshes()

        self.print_time()
        return {"FINISHED"}

    def expand_uv_boundary_outward(self, island, offset):
        uv_layer = island.uv_layer

        selected_uv_edges = []
        for face in island.faces:
            if face.select:
                for loop in face.loops:
                    if loop[uv_layer].select and loop.link_loop_next[uv_layer].select:
                        selected_uv_edges.append((loop, loop.link_loop_next))

        uv_movements = {}
        for loop1, loop2 in selected_uv_edges:
            uv1 = loop1[uv_layer].uv
            uv2 = loop2[uv_layer].uv
            edge_vector = (uv2 - uv1).normalized()
            perp_vector = -Vector((-edge_vector.y, edge_vector.x))

            uv_movements[loop1.vert] = uv_movements.get(loop1.vert, Vector((0, 0))) + (perp_vector * offset)
            uv_movements[loop2.vert] = uv_movements.get(loop2.vert, Vector((0, 0))) + (perp_vector * offset)

        for vert, movement in uv_movements.items():
            # if vert in island_verts:
            for face in island.faces:
                if face.select:
                    for loop in face.loops:
                        if loop.vert == vert:
                            if not (self.keep_pin and loop[uv_layer].pin_uv):
                                loop[uv_layer].uv += movement


classes = [
    MIO3UV_OT_offset,
]


def register():
    for c in classes:
        bpy.utils.register_class(c)


def unregister():
    for c in classes:
        bpy.utils.unregister_class(c)
