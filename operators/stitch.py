import bpy
from ..classes.uv import UVIslandManager
from ..classes.operator import Mio3UVOperator


class MIO3UV_OT_stitch(Mio3UVOperator):
    bl_idname = "uv.mio3_stitch"
    bl_label = "Stitch"
    bl_description = "Stitch Island"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        self.objects = self.get_selected_objects(context)

        use_uv_select_sync = context.tool_settings.use_uv_select_sync
        if use_uv_select_sync:
            self.sync_uv_from_mesh(context, self.objects)

        island_manager = UVIslandManager(self.objects)
        if not island_manager.islands:
            return {"CANCELLED"}

        # for island in island_manager.islands:
        #     island.deselect_all_uv()

        stitch_count = max(1, len(island_manager.islands) - 1)
        for _ in range(stitch_count):
            bpy.ops.uv.stitch(snap_islands=True, clear_seams=True, mode="EDGE", stored_mode="EDGE")

        island_manager.update_uvmeshes()

        return {"FINISHED"}


classes = [
    MIO3UV_OT_stitch,
]


def register():
    for c in classes:
        bpy.utils.register_class(c)


def unregister():
    for c in classes:
        bpy.utils.unregister_class(c)
