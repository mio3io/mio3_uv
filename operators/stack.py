import bpy
from bpy.props import BoolProperty, EnumProperty
from ..classes.uv import UVIslandManager
from ..classes.operator import Mio3UVOperator


class MIO3UV_OT_paste(Mio3UVOperator):
    bl_idname = "uv.mio3_paste"
    bl_label = "Paste"
    bl_description = "Paste selected UV vertices"
    bl_options = {"REGISTER", "UNDO"}

    mode: EnumProperty(
        name="Mode", items=[("PASTE", "Paste", ""), ("AUTO", "Auto", "")], default="PASTE", options={"HIDDEN"}
    )
    keep_position: BoolProperty(name="Keep Position", default=True)

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

        if self.keep_position:
            for island in island_manager.islands:
                island.update_bounds()
                offset = island.original_center - island.center
                island.move(offset)

        island_manager.update_uvmeshes()

        return {"FINISHED"}


class MIO3UV_OT_stack(Mio3UVOperator):
    bl_idname = "uv.mio3_stack"
    bl_label = "Stack"
    bl_description = "Overlap similar UV shapes"
    bl_options = {"REGISTER", "UNDO"}

    selected: BoolProperty(name="Selected Only", default=False)

    def execute(self, context):
        self.start_time()

        self.objects = self.get_selected_objects(context)
        use_uv_select_sync = context.tool_settings.use_uv_select_sync

        if use_uv_select_sync:
            self.sync_uv_from_mesh(context, self.objects)
            context.tool_settings.use_uv_select_sync = False
            context.scene.mio3uv.auto_uv_sync_skip = True
            island_manager = UVIslandManager(self.objects, find_all=True, mesh_all=True)
        else:
            island_manager = UVIslandManager(self.objects, find_all=True)

        selected_islands = [island for island in island_manager.islands if island.is_any_uv_selected()]
        islands = selected_islands if self.selected else island_manager.islands

        bpy.ops.uv.copy()

        visited = set()
        for base_island in selected_islands:
            if base_island in visited:
                continue
            base_face_count = len(base_island.faces)
            base_uv_count = self.get_island_uv_count(base_island)

            for island in islands:
                if island == base_island:
                    continue
                if not self.is_different(island, base_face_count, base_uv_count):
                    island.select_all_uv()
                    visited.add(island)

        bpy.ops.uv.paste()

        if use_uv_select_sync:
            island_manager.restore_vertex_selection()
            context.tool_settings.use_uv_select_sync = True

        island_manager.update_uvmeshes()
        self.print_time()
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
