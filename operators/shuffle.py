import bpy
import random
from ..classes.uv import UVIslandManager
from ..classes.operator import Mio3UVOperator


class MIO3UV_OT_shuffle_island(Mio3UVOperator):
    bl_idname = "uv.mio3_shuffle_island"
    bl_label = "Shuffle"
    bl_description = "Shuffle Island"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        self.objects = self.get_selected_objects(context)

        use_uv_select_sync = context.tool_settings.use_uv_select_sync
        if use_uv_select_sync:
            self.sync_uv_from_mesh(context, self.objects)
            island_manager = UVIslandManager(self.objects, mesh_link_uv=True)
        else:
            island_manager = UVIslandManager(self.objects)

        islands = island_manager.islands
        selected_count = len(island_manager.islands)

        if selected_count == 2:
            island1 = islands[0]
            island2 = islands[1]
            island1_center = island1.center
            island2_center = island2.center
            island1.move(island2_center - island1_center)
            island2.move(island1_center - island2_center)

        elif selected_count > 2:
            original_centers = [island.center for island in islands]
            random.shuffle(original_centers)
            for island, new_center in zip(islands, original_centers):
                island.move(new_center - island.center)
        else:
            return {"CANCELLED"}

        if use_uv_select_sync:
            island_manager.restore_vertex_selection()

        island_manager.update_uvmeshes()

        return {"FINISHED"}


classes = [
    MIO3UV_OT_shuffle_island,
]


def register():
    for c in classes:
        bpy.utils.register_class(c)


def unregister():
    for c in classes:
        bpy.utils.unregister_class(c)
