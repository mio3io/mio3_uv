import bpy
from mathutils import Vector
from bpy.app.translations import pgettext_iface as tt_iface
from bpy.props import BoolProperty, EnumProperty
from ..classes.operator import Mio3UVOperator
from ..classes.uv import UVIslandManager


class MIO3UV_OT_mirror(Mio3UVOperator):
    bl_idname = "uv.mio3_mirror"
    bl_label = "Mirror"
    bl_description = "[Shift] {}\n[Alt] {}".format(tt_iface("Individual Origins"), tt_iface("Y Axis"))
    bl_options = {"REGISTER", "UNDO"}

    axis: EnumProperty(
        name="Axis",
        items=[
            ("X", "X", "X Axis"),
            ("Y", "Y", "Y Axis"),
        ],
    )
    pivot_point: EnumProperty(
        name="Pivot Point",
        items=[
            ("CENTER", "Center", "Bounding Box Center", "PIVOT_BOUNDBOX", 0),
            ("MEDIAN", "Median Point", "Median Point", "PIVOT_MEDIAN", 1),
            ("CURSOR", "2D Cursor", "2D Cursor", "PIVOT_CURSOR", 2),
            ("INDIVIDUAL_ORIGINS", "Individual Origins", "Individual Origins", "PIVOT_INDIVIDUAL", 3),
        ],
    )
    island: BoolProperty(name="Island Mode", default=False)

    def invoke(self, context, event):
        self.objects = self.get_selected_objects(context)
        if not self.objects:
            self.report({"WARNING"}, "Object is not selected")
            return {"CANCELLED"}

        if context.tool_settings.use_uv_select_sync:
            self.sync_uv_from_mesh(context, self.objects)

        if event.alt:
            self.axis = "Y"

        if event.shift:
            self.pivot_point = "INDIVIDUAL_ORIGINS"
        else:
            self.pivot_point = context.space_data.pivot_point

        selected_face = self.check_selected_face_objects(self.objects)
        self.island = True if context.scene.mio3uv.island_mode else selected_face
        return self.execute(context)

    def execute(self, context):
        self.start_time()

        if self.island:
            self.objects = self.get_selected_objects(context)
            use_uv_select_sync = context.tool_settings.use_uv_select_sync
            if use_uv_select_sync:
                self.sync_uv_from_mesh(context, self.objects)

            if use_uv_select_sync:
                island_manager = UVIslandManager(self.objects, mesh_keep=True, mesh_link_uv=True)
            else:
                island_manager = UVIslandManager(self.objects)

            if not island_manager.islands:
                return {"CANCELLED"}

            if self.pivot_point == "MEDIAN":
                center = self.get_median_point(island_manager.islands)
            elif self.pivot_point == "CENTER":
                center = self.get_islands_bounds(island_manager.islands)
            else:
                center = context.space_data.cursor_location.copy()

            for island in island_manager.islands:
                uv_layer = island.uv_layer

                if self.pivot_point == "INDIVIDUAL_ORIGINS":
                    center = island.center

                for face in island.faces:
                    for loop in face.loops:
                        uv = loop[uv_layer]
                        if self.axis == "X":
                            uv.uv.x = 2 * center.x - uv.uv.x
                        else:
                            uv.uv.y = 2 * center.y - uv.uv.y

                island.update_bounds()

            island_manager.update_uvmeshes()
        else:
            pivot_point = context.space_data.pivot_point
            context.space_data.pivot_point = self.pivot_point
            bpy.ops.transform.mirror(
                orient_type="GLOBAL",
                constraint_axis=(self.axis == "X", self.axis == "Y", False),
            )
            context.space_data.pivot_point = pivot_point

        self.print_time()
        return {"FINISHED"}

    def get_median_point(self, islands):
        sum_x = sum(island.center.x for island in islands)
        sum_y = sum(island.center.y for island in islands)
        count = len(islands)
        return Vector((sum_x / count, sum_y / count))

    def get_islands_bounds(self, islands):
        min_x = min(island.min_uv.x for island in islands)
        min_y = min(island.min_uv.y for island in islands)
        max_x = max(island.max_uv.x for island in islands)
        max_y = max(island.max_uv.y for island in islands)
        return Vector(((min_x + max_x) / 2, (min_y + max_y) / 2))


classes = [MIO3UV_OT_mirror]


def register():
    for c in classes:
        bpy.utils.register_class(c)


def unregister():
    for c in classes:
        bpy.utils.unregister_class(c)
