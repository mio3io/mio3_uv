import bpy
import time
import numpy as np
from bpy.props import BoolProperty, EnumProperty
from ..classes.uv import UVIslandManager, UVNodeManager
from ..classes.operator import Mio3UVOperator


class MIO3UV_OT_stretch(Mio3UVOperator):
    bl_idname = "uv.mio3_stretch"
    bl_label = "Stretch Island"
    bl_description = "Align the width of islands or UV groups"
    bl_options = {"REGISTER", "UNDO"}

    axis: EnumProperty(
        name="Axis",
        items=[("AUTO", "Auto", ""), ("BOTH", "Both", ""), ("X", "X", ""), ("Y", "Y", "")],
    )
    island: BoolProperty(name="Island Mode", default=False)
    keep_aspect: BoolProperty(name="Keep Aspect Ratio", default=False)

    def invoke(self, context, event):
        self.objects = self.get_selected_objects(context)
        if not self.objects:
            self.report({"WARNING"}, "Object is not selected")
            return {"CANCELLED"}

        use_uv_select_sync = context.tool_settings.use_uv_select_sync
        if use_uv_select_sync:
            self.sync_uv_from_mesh(context, self.objects)
        selected_face = self.check_selected_face_objects(self.objects)

        self.island = True if context.scene.mio3uv.island_mode else selected_face

        return self.execute(context)

    def check(self, context):
        self.objects = self.get_selected_objects(context)
        if context.tool_settings.use_uv_select_sync:
            self.sync_uv_from_mesh(context, self.objects)
        return True

    def execute(self, context):
        self.start_time = time.time()

        self.objects = self.get_selected_objects(context)

        if self.island:
            use_uv_select_sync = context.tool_settings.use_uv_select_sync
            if use_uv_select_sync:
                im = UVIslandManager(self.objects, mesh_link_uv=True, mesh_keep=True)
            else:
                im = UVIslandManager(self.objects)

            if not im.islands:
                return {"CANCELLED"}

            if self.axis == "AUTO":
                all_centers = np.array([island.center for island in im.islands])
                mesh_size = np.ptp(all_centers, axis=0)
                axis = ["Y", "X"][np.argmax(mesh_size)]
            else:
                axis = self.axis

            min_coord_x = min(island.min_uv.x for island in im.islands)
            max_coord_x = max(island.max_uv.x for island in im.islands)
            total_range_x = max_coord_x - min_coord_x

            min_coord_y = min(island.min_uv.y for island in im.islands)
            max_coord_y = max(island.max_uv.y for island in im.islands)
            total_range_y = max_coord_y - min_coord_y

            for island in im.islands:
                center_y = island.center.y
                center_x = island.center.x

                if axis == "BOTH":
                    scale_x = total_range_x / island.width
                    scale_y = total_range_y / island.height

                    for face in island.faces:
                        for loop in face.loops:
                            uv = loop[island.uv_layer].uv
                            local_x = uv.x - island.min_uv.x
                            local_y = uv.y - island.min_uv.y
                            uv.x = min_coord_x + (local_x * scale_x)
                            uv.y = min_coord_y + (local_y * scale_y)
                elif axis == "X":
                    scale_x = total_range_x / island.width
                    scale_y = scale_x if self.keep_aspect else 1.0

                    for face in island.faces:
                        for loop in face.loops:
                            uv = loop[island.uv_layer].uv
                            local_x = uv.x - island.min_uv.x
                            uv.x = min_coord_x + (local_x * scale_x)
                            if self.keep_aspect:
                                local_y = uv.y - center_y
                                uv.y = center_y + (local_y * scale_y)
                else:
                    scale_y = total_range_y / island.height
                    scale_x = scale_y if self.keep_aspect else 1.0

                    for face in island.faces:
                        for loop in face.loops:
                            uv = loop[island.uv_layer].uv
                            local_y = uv.y - island.min_uv.y
                            uv.y = min_coord_y + (local_y * scale_y)
                            if self.keep_aspect:
                                local_x = uv.x - center_x
                                uv.x = center_x + (local_x * scale_x)

            im.update_uvmeshes()
        else:
            nm = UVNodeManager(self.objects, mode="VERT")
            if not nm.groups:
                return {"CANCELLED"}

            for group in nm.groups:
                group.update_bounds()

            if self.axis == "AUTO":
                all_centers = np.array([group.center for group in nm.groups])
                mesh_size = np.ptp(all_centers, axis=0)
                axis = ["Y", "X"][np.argmax(mesh_size)]
            else:
                axis = self.axis

            min_coord = float("inf")
            max_coord = float("-inf")

            for group in nm.groups:
                if axis == "X":
                    min_coord = min(min_coord, group.min_uv.x)
                    max_coord = max(max_coord, group.max_uv.x)
                else:
                    min_coord = min(min_coord, group.min_uv.y)
                    max_coord = max(max_coord, group.max_uv.y)

            for group in nm.groups:
                if axis == "X":
                    group_width = group.max_uv.x - group.min_uv.x
                    if group_width > 0:
                        scale = (max_coord - min_coord) / group_width
                        for node in group.nodes:
                            local_x = node.uv.x - group.min_uv.x
                            node.uv.x = min_coord + (local_x * scale)
                else:
                    group_height = group.max_uv.y - group.min_uv.y
                    if group_height > 0:
                        scale = (max_coord - min_coord) / group_height
                        for node in group.nodes:
                            local_y = node.uv.y - group.min_uv.y
                            node.uv.y = min_coord + (local_y * scale)

                group.update_uvs()

            nm.update_uvmeshes()

        self.print_time(time.time() - self.start_time)
        return {"FINISHED"}

    def draw(self, context):
        layout = self.layout
        row = layout.row()
        row.label(text="Axis")

        row.prop(self, "axis", expand=True)
        layout.use_property_split = True
        layout.use_property_decorate = False
        layout.prop(self, "island")
        row = layout.row()
        row.prop(self, "keep_aspect")
        row.active = self.axis != "BOTH"


classes = [
    MIO3UV_OT_stretch,
]


def register():
    for c in classes:
        bpy.utils.register_class(c)


def unregister():
    for c in classes:
        bpy.utils.unregister_class(c)