import bpy
import numpy as np
from bpy.props import BoolProperty, EnumProperty
from ..classes.uv import UVIslandManager, UVNodeManager
from ..classes.operator import Mio3UVOperator


class MIO3UV_OT_stretch(Mio3UVOperator):
    bl_idname = "uv.mio3_stretch"
    bl_label = "Stretch"
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
        self.start_time()

        self.objects = self.get_selected_objects(context)
        use_uv_select_sync = context.tool_settings.use_uv_select_sync

        if self.island:
            if use_uv_select_sync:
                im = UVIslandManager(self.objects, mesh_link_uv=True, mesh_keep=True)
            else:
                im = UVIslandManager(self.objects)

            if not im.islands:
                return {"CANCELLED"}

            axis = im.get_axis_uv() if self.axis == "AUTO" else self.axis

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
                else:
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

            im.update_uvmeshes()
        else:
            if use_uv_select_sync:
                nm = UVNodeManager(self.objects, mode="VERT")
            else:
                nm = UVNodeManager(self.objects, mode="EDGE")
            
            if not nm.groups:
                return {"CANCELLED"}

            for group in nm.groups:
                group.update_bounds()

            if self.axis == "AUTO":
                all_centers = np.array([group.center for group in nm.groups])
                mesh_size = np.ptp(all_centers, axis=0)
                axis = ["X", "Y"][np.argmax(mesh_size)]
            else:
                axis = self.axis

            min_coord_x = min(group.min_uv.x for group in nm.groups)
            max_coord_x = max(group.max_uv.x for group in nm.groups)
            min_coord_y = min(group.min_uv.y for group in nm.groups)
            max_coord_y = max(group.max_uv.y for group in nm.groups)

            if axis == "BOTH":
                for group in nm.groups:
                    group_width = group.max_uv.x - group.min_uv.x
                    group_height = group.max_uv.y - group.min_uv.y
                    if group_width > 0:
                        scale_x = (max_coord_x - min_coord_x) / group_width
                        scale_y = (max_coord_y - min_coord_y) / group_height
                        for node in group.nodes:
                            local_x = node.uv.x - group.min_uv.x
                            node.uv.x = min_coord_x + (local_x * scale_x)
                            local_y = node.uv.y - group.min_uv.y
                            node.uv.y = min_coord_y + (local_y * scale_y)
                    group.update_uvs()
            elif axis == "X":
                for group in nm.groups:
                    group_height = group.max_uv.y - group.min_uv.y
                    if group_height > 0:
                        scale_y = (max_coord_y - min_coord_y) / group_height
                        for node in group.nodes:
                            local_y = node.uv.y - group.min_uv.y
                            node.uv.y = min_coord_y + (local_y * scale_y)
                    group.update_uvs()
            else:
                for group in nm.groups:
                    group_width = group.max_uv.x - group.min_uv.x
                    if group_width > 0:
                        scale_x = (max_coord_x - min_coord_x) / group_width
                        for node in group.nodes:
                            local_x = node.uv.x - group.min_uv.x
                            node.uv.x = min_coord_x + (local_x * scale_x)
                    group.update_uvs()

            nm.update_uvmeshes()

        self.print_time()
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
        row.enabled = self.axis != "BOTH"


classes = [
    MIO3UV_OT_stretch,
]


def register():
    for c in classes:
        bpy.utils.register_class(c)


def unregister():
    for c in classes:
        bpy.utils.unregister_class(c)
