import bpy
from bpy.props import BoolProperty, IntProperty
from ..classes import UVIslandManager, Mio3UVOperator


class MIO3UV_OT_stitch(Mio3UVOperator):
    bl_idname = "uv.mio3_stitch"
    bl_label = "Stitch"
    bl_description = "Stitch Island"
    bl_options = {"REGISTER", "UNDO"}

    static_island: IntProperty(name="Static Island", default=0)
    clear_seams: BoolProperty(name="Clear Seams", default=True)

    def execute(self, context):
        self.objects = self.get_selected_objects(context)
        use_uv_select_sync = context.tool_settings.use_uv_select_sync

        island_manager = UVIslandManager(self.objects, sync=use_uv_select_sync, select_mode="EDGE")
        if not island_manager.islands:
            return {"CANCELLED"}

        stitch_count = max(1, len(island_manager.islands) - 1)
        for _ in range(stitch_count):
            bpy.ops.uv.stitch(
                snap_islands=True,
                static_island=self.static_island,
                clear_seams=self.clear_seams,
                mode="EDGE",
                stored_mode="EDGE",
            )

        island_manager.update_uvmeshes(True)

        return {"FINISHED"}


def register():
    bpy.utils.register_class(MIO3UV_OT_stitch)


def unregister():
    bpy.utils.unregister_class(MIO3UV_OT_stitch)
