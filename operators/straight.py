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
    method: EnumProperty(
        name="Method",
        items=[
            ("ANGLE_BASED", "Angle Based", "Angle based unwrapping method"),
            ("CONFORMAL", "Conformal", "Conformal mapping method"),
            ("MINIMUM_STRETCH", "Minimum Stretch", "Minimum stretch mapping method"),
        ],
    )
    keep_length: BoolProperty(name="Preserve Length", default=True)
    pin: BoolProperty(name="Pinned", default=True)

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

        bpy.ops.uv.unwrap(method=self.method, margin=0.001, use_subsurf_data=False, fill_holes=True, correct_aspect=True)

        for island in island_manager.islands:
            island.restore_selection()
            if not self.pin:
                for face in island.faces:
                    for loop in face.loops:
                        if loop.uv_select_vert:
                            loop[island.uv_layer].pin_uv = False

        island_manager.update_uvmeshes(True)

        self.end_time()
        return {"FINISHED"}


def register():
    bpy.utils.register_class(UV_OT_mio3_straight)


def unregister():
    bpy.utils.unregister_class(UV_OT_mio3_straight)
