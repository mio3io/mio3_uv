import bpy
import bmesh
from mathutils import Vector, kdtree
from bpy.props import FloatProperty, EnumProperty
from ..classes import Mio3UVOperator
from ..utils import get_tile_co
from ..icons import preview_collections


class MIO3UV_OT_symmetry_snap(Mio3UVOperator):
    bl_idname = "uv.mio3_symmetry_snap"
    bl_label = "Snap"
    bl_description = "Symmetrize based on UV space"
    bl_options = {"REGISTER", "UNDO"}

    def symmetry_direction_items(self, context):
        icons = preview_collections["icons"]
        symmetry_uv_axis = context.scene.mio3uv.symmetry_uv_axis
        if symmetry_uv_axis == "X":
            return [
                ("NEGATIVE", "-X → +X", "", icons["SYMM_N_X"].icon_id, 0),
                ("POSITIVE", "-X ← +X", "", icons["SYMM_P_X"].icon_id, 1),
            ]
        else:
            return [
                ("NEGATIVE", "-Y → +Y", "", icons["SYMM_N_Y"].icon_id, 0),
                ("POSITIVE", "-Y ← +Y", "", icons["SYMM_P_Y"].icon_id, 1),
            ]

    center: EnumProperty(
        name="Center",
        items=[
            ("GLOBAL", "Center", "Use UV space center"),
            ("CURSOR", "Cursor", "Use 2D cursor position"),
            ("SELECT", "Selection", "Selection"),
        ],
        default="SELECT",
    )
    direction: EnumProperty(
        name="Direction",
        items=symmetry_direction_items,
        default=1,
    )
    axis_uv: EnumProperty(
        name="Axis",
        items=[
            ("X", "X", ""),
            ("Y", "Y", ""),
        ],
        default="X",
    )
    threshold: FloatProperty(
        name="Threshold",
        default=0.05,
        min=0.0001,
        max=0.1,
        step=0.1,
        precision=4,
    )
    threshold_center: FloatProperty(
        name="Threshold Center",
        default=0.0005,
        min=0.0001,
        max=0.001,
        step=0.1,
        precision=4,
    )

    def invoke(self, context, event):
        self.objects = self.get_selected_objects(context)
        if not self.objects:
            self.report({"WARNING"}, "No objects selected")
            return {"CANCELLED"}
        self.center = context.scene.mio3uv.symmetry_center
        self.axis_uv = context.scene.mio3uv.symmetry_uv_axis
        self.axis_3d = context.scene.mio3uv.symmetry_3d_axis
        return self.execute(context)

    def check(self, context):
        context.scene.mio3uv.symmetry_center = self.center
        self.axis_uv = context.scene.mio3uv.symmetry_uv_axis
        self.axis_3d = context.scene.mio3uv.symmetry_3d_axis
        return True

    def execute(self, context):
        use_uv_select_sync = context.tool_settings.use_uv_select_sync
        if context.tool_settings.use_uv_select_sync:
            self.sync_uv_from_mesh(context, self.objects)

        for obj in self.objects:
            context.view_layer.objects.active = obj
            self.symmetrize_object(context, obj)

        if use_uv_select_sync:
            context.tool_settings.use_uv_select_sync = True
        return {"FINISHED"}

    def symmetrize_object(self, context, obj):
        current_mode = context.tool_settings.mesh_select_mode[:]
        bpy.ops.mesh.select_mode(type="VERT")
        bm = bmesh.from_edit_mesh(obj.data)
        bm.select_history.clear()
        bm.verts.ensure_lookup_table()
        bm.faces.ensure_lookup_table()
        uv_layer = bm.loops.layers.uv.verify()

        selected_loops = set()
        for face in bm.faces:
            if face.select:
                for loop in face.loops:
                    if loop[uv_layer].select:
                        selected_loops.add(loop)

        center = self.get_symmetry_center(context, uv_layer, selected_loops)

        center_uvs = []
        negative_uvs = []
        positive_uvs = []
        for loop in selected_loops:
            if loop[uv_layer].select:
                uv = loop[uv_layer].uv
                if self.axis_uv == "X":
                    axis_value = uv.x
                    center_value = center.x
                else:
                    axis_value = uv.y
                    center_value = center.y

                if abs(axis_value - center_value) <= self.threshold_center:
                    if self.axis_uv == "X":
                        uv.x = center_value
                    else:
                        uv.y = center_value
                    center_uvs.append((loop, uv))
                elif axis_value < center_value:
                    negative_uvs.append((loop, uv))
                elif axis_value > center_value:
                    positive_uvs.append((loop, uv))

        direction = self.direction
        if direction == "POSITIVE":
            source_uvs, target_uvs = positive_uvs, negative_uvs
        else:
            source_uvs, target_uvs = negative_uvs, positive_uvs

        kd_tree = kdtree.KDTree(len(source_uvs))
        for i, (_, uv) in enumerate(source_uvs):
            kd_tree.insert(Vector((uv.x, uv.y, 0)), i)
        kd_tree.balance()

        if len(source_uvs) == 0:
            return

        for loop, uv in target_uvs:
            if self.axis_uv == "X":
                mirrored_value = 2 * center.x - uv.x
                mirrored_pos = Vector((mirrored_value, uv.y, 0))
            else:
                mirrored_value = 2 * center.y - uv.y
                mirrored_pos = Vector((uv.x, mirrored_value, 0))

            _, index, dist = kd_tree.find(mirrored_pos)
            if dist <= self.threshold:
                closest_uv = source_uvs[index][1]
                if self.axis_uv == "X":
                    new_value = 2 * center.x - closest_uv.x
                    loop[uv_layer].uv = Vector((new_value, closest_uv.y))
                else:
                    new_value = 2 * center.y - closest_uv.y
                    loop[uv_layer].uv = Vector((closest_uv.x, new_value))

        bmesh.update_edit_mesh(obj.data)
        context.tool_settings.mesh_select_mode = current_mode

    def get_symmetry_center(self, context, uv_layer, loops):
        if self.center == "SELECT":
            original = context.space_data.cursor_location.copy()
            bpy.ops.uv.snap_cursor(target="SELECTED")
            selection_loc = context.space_data.cursor_location.copy()
            bpy.ops.uv.cursor_set(location=original)
            return selection_loc
        elif self.center == "CURSOR":
            return context.space_data.cursor_location.copy()
        else:
            if context.scene.mio3uv.udim:
                return get_tile_co(Vector((0.5, 0.5)), uv_layer, loops)
            else:
                return Vector((0.5, 0.5))

    def draw(self, context):
        layout = self.layout
        row = layout.row()
        row.prop(self, "center", expand=True)
        split = layout.split(factor=0.35)
        split.alignment = "RIGHT"
        split.label(text="Direction")
        row = split.row()
        row.prop(self, "direction", expand=True)
        split = layout.split(factor=0.35)
        split.alignment = "RIGHT"
        split.label(text="Threshold")
        split.prop(self, "threshold", text="")


def register():
    bpy.utils.register_class(MIO3UV_OT_symmetry_snap)


def unregister():
    bpy.utils.unregister_class(MIO3UV_OT_symmetry_snap)
