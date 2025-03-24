import bpy
import math
from mathutils import Vector, Matrix
from bpy.props import BoolProperty, FloatProperty
from ..classes.operator import Mio3UVOperator
from ..classes.uv import UVIslandManager


class MIO3UV_OT_rotate(Mio3UVOperator):
    bl_idname = "uv.mio3_rotate"
    bl_label = "Rotate"
    bl_description = "Rotate"
    bl_options = {"REGISTER", "UNDO"}

    angle: FloatProperty(
        name="Angle",
        default=math.radians(90),
        min=-math.pi,
        max=math.pi,
        subtype="ANGLE",
        step=1000,
    )
    island: BoolProperty(name="Island Mode", default=False)

    def invoke(self, context, event):
        self.objects = self.get_selected_objects(context)
        if not self.objects:
            self.report({"WARNING"}, "Object is not selected")
            return {"CANCELLED"}

        if context.tool_settings.use_uv_select_sync:
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

        if not self.island:
            bpy.ops.transform.rotate(
                value=self.angle,
                orient_type="VIEW",
                orient_matrix=((1, 0, 0), (0, 1, 0), (0, 0, 1)),
                orient_matrix_type="VIEW",
            )
            return {"FINISHED"}

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

        pivot_point = context.space_data.pivot_point
        if pivot_point == "MEDIAN":
            center = self.get_median_point(island_manager.islands)
        elif pivot_point == "CENTER":
            center = self.get_islands_bounds(island_manager.islands)
        else:
            center = context.space_data.cursor_location.copy()

        angle = -self.angle
        cos_a = math.cos(angle)
        sin_a = math.sin(angle)
        rot_matrix = Matrix(((cos_a, -sin_a), (sin_a, cos_a)))

        for island in island_manager.islands:
            uv_layer = island.uv_layer

            if pivot_point == "INDIVIDUAL_ORIGINS":
                center = island.center

            for face in island.faces:
                for loop in face.loops:
                    uv = loop[uv_layer]
                    relative_pos = uv.uv - center
                    uv.uv = rot_matrix @ relative_pos + center

            island.update_bounds()

        island_manager.update_uvmeshes()

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


classes = [MIO3UV_OT_rotate]


def register():
    for c in classes:
        bpy.utils.register_class(c)


def unregister():
    for c in classes:
        bpy.utils.unregister_class(c)
