import bpy
from mathutils import Vector
from bpy.props import BoolProperty
from ..classes.uv import UVIslandManager
from ..classes.operator import Mio3UVOperator


class MIO3UV_OT_normalize(Mio3UVOperator):
    bl_idname = "uv.mio3_normalize"
    bl_label = "Normalize"
    bl_description = "Normalize UVs"
    bl_options = {"REGISTER", "UNDO"}

    keep_aspect: BoolProperty(name="Keep Aspect Ratio", default=False)
    individual: BoolProperty(name="Individual", default=False)

    def execute(self, context):
        self.start_time()
        self.objects = self.get_selected_objects(context)

        use_uv_select_sync = context.tool_settings.use_uv_select_sync
        if use_uv_select_sync:
            self.sync_uv_from_mesh(context, self.objects)

        island_manager = UVIslandManager(self.objects, extend=False)

        if self.individual:
            for island in island_manager.islands:
                self.normalize_island(context, island)
        else:
            self.normalize_all_islands(context, island_manager.islands)

        island_manager.update_uvmeshes()

        self.print_time()
        return {"FINISHED"}

    def normalize_island(self, context, island):
        current_width = island.width
        current_height = island.height

        if self.keep_aspect:
            scale_factor = 1 / max(current_width, current_height)
            scale_x = scale_y = scale_factor
        else:
            scale_x = 1 / current_width
            scale_y = 1 / current_height

        self.apply_scale(context, island, scale_x, scale_y)

    def normalize_all_islands(self, context, islands):
        min_uv = Vector((float('inf'), float('inf')))
        max_uv = Vector((float('-inf'), float('-inf')))

        for island in islands:
            min_uv.x = min(min_uv.x, island.min_uv.x)
            min_uv.y = min(min_uv.y, island.min_uv.y)
            max_uv.x = max(max_uv.x, island.max_uv.x)
            max_uv.y = max(max_uv.y, island.max_uv.y)

        total_width = max_uv.x - min_uv.x
        total_height = max_uv.y - min_uv.y

        if self.keep_aspect:
            scale_factor = 1 / max(total_width, total_height)
            scale_x = scale_y = scale_factor
        else:
            scale_x = 1 / total_width
            scale_y = 1 / total_height

        for island in islands:
            self.apply_scale(context, island, scale_x, scale_y, min_uv)

    def apply_scale(self, context, island, scale_x, scale_y, global_min_uv=None):
        selected_loops = []
        for face in island.faces:
            for loop in face.loops:
                selected_loops.append(loop)
        
        anchor = self.get_anchor(context, island.center)

        min_uv = global_min_uv if global_min_uv else island.min_uv
        for face in island.faces:
            for loop in face.loops:
                uv = loop[island.uv_layer]
                new_x = (uv.uv.x - min_uv.x) * scale_x
                new_y = (uv.uv.y - min_uv.y) * scale_y
                uv.uv = anchor + Vector((new_x, new_y))

        island.update_bounds()

        if not global_min_uv:
            offset = anchor - island.min_uv
            island.move(offset)

    def get_anchor(self, context, center):
        if context.scene.mio3uv.udim:
            return self.get_tile_co(Vector((0, 0)), center)
        else:
            return Vector((0, 0))

    def get_tile_co(self, offset_vector, center):
        tile_u = int(center.x)
        tile_v = int(center.y)
        udim_x = tile_u + offset_vector.x
        udim_y = tile_v + offset_vector.y
        return Vector((udim_x, udim_y))

classes = [
    MIO3UV_OT_normalize,
]


def register():
    for c in classes:
        bpy.utils.register_class(c)


def unregister():
    for c in classes:
        bpy.utils.unregister_class(c)
