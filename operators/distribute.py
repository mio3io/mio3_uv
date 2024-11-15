import bpy
import time
import numpy as np
from bpy.props import BoolProperty, FloatProperty, EnumProperty
from mathutils import Vector
from ..classes.uv import UVIslandManager
from ..classes.operator import Mio3UVOperator


class MIO3UV_OT_distribute(Mio3UVOperator):
    bl_idname = "uv.mio3_distribute"
    bl_label = "Distribute"
    bl_description = "Distribute Islands"
    bl_options = {"REGISTER", "UNDO"}
    method: EnumProperty(name="Method", items=[("ALIGN", "Align", ""), ("DISTRIBUTE", "Distribute", "")])
    axis: EnumProperty(name="Direction", items=[("AUTO", "Auto", ""), ("X", "Align V", ""), ("Y", "Align H", "")])
    spacing: FloatProperty(name="Margin", default=0.01, min=0.0, step=0.1, precision=3)

    def execute(self, context):
        self.start_time = time.time()
        self.objects = self.get_selected_objects(context)
        use_uv_select_sync = context.tool_settings.use_uv_select_sync

        if use_uv_select_sync:
            self.sync_uv_from_mesh(context, self.objects)

        island_manager = UVIslandManager(self.objects)
        if not island_manager.islands:
            return {"CANCELLED"}

        self.align_islands(island_manager)

        island_manager.update_uvmeshes()
        self.print_time(time.time() - self.start_time)
        return {"FINISHED"}

    def align_islands(self, island_manager):
        islands = island_manager.islands
        if not islands:
            return

        if self.axis == "AUTO":
            all_centers = np.array([island.center for island in island_manager.islands])
            mesh_size = np.ptp(all_centers, axis=0)
            axis = ["X", "Y"][np.argmax(mesh_size)]
        else:
            axis = self.axis

        if axis == "X":
            island_manager.islands.sort(key=lambda island: island.center[0], reverse=False)
        else:
            island_manager.islands.sort(key=lambda island: island.center[1], reverse=True)

        if self.method == "DISTRIBUTE":
            total_islands = len(islands)
            if total_islands < 3:
                return

            first_island = islands[0]
            last_island = islands[-1]

            if axis == "X":
                total_space = last_island.max_uv.x - first_island.min_uv.x
                islands_width = sum(island.width for island in islands[1:-1])
                space = (total_space - islands_width - first_island.width - last_island.width) / (total_islands - 1)
                current_pos = first_island.max_uv.x + space
                for island in islands[1:-1]:
                    offset = Vector((current_pos - island.min_uv.x, 0))
                    island.move(offset)
                    current_pos += island.width + space
            else:
                total_space = first_island.max_uv.y - last_island.min_uv.y
                islands_height = sum(island.height for island in islands[1:-1])
                space = (total_space - islands_height - first_island.height - last_island.height) / (total_islands - 1)
                current_pos = first_island.min_uv.y - space
                for island in islands[1:-1]:
                    offset = Vector((0, current_pos - island.max_uv.y))
                    island.move(offset)
                    current_pos -= island.height + space
        else:
            all_bounds_min = Vector((float("inf"), float("inf")))
            all_bounds_max = Vector((float("-inf"), float("-inf")))
            for island in islands:
                all_bounds_min.x = min(all_bounds_min.x, island.min_uv.x)
                all_bounds_min.y = min(all_bounds_min.y, island.min_uv.y)
                all_bounds_max.x = max(all_bounds_max.x, island.max_uv.x)
                all_bounds_max.y = max(all_bounds_max.y, island.max_uv.y)

            if axis == "X":
                current_pos = all_bounds_min.x
            else:
                current_pos = all_bounds_max.y

            for island in islands:
                if axis == "X":
                    offset = Vector((current_pos - island.min_uv.x, 0))
                    current_pos += island.width + self.spacing
                else:
                    offset = Vector((0, current_pos - island.max_uv.y))
                    current_pos -= island.height + self.spacing

                island.move(offset)

    def draw(self, context):
        layout = self.layout
        layout.use_property_split = True
        layout.use_property_decorate = False

        row = layout.row()
        row.prop(self, "method", expand=True)

        row = layout.row()
        row.prop(self, "spacing", text="Spacing")
        row.active = self.method == "ALIGN"

        layout.use_property_split = False

        layout.label(text="Direction")
        row = layout.row()
        row.prop(self, "axis", expand=True)


classes = [MIO3UV_OT_distribute]


def register():
    for c in classes:
        bpy.utils.register_class(c)


def unregister():
    for c in classes:
        bpy.utils.unregister_class(c)
