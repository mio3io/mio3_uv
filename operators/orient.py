import bpy
import math
from mathutils import Vector
from bpy.props import BoolProperty
from ..classes.uv import UVIslandManager
from ..classes.operator import Mio3UVOperator


class MIO3UV_OT_orient(Mio3UVOperator):
    bl_idname = "uv.mio3_orient"
    bl_label = "Align Axis"
    bl_description = "Align the selected edge or island to an axis"
    bl_options = {"REGISTER", "UNDO"}

    center: BoolProperty(name="Center", default=False)
    island: BoolProperty(name="Island Mode", default=False)

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

    def execute(self, context):
        self.start_time()
        self.objects = self.get_selected_objects(context)

        use_uv_select_sync = context.tool_settings.use_uv_select_sync
        if use_uv_select_sync:
            self.sync_uv_from_mesh(context, self.objects)
            island_manager = UVIslandManager(self.objects, mesh_link_uv=True, mesh_keep=True)
        else:
            island_manager = UVIslandManager(self.objects)

        if not island_manager.islands:
            return {"CANCELLED"}

        if self.island:
            for island in island_manager.islands:
                island.select_all_uv()

            bpy.ops.uv.align_rotation(method="AUTO")
        else:
            for island in island_manager.islands:
                uv_layer = island.uv_layer
                selected_edges = self.get_selected_edges(island, uv_layer)
                if not selected_edges:
                    continue

                edge_uv = selected_edges[0][1][uv_layer].uv - selected_edges[0][0][uv_layer].uv
                current_angle = math.atan2(edge_uv.y, edge_uv.x)
                target_angle = round(current_angle / (math.pi / 2)) * (math.pi / 2)
                rotation_angle = target_angle - current_angle
                rotation_rad = rotation_angle

                self.rotate_island(island, rotation_rad, uv_layer, island.center)

                if self.center:
                    target_x = self.get_x(context, 0.5, island, uv_layer)
                    edge_center_x = sum(
                        (edge[0][uv_layer].uv.x + edge[1][uv_layer].uv.x) / 2 for edge in selected_edges
                    ) / len(selected_edges)
                    move_delta = target_x - edge_center_x
                    for face in island.faces:
                        for loop in face.loops:
                            loop[uv_layer].uv.x += move_delta

            island_manager.update_uvmeshes()

        self.print_time()
        return {"FINISHED"}

    def get_selected_edges(self, island, uv_layer):
        selected_edges = []
        for face in island.faces:
            for loop in face.loops:
                if loop[uv_layer].select and loop.link_loop_next[uv_layer].select:
                    selected_edges.append((loop, loop.link_loop_next))
        return selected_edges

    def rotate_island(self, island, rotation_angle, uv_layer, center_uv):
        sin_rot = math.sin(rotation_angle)
        cos_rot = math.cos(rotation_angle)
        for face in island.faces:
            for loop in face.loops:
                uv = loop[uv_layer].uv
                uv_local = uv - center_uv
                uv_rotated = (
                    Vector((uv_local.x * cos_rot - uv_local.y * sin_rot, uv_local.x * sin_rot + uv_local.y * cos_rot))
                    + center_uv
                )
                loop[uv_layer].uv = uv_rotated

    def get_x(self, context, x, island, uv_layer):
        if context.scene.mio3uv.udim:
            min_x = min(loop[uv_layer].uv.x for face in island.faces for loop in face.loops)
            tile_u = int(min_x)
            udim_x = tile_u + x
            return udim_x
        else:
            return x

    def draw(self, context):
        layout = self.layout
        layout.use_property_decorate = False
        layout.use_property_split = True
        layout.prop(self, "island")
        row = layout.row()
        row.prop(self, "center")
        if self.island:
            row.enabled = False


classes = [
    MIO3UV_OT_orient,
]


def register():
    for c in classes:
        bpy.utils.register_class(c)


def unregister():
    for c in classes:
        bpy.utils.unregister_class(c)
