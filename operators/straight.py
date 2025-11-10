import bpy
from bpy.props import BoolProperty, EnumProperty
from ..utils import straight_uv_nodes
from ..classes import UVNodeManager, Mio3UVOperator


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

        node_manager = UVNodeManager(self.objects, sync=use_uv_select_sync)

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
        
        node_manager.uv_select_set_all(False)

        for group in node_manager.groups:
            group.restore_selection()

        node_manager.update_uvmeshes(True)

        self.print_time()
        return {"FINISHED"}


def register():
    bpy.utils.register_class(MIO3UV_OT_straight)


def unregister():
    bpy.utils.unregister_class(MIO3UV_OT_straight)
