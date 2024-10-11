import bpy
import time
import numpy as np
from bpy.props import BoolProperty, FloatProperty, EnumProperty
from mathutils import Vector
from ..classes.uv import UVIslandManager
from ..classes.operator import Mio3UVOperator


class MIO3UV_OT_place(Mio3UVOperator):
    bl_idname = "uv.mio3_place"
    bl_label = "Align Islands"
    bl_description = "Align Islands"
    bl_options = {"REGISTER", "UNDO"}

    axis: EnumProperty(name="Axis", items=[("AUTO", "Auto", ""), ("Y", "Y", ""), ("X", "X", "")])
    align_uv: EnumProperty(name="Align", items=[("X", "Align V", ""), ("Y", "Align H", "")])
    item_spacing: FloatProperty(
        name="Margin",
        default=0.01,
        min=0.0,
        step=0.1,
        precision=3,
    )

    def execute(self, context):
        self.start_time = time.time()
        self.objects = self.get_selected_objects(context)
        use_uv_select_sync = context.tool_settings.use_uv_select_sync

        if use_uv_select_sync:
            self.sync_uv_from_mesh(context, self.objects)

        island_manager = UVIslandManager(self.objects)
        if not island_manager.islands:
            return {"CANCELLED"}

        self.sort_uv_space(island_manager)
        self.align_islands(island_manager.islands)

        island_manager.update_uvmeshes()
        self.print_time(time.time() - self.start_time)
        return {"FINISHED"}

    def sort_uv_space(self, island_manager):
        if self.axis == "AUTO":
            all_centers = np.array([island.center for island in island_manager.islands])
            mesh_size = np.ptp(all_centers, axis=0)
            axis = ["X", "Y"][np.argmax(mesh_size)]
        else:
            axis = self.axis

        def sort_func(island):
            axis_index = {"X": 0, "Y": 1}[axis]
            return island.center[axis_index]

        island_manager.islands.sort(key=sort_func)

    def align_islands(self, islands):
        island_bounds = []
        for island in islands:
            island_bounds.append((island, island.min_uv, island.max_uv))

        all_min = np.min([bounds[1] for bounds in island_bounds], axis=0)
        all_max = np.max([bounds[2] for bounds in island_bounds], axis=0)

        if self.align_uv == "X":
            offset = Vector((all_min[0], 0))
        else:
            offset = Vector((0, all_max[1]))

        for island, min_uv, max_uv in island_bounds:
            if self.align_uv == "X":
                island_offset = Vector((offset.x - min_uv[0], 0 - min_uv[1]))
            else:
                island_offset = Vector((0 - min_uv[0], offset.y - max_uv[1]))
            
            island.move(island_offset)

            if self.align_uv == "X":
                offset.x += island.width + self.item_spacing
            else:
                offset.y -= island.height + self.item_spacing


classes = [MIO3UV_OT_place]


def register():
    for c in classes:
        bpy.utils.register_class(c)


def unregister():
    for c in classes:
        bpy.utils.unregister_class(c)