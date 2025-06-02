import bpy
import math
from mathutils import Vector, Matrix
from bpy.props import BoolProperty, EnumProperty
from ..classes import UVIslandManager, Mio3UVOperator
from ..utils import get_uv_from_mirror_offset, rotate_uv_faces


class MIO3UV_OT_orient(Mio3UVOperator):
    bl_idname = "uv.mio3_orient"
    bl_label = "Align Axis"
    bl_description = "Align the selected edge or island to an axis"
    bl_options = {"REGISTER", "UNDO"}

    island: BoolProperty(name="Island Mode", default=False)
    center_axis: EnumProperty(
        name="Alignment",
        items=[
            ("NONE", "Original Position", ""),
            ("CENTER", "Center", ""),
            ("MIRROR", "Mirror U/V", "Refers to the Mirror setting of the Mirror Modifier"),
        ],
        default="NONE",
    )

    def invoke(self, context, event):
        self.objects = self.get_selected_objects(context)
        if not self.objects:
            self.report({"WARNING"}, "Object is not selected")
            return {"CANCELLED"}

        selected_face = self.check_selected_face_objects(self.objects)
        self.island = True if context.scene.mio3uv.island_mode else selected_face
        return self.execute(context)

    def execute(self, context):
        self.start_time()

        # アイランド
        if self.island:
            bpy.ops.uv.align_rotation(method="AUTO")
            return {"FINISHED"}

        # UVグループ

        self.objects = self.get_selected_objects(context)
        udim = context.scene.mio3uv.udim

        use_uv_select_sync = context.tool_settings.use_uv_select_sync
        if use_uv_select_sync:
            self.sync_uv_from_mesh(context, self.objects)

        island_manager = UVIslandManager(self.objects, sync=use_uv_select_sync)
        if not island_manager.islands:
            return {"CANCELLED"}

        for island in island_manager.islands:
            uv_layer = island.uv_layer
            loop_uv1, loop_uv2 = self.get_selected_edge_loop(island)
            if not loop_uv1:
                continue

            edge_uv = loop_uv1.uv - loop_uv2.uv  # エッジのUV座標差分
            current_angle = math.atan2(edge_uv.y, edge_uv.x)  # 現在の角度
            target_angle = round(current_angle / (math.pi / 2)) * (math.pi / 2)  # 90度単位
            angle_diff = target_angle - current_angle

            rotate_uv_faces(island.faces, angle_diff, island.uv_layer, island.center)

            is_vertical = loop_uv1.uv.x == loop_uv2.uv.x  # 縦向きに整列した

            if self.center_axis == "MIRROR":
                center_uv = get_uv_from_mirror_offset(island.obj, is_vertical)
                if not center_uv:
                    continue
            elif self.center_axis == "CENTER":
                center_uv = Vector((0.5, 0.5))
            else:
                continue

            center_uv = self.get_udim_co(udim, center_uv, island)

            if is_vertical:
                move_delta = center_uv.x - loop_uv1.uv.x
                for face in island.faces:
                    for l in face.loops:
                        l[uv_layer].uv.x += move_delta
            else:
                move_delta = center_uv.y - loop_uv1.uv.y
                for face in island.faces:
                    for l in face.loops:
                        l[uv_layer].uv.y += move_delta

        if use_uv_select_sync:
            island_manager.restore_vertex_selection()

        island_manager.update_uvmeshes()

        self.print_time()
        return {"FINISHED"}

    def get_udim_co(self, is_udim, co, island):
        if is_udim:
            return Vector((int(island.center.x) + co.x, int(island.center.y) + co.y))
        else:
            return co

    def get_selected_edge_loop(self, island):
        uv_layer = island.uv_layer
        if island.sync:
            for face in island.faces:
                for edge in face.edges:
                    if edge.select:
                        for loop in edge.link_loops:
                            if loop[uv_layer].select and loop.link_loop_next[uv_layer].select:
                                return (loop[uv_layer], loop.link_loop_next[uv_layer])
        else:
            for face in island.faces:
                if face.select:
                    for loop in face.loops:
                        if loop[uv_layer].select and loop.link_loop_next[uv_layer].select:
                            return (loop[uv_layer], loop.link_loop_next[uv_layer])
        return (None, None)

    def draw(self, context):
        layout = self.layout
        split = layout.split(factor=0.3)
        split.label(text="")
        split.prop(self, "island")
        split = layout.split(factor=0.3)
        split.label(text="Alignment")
        split.prop(self, "center_axis", expand=True)
        split.enabled = not self.island


def register():
    bpy.utils.register_class(MIO3UV_OT_orient)


def unregister():
    bpy.utils.unregister_class(MIO3UV_OT_orient)
