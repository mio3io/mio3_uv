import bpy
import numpy as np
from bpy.props import BoolProperty, EnumProperty
from ..classes import Mio3UVOperator, UVIslandManager, UVNodeManager


class UV_OT_mio3_stretch(Mio3UVOperator):
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
        objects = self.get_selected_objects(context)
        if not objects:
            self.report({"WARNING"}, "Object is not selected")
            return {"CANCELLED"}

        face_selected = self.check_selected_face_objects(objects)
        self.island = True if context.scene.mio3uv.island_mode else face_selected

        return self.execute(context)

    def execute(self, context):
        self.start_time()
        objects = self.get_selected_objects(context)

        use_uv_select_sync = context.tool_settings.use_uv_select_sync

        if self.island:
            island_manager = UVIslandManager(objects, sync=use_uv_select_sync)
            if not island_manager.islands:
                return {"CANCELLED"}

            axis = island_manager.get_axis_uv() if self.axis == "AUTO" else self.axis

            min_x = min(island.min_uv.x for island in island_manager.islands)
            max_x = max(island.max_uv.x for island in island_manager.islands)
            min_y = min(island.min_uv.y for island in island_manager.islands)
            max_y = max(island.max_uv.y for island in island_manager.islands)
            total_range_x = max_x - min_x
            total_range_y = max_y - min_y

            for island in island_manager.islands:
                uv_layer = island.uv_layer
                center_y = island.center.y
                center_x = island.center.x

                if axis == "BOTH":
                    scale_x = total_range_x / island.width
                    scale_y = total_range_y / island.height
                    for face in island.faces:
                        for loop in face.loops:
                            uv = loop[uv_layer].uv
                            local_x = uv.x - island.min_uv.x
                            local_y = uv.y - island.min_uv.y
                            uv.x = min_x + (local_x * scale_x)
                            uv.y = min_y + (local_y * scale_y)
                elif axis == "X":
                    scale_y = total_range_y / island.height
                    scale_x = scale_y if self.keep_aspect else 1.0
                    for face in island.faces:
                        for loop in face.loops:
                            uv = loop[uv_layer].uv
                            local_y = uv.y - island.min_uv.y
                            uv.y = min_y + (local_y * scale_y)
                            if self.keep_aspect:
                                local_x = uv.x - center_x
                                uv.x = center_x + (local_x * scale_x)
                else:
                    scale_x = total_range_x / island.width
                    scale_y = scale_x if self.keep_aspect else 1.0

                    for face in island.faces:
                        for loop in face.loops:
                            uv = loop[uv_layer].uv
                            local_x = uv.x - island.min_uv.x
                            uv.x = min_x + (local_x * scale_x)
                            if self.keep_aspect:
                                local_y = uv.y - center_y
                                uv.y = center_y + (local_y * scale_y)

            island_manager.update_uvmeshes(True)
        else:
            node_manager = UVNodeManager(objects, sync=use_uv_select_sync)
            if not node_manager.groups:
                return {"CANCELLED"}

            if self.axis == "AUTO":
                all_centers = np.array([group.center for group in node_manager.groups])
                mesh_size = np.ptp(all_centers, axis=0)
                axis = ["X", "Y"][np.argmax(mesh_size)]
            else:
                axis = self.axis

            min_x = min(group.min_uv.x for group in node_manager.groups)
            max_x = max(group.max_uv.x for group in node_manager.groups)
            min_y = min(group.min_uv.y for group in node_manager.groups)
            max_y = max(group.max_uv.y for group in node_manager.groups)

            if axis == "BOTH":
                for group in node_manager.groups:
                    group_width = group.max_uv.x - group.min_uv.x
                    group_height = group.max_uv.y - group.min_uv.y
                    if group_width > 0:
                        scale_x = (max_x - min_x) / group_width
                        scale_y = (max_y - min_y) / group_height
                        for node in group.nodes:
                            local_x = node.uv.x - group.min_uv.x
                            node.uv.x = min_x + (local_x * scale_x)
                            local_y = node.uv.y - group.min_uv.y
                            node.uv.y = min_y + (local_y * scale_y)
            elif axis == "X":
                for group in node_manager.groups:
                    group_height = group.max_uv.y - group.min_uv.y
                    if group_height > 0:
                        scale_y = (max_y - min_y) / group_height
                        for node in group.nodes:
                            local_y = node.uv.y - group.min_uv.y
                            node.uv.y = min_y + (local_y * scale_y)
            else:
                for group in node_manager.groups:
                    group_width = group.max_uv.x - group.min_uv.x
                    if group_width > 0:
                        scale_x = (max_x - min_x) / group_width
                        for node in group.nodes:
                            local_x = node.uv.x - group.min_uv.x
                            node.uv.x = min_x + (local_x * scale_x)

            for group in node_manager.groups:
                group.update_uvs()

            node_manager.update_uvmeshes()

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


def register():
    bpy.utils.register_class(UV_OT_mio3_stretch)


def unregister():
    bpy.utils.unregister_class(UV_OT_mio3_stretch)
