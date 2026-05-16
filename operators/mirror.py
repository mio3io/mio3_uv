import bpy
from bpy.app.translations import pgettext_iface as tt_iface
from bpy.props import BoolProperty, EnumProperty
from ..classes import Mio3UVOperator, UVIslandManager, UVNodeManager

ver_5_1 = bpy.app.version >= (5, 1, 0)


class UV_OT_mio3_mirror(Mio3UVOperator):
    bl_idname = "uv.mio3_mirror"
    bl_label = "Mirror"
    bl_description = "[Shift] {}\n[Alt] {}".format(tt_iface("Individual Origins"), tt_iface("Y Axis"))
    bl_options = {"REGISTER", "UNDO"}

    def pivot_point_items(self, context):
        if ver_5_1:
            return [
                ("BOUNDING_BOX_CENTER", "Center", "Bounding Box Center", "PIVOT_BOUNDBOX", 0),
                ("MEDIAN_POINT", "Median Point", "Median Point of UVs", "PIVOT_MEDIAN", 1),
                ("CURSOR", "2D Cursor", "2D Cursor", "PIVOT_CURSOR", 2),
                ("INDIVIDUAL_ORIGINS", "Individual Origins", "Individual Origins", "PIVOT_INDIVIDUAL", 3),
            ]
        else:
            return [
                ("CENTER", "Center", "Bounding Box Center", "PIVOT_BOUNDBOX", 0),
                ("MEDIAN", "Median Point", "Median Point of UVs", "PIVOT_MEDIAN", 1),
                ("CURSOR", "2D Cursor", "2D Cursor", "PIVOT_CURSOR", 2),
                ("INDIVIDUAL_ORIGINS", "Individual Origins", "Individual Origins", "PIVOT_INDIVIDUAL", 3),
            ]

    axis: EnumProperty(
        name="Axis",
        items=[
            ("X", "X", "X Axis"),
            ("Y", "Y", "Y Axis"),
        ],
    )
    pivot_point: EnumProperty(
        name="Pivot Point",
        items=pivot_point_items,
    )
    island: BoolProperty(name="Island Mode", default=False)

    def invoke(self, context, event):
        objects = self.get_selected_objects(context)
        if not objects:
            self.report({"WARNING"}, "Object is not selected")
            return {"CANCELLED"}

        if event.alt:
            self.axis = "Y"

        if event.shift:
            self.pivot_point = "INDIVIDUAL_ORIGINS"
        else:
            self.pivot_point = context.space_data.pivot_point

        face_selected = self.check_selected_face_objects(objects)
        self.island = True if context.scene.mio3uv.island_mode else face_selected
        return self.execute(context)

    def execute(self, context):
        self.start_time()
        objects = self.get_selected_objects(context)
        use_uv_select_sync = context.tool_settings.use_uv_select_sync

        is_axis_x = self.axis == "X"
        center = context.space_data.cursor_location.copy()

        if self.island:
            island_manager = UVIslandManager(objects, sync=use_uv_select_sync)
            if not island_manager.islands:
                return {"CANCELLED"}

            if self.pivot_point in ("MEDIAN", "MEDIAN_POINT"):
                center = island_manager.get_median_center()
            elif self.pivot_point in ("CENTER", "BOUNDING_BOX_CENTER"):
                center = island_manager.get_bbox_center()

            for island in island_manager.islands:
                uv_layer = island.uv_layer

                if self.pivot_point == "INDIVIDUAL_ORIGINS":
                    center = island.median_center

                for face in island.faces:
                    for loop in face.loops:
                        loop_uv = loop[uv_layer]
                        if is_axis_x:
                            loop_uv.uv.x = 2 * center.x - loop_uv.uv.x
                        else:
                            loop_uv.uv.y = 2 * center.y - loop_uv.uv.y

                island.update_bounds()

            island_manager.update_uvmeshes(True)
        else:
            node_manager = UVNodeManager(objects, sync=use_uv_select_sync)
            if not node_manager.groups:
                return {"CANCELLED"}

            if self.pivot_point in ("MEDIAN", "MEDIAN_POINT"):
                center = node_manager.get_median_center()
            elif self.pivot_point in ("CENTER", "BOUNDING_BOX_CENTER"):
                center = node_manager.get_bbox_center()

            for group in node_manager.groups:
                if self.pivot_point == "INDIVIDUAL_ORIGINS":
                    center = group.median_center

                for node in group.nodes:
                    if is_axis_x:
                        node.uv.x = 2 * center.x - node.uv.x
                    else:
                        node.uv.y = 2 * center.y - node.uv.y

                group.update_bounds()
                group.update_uvs()

            node_manager.update_uvmeshes()

        self.end_time()
        return {"FINISHED"}

def register():
    bpy.utils.register_class(UV_OT_mio3_mirror)


def unregister():
    bpy.utils.unregister_class(UV_OT_mio3_mirror)
