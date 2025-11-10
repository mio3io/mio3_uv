import bpy
from mathutils import Vector
from bpy.props import BoolProperty
from ..classes import UVNodeManager, UVNodeGroup, Mio3UVOperator


class MIO3UV_OT_circle(Mio3UVOperator):
    bl_idname = "uv.mio3_circle"
    bl_label = "Circular"
    bl_description = "Shape the edge loop into a circular shape"
    bl_options = {"REGISTER", "UNDO"}

    composite: BoolProperty(
        name="Composite Edges",
        description="Process multiple edge loops as a single group",
    )

    def invoke(self, context, event):
        self.objects = self.get_selected_objects(context)
        if not self.objects:
            self.report({"WARNING"}, "Object is not selected")
            return {"CANCELLED"}
        return self.execute(context)

    def execute(self, context):
        self.start_time()
        use_uv_select_sync = context.tool_settings.use_uv_select_sync

        node_manager = UVNodeManager(self.objects, sync=use_uv_select_sync)
        if not node_manager.groups:
            return {"CANCELLED"}

        if self.composite:
            base_group = node_manager.groups[0]
            all_nodes = {node for group in node_manager.groups for node in group.nodes}
            composite_group = UVNodeGroup(
                nodes=all_nodes, obj=base_group.obj, bm=base_group.bm, uv_layer=base_group.uv_layer, mode="EDGE"
            )
            self.make_circular(composite_group)
            composite_group.update_uvs()
        else:
            for group in node_manager.groups:
                self.make_circular(group)
                group.update_uvs()

        node_manager.update_uvmeshes()

        self.print_time()
        return {"FINISHED"}

    def make_circular(self, group):
        center = sum((node.uv for node in group.nodes), Vector((0, 0))) / len(group.nodes)
        avg_radius = sum((node.uv - center).length for node in group.nodes) / len(group.nodes)
        for node in group.nodes:
            direction = node.uv - center
            if direction.length > 0:
                node.uv = center + direction.normalized() * avg_radius


def register():
    bpy.utils.register_class(MIO3UV_OT_circle)


def unregister():
    bpy.utils.unregister_class(MIO3UV_OT_circle)
