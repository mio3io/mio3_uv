import bpy
import math
from mathutils import Matrix
from bpy.app.translations import pgettext_iface as tt_iface
from bpy.props import BoolProperty, FloatProperty, EnumProperty
from ..classes import Mio3UVOperator, UVIslandManager, UVNodeManager

ver_5_1 = bpy.app.version >= (5, 1, 0)


class MIO3UV_OT_rotate(Mio3UVOperator):
    bl_idname = "uv.mio3_rotate"
    bl_label = "Rotate"
    bl_description = "[Shift] {}".format(tt_iface("Individual Origins"))
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

    angle: FloatProperty(
        name="Angle",
        default=math.radians(90),
        min=-math.pi,
        max=math.pi,
        subtype="ANGLE",
        step=1000,
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

        center = context.space_data.cursor_location.copy()

        if self.island:
            island_manager = UVIslandManager(objects, sync=use_uv_select_sync)
            if not island_manager.islands:
                return {"CANCELLED"}

            if self.pivot_point in ("MEDIAN", "MEDIAN_POINT"):
                center = island_manager.get_median_center()
            elif self.pivot_point in ("CENTER", "BOUNDING_BOX_CENTER"):
                center = island_manager.get_bbox_center()

            angle = -self.angle
            cos_a = math.cos(angle)
            sin_a = math.sin(angle)
            rot_matrix = Matrix(((cos_a, -sin_a), (sin_a, cos_a)))

            for island in island_manager.islands:
                uv_layer = island.uv_layer

                if self.pivot_point == "INDIVIDUAL_ORIGINS":
                    center = island.median_center

                for face in island.faces:
                    for loop in face.loops:
                        loop_uv = loop[uv_layer]
                        relative_pos = loop_uv.uv - center
                        loop_uv.uv = rot_matrix @ relative_pos + center

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
                
            angle = -self.angle
            cos_a = math.cos(angle)
            sin_a = math.sin(angle)
            rot_matrix = Matrix(((cos_a, -sin_a), (sin_a, cos_a)))

            for group in node_manager.groups:
                if self.pivot_point == "INDIVIDUAL_ORIGINS":
                    center = group.median_center

                for node in group.nodes:
                    relative_pos = node.uv - center
                    node.uv = rot_matrix @ relative_pos + center

                group.update_bounds()
                group.update_uvs()

            node_manager.update_uvmeshes()

        self.print_time()
        return {"FINISHED"}

def register():
    bpy.utils.register_class(MIO3UV_OT_rotate)


def unregister():
    bpy.utils.unregister_class(MIO3UV_OT_rotate)
