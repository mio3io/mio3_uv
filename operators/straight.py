import bpy
from bpy.props import BoolProperty, EnumProperty
from ..utils.utils import straight_uv_nodes
from ..classes import Mio3UVOperator, UVIslandManager, UVNodeManager


class UV_OT_mio3_straight(Mio3UVOperator):
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
        objects = self.get_selected_objects(context)

        use_uv_select_sync = context.tool_settings.use_uv_select_sync

        island_manager = UVIslandManager(objects, sync=use_uv_select_sync)
        for island in island_manager.islands:
            island.store_selection()

            node_manager = UVNodeManager.from_island(island, sync=use_uv_select_sync, sub_faces=island.faces)
            if node_manager.groups:
                for group in node_manager.groups:
                    group.store_selection()
                    straight_uv_nodes(group, self.type, self.keep_length, center=True)
                    for node in group.nodes:
                        node.update_uv(group.uv_layer)
                    group.set_pin(True)

            island.uv_select_set_all(True)

        bpy.ops.uv.unwrap(method="ANGLE_BASED", margin=0.001)

        for island in island_manager.islands:
            island.restore_selection()

        island_manager.update_uvmeshes(True)

        self.end_time()
        return {"FINISHED"}


def register():
    bpy.utils.register_class(UV_OT_mio3_straight)


def unregister():
    bpy.utils.unregister_class(UV_OT_mio3_straight)
