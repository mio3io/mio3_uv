import bpy
from bpy.props import BoolProperty, EnumProperty
from ..utils import straight_uv_nodes
from ..classes.uv import UVNodeManager
from ..classes.operator import Mio3UVOperator


class MIO3UV_OT_straight(Mio3UVOperator):
    bl_idname = "uv.mio3_straight"
    bl_label = "Straight"
    bl_description = "Unwrap selected edge loop to a straight line"
    bl_options = {"REGISTER", "UNDO"}

    type: EnumProperty(
        name="Align",
        items=[
            ("GEOMETRY", "Geometry", ""),
            ("EVEN", "Even", ""),
            ("NONE", "None", ""),
        ],
    )

    keep_length: BoolProperty(name="Preserve Length", default=True)

    def execute(self, context):
        self.start_time()
        self.objects = self.get_selected_objects(context)

        use_uv_select_sync = context.tool_settings.use_uv_select_sync
        if use_uv_select_sync:
            self.sync_uv_from_mesh(context, self.objects)
            bpy.ops.mesh.select_linked(delimit={"UV"})
            context.tool_settings.use_uv_select_sync = False
            context.scene.mio3uv.auto_uv_sync_skip = True

            node_manager = UVNodeManager(self.objects, mode="VERT")
        else:
            node_manager = UVNodeManager(self.objects, mode="EDGE")

        uv_select_mode = context.tool_settings.uv_select_mode
        if uv_select_mode == "FACE":
            context.tool_settings.uv_select_mode = "EDGE"

        for group in node_manager.groups:
            group.store_selection()

        for group in node_manager.groups:
            straight_uv_nodes(group, self.type, self.keep_length, center=True)
            for node in group.nodes:
                node.update_uv(group.uv_layer)

        bpy.ops.uv.pin(clear=False)
        bpy.ops.uv.select_linked()
        bpy.ops.uv.unwrap(method="ANGLE_BASED", margin=0.001)

        bpy.ops.uv.select_all(action="DESELECT")

        for group in node_manager.groups:
            group.restore_selection()

        bpy.ops.uv.pin(clear=True)

        node_manager.update_uvmeshes()

        if use_uv_select_sync:
            context.tool_settings.use_uv_select_sync = True

        self.print_time()
        return {"FINISHED"}


classes = [
    MIO3UV_OT_straight,
]


def register():
    for c in classes:
        bpy.utils.register_class(c)


def unregister():
    for c in classes:
        bpy.utils.unregister_class(c)
