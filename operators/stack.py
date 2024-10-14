import bpy
import time
from bpy.props import BoolProperty, FloatProperty, EnumProperty
from ..icons import preview_collections
from ..classes.uv import UVIslandManager
from ..classes.operator import Mio3UVOperator


class MIO3UV_OT_paste(Mio3UVOperator):
    bl_idname = "uv.mio3_paste"
    bl_label = "Paste"
    bl_description = "Paste UV shapes"
    bl_options = {"REGISTER", "UNDO"}

    mode: EnumProperty(
        name="Mode", items=[("PASTE", "Paste", ""), ("AUTO", "Auto", "")], default="PASTE", options={"HIDDEN"}
    )

    def execute(self, context):
        self.objects = self.get_selected_objects(context)

        use_uv_select_sync = context.tool_settings.use_uv_select_sync
        if use_uv_select_sync:
            self.sync_uv_from_mesh(context, self.objects)

        island_manager = UVIslandManager(self.objects)
        if self.mode == "AUTO":
            bpy.ops.uv.copy()

        for island in island_manager.islands:
            island.store_selection()

        bpy.ops.uv.paste()

        for island in island_manager.islands:
            island.update_bounds()
            offset = island.original_center - island.center
            island.move(offset)

        island_manager.update_uvmeshes()

        return {"FINISHED"}


class MIO3UV_OT_stack(Mio3UVOperator):
    bl_idname = "uv.mio3_stack"
    bl_label = "Stack Island"
    bl_description = "Overlap similar UV shapes"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        self.objects = self.get_selected_objects(context)
        use_uv_select_sync = context.tool_settings.use_uv_select_sync
        current_select_mode = context.tool_settings.mesh_select_mode[:]

        if use_uv_select_sync:
            self.sync_uv_from_mesh(context, self.objects)
            island_manager = UVIslandManager(self.objects)

            bpy.ops.uv.copy()
            bpy.ops.uv.select_all(action="SELECT")
            bpy.ops.uv.paste()

            island_manager.restore_vertex_selection()
            island_manager.update_uvmeshes()
        else:
            island_manager = UVIslandManager(self.objects, find_all=True, uv_select=False)

            if not island_manager.islands:
                return {"CANCELLED"}

            base_island = next((island for island in island_manager.islands if island.is_any_uv_selected()), None)
            if not base_island:
                return {"CANCELLED"}

            base_face_count = len(base_island.faces)
            base_uv_count = self.get_island_uv_count(base_island)
            base_island.select_all_uv()

            bpy.ops.uv.copy()

            for island in island_manager.islands:
                if island == base_island:
                    continue
                if not self.is_different(island, base_face_count, base_uv_count):
                    island.select_all_uv()

            bpy.ops.uv.paste()

            island_manager.update_uvmeshes()

        return {"FINISHED"}

    def get_island_uv_count(self, island):
        return sum(len(face.loops) for face in island.faces)

    def is_different(self, island, base_face_count, base_uv_count):
        if len(island.faces) != base_face_count:
            return True
        if self.get_island_uv_count(island) != base_uv_count:
            return True
        return False


classes = [
    MIO3UV_OT_paste,
    MIO3UV_OT_stack,
]


def register():
    for c in classes:
        bpy.utils.register_class(c)


def unregister():
    for c in classes:
        bpy.utils.unregister_class(c)
