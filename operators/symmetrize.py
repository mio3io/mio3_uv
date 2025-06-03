import bpy
import bmesh
from mathutils import Vector, kdtree
from bpy.types import Context
from bpy.props import BoolProperty, FloatProperty, EnumProperty
from bmesh.types import BMesh
from ..classes import Mio3UVOperator
from ..utils import get_tile_co
from ..icons import preview_collections


class MIO3UV_OT_symmetrize(Mio3UVOperator):
    bl_idname = "uv.mio3_symmetrize"
    bl_label = "Symmetrize"
    bl_description = "Symmetrize based on 3D space"
    bl_options = {"REGISTER", "UNDO"}

    def symmetry_direction_items(self, context: Context):
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
            ("SELECT", "Selection", "Bounding Box Center"),
        ],
        default="GLOBAL",
    )
    direction: EnumProperty(
        name="Direction",
        items=symmetry_direction_items,
        default=1,
    )
    threshold: FloatProperty(
        name="Threshold",
        default=0.001,
        min=0.0001,
        max=0.1,
        precision=4,
        step=0.01,
    )
    merge: BoolProperty(name="Merge by Distance", description="Merge by Distance", default=True)
    stack: BoolProperty(name="Stack Mirror", description="Mirror along the axis and stack the UVs", default=False)
    threshold_uv = 0.00001

    def invoke(self, context, event):
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
        self.start_time()
        self.objects = self.get_selected_objects(context)
        self.threshold_sq = self.threshold * self.threshold

        if not self.objects:
            self.report({"WARNING"}, "Object is not selected")
            return {"CANCELLED"}

        use_uv_select_sync = context.tool_settings.use_uv_select_sync
        if use_uv_select_sync:
            self.sync_uv_from_mesh(context, self.objects)

        if self.axis_3d == "AUTO":
            self.axis_3d = {"X": "X", "Y": "Z"}.get(self.axis_uv, self.axis_uv)

        if self.axis_3d == "X":
            self.get_symmetric_3d_point = lambda co: Vector((-co.x, co.y, co.z))
        elif self.axis_3d == "Y":
            self.get_symmetric_3d_point = lambda co: Vector((co.x, -co.y, co.z))
        else:
            self.get_symmetric_3d_point = lambda co: Vector((co.x, co.y, -co.z))

        if self.axis_uv == "X":
            self.get_symmetric_uv_point = lambda uv, center: Vector((2 * center.x - uv.x, uv.y))
        else:
            self.get_symmetric_uv_point = lambda uv, center: Vector((uv.x, 2 * center.y - uv.y))

        self.uv_axis_index = 0 if self.axis_uv == "X" else 1
        self.axis_3d_index = {"X": 0, "Y": 1, "Z": 2}[self.axis_3d]

        mesh_select_mode = self.store_mesh_select_mode(context, mode=(True, False, False))

        for obj in self.objects:
            bm = bmesh.from_edit_mesh(obj.data)
            bm.verts.ensure_lookup_table()
            bm.faces.ensure_lookup_table()
            uv_layer = bm.loops.layers.uv.verify()
            original_selected_verts = {v.index for v in bm.verts if v.select}

            self.symmetrize(context, bm, uv_layer)

            for v in bm.verts:
                v.select = False
            for i in original_selected_verts:
                bm.verts[i].select = True
            bm.select_flush_mode()
            bmesh.update_edit_mesh(obj.data)

        if self.merge:
            bpy.ops.uv.remove_doubles(threshold=self.threshold_uv)

        self.restore_mesh_select_mode(context, mesh_select_mode)
        self.print_time()
        return {"FINISHED"}

    def symmetrize(self, context, bm, uv_layer):
        threshold_sq = self.threshold_sq
        axis_3d = self.axis_3d

        target_faces, target_verts, source_loops = self.find_targets(bm, uv_layer)

        kd = kdtree.KDTree(len(bm.faces))
        face_centers = {}
        for i, face in enumerate(bm.faces):
            if face in target_faces:
                face_center = face.calc_center_median()
                face_centers[face] = face_center
                kd.insert(face_center, i)
        kd.balance()

        sym_center_uv = self.get_symmetry_center(context, uv_layer, source_loops)
        direction_3d = self.check_uv_3d_direction(uv_layer, sym_center_uv, face_centers, target_faces)

        sym_positions = {v: self.get_symmetric_3d_point(v.co) for v in target_verts}
        face_sym_verts = {face: [sym_positions[v] for v in face.verts if v in sym_positions] for face in target_faces}

        get_symmetric_uv_point = self.get_symmetric_uv_point
        get_symmetric_face = self.get_symmetric_face
        stack = self.stack

        for face in target_faces:
            center = face_centers[face]
            sym_center = self.get_symmetric_3d_point(center)
            if self.should_symmetrize(center, direction_3d, axis_3d):
                potential_sym_faces = [bm.faces[i] for (_, i, _) in kd.find_n(sym_center, 5)]
                sym_face = get_symmetric_face(potential_sym_faces, face_sym_verts[face], threshold_sq)
                if not sym_face:
                    continue
                for loop in face.loops:
                    loop_uv = loop[uv_layer]
                    sym_vert = min(sym_face.verts, key=lambda v: (v.co - sym_positions[loop.vert]).length_squared)
                    for sym_loop in sym_face.loops:
                        if sym_loop.vert == sym_vert:
                            if sym_loop[uv_layer].select or loop_uv.select:
                                if stack:
                                    sym_loop[uv_layer].uv = loop[uv_layer].uv
                                else:
                                    sym_loop[uv_layer].uv = get_symmetric_uv_point(loop_uv.uv, sym_center_uv)

    # self.direction側にあるUV面がどの方向にあるか調べる
    def check_uv_3d_direction(self, uv_layer, sym_center_uv, face_centers, target_faces):
        uv_axis_index = self.uv_axis_index
        axis_3d_index = self.axis_3d_index
        for face in target_faces:
            center = face_centers[face]
            face_uv_center = Vector((0, 0))
            for loop in face.loops:
                face_uv_center += loop[uv_layer].uv
            face_uv_center /= len(face.loops)

            if self.is_flipped(face, uv_layer):
                continue

            if self.direction == "POSITIVE":
                if face_uv_center[uv_axis_index] > sym_center_uv[uv_axis_index]:
                    return "POSITIVE" if center[axis_3d_index] > 0 else "NEGATIVE"
            else:
                if face_uv_center[uv_axis_index] < sym_center_uv[uv_axis_index]:
                    return "POSITIVE" if center[axis_3d_index] > 0 else "NEGATIVE"
        return self.direction

    @staticmethod
    def is_flipped(face, uv_layer):
        prev_uv = face.loops[-1][uv_layer].uv
        area = 0.0
        for loop in face.loops:
            uv = loop[uv_layer].uv
            area += prev_uv.x * uv.y - uv.x * prev_uv.y
            prev_uv = uv
        return area < -1e-7

    # 対称化化するか判定
    @staticmethod
    def should_symmetrize(point, direction_3d, axis_3d):
        axis_index = {"X": 0, "Y": 1, "Z": 2}[axis_3d]
        return (direction_3d == "POSITIVE" and point[axis_index] > 0) or (
            direction_3d == "NEGATIVE" and point[axis_index] < 0
        )

    # 対称的な面を見つける
    @staticmethod
    def get_symmetric_face(potential_faces, sym_verts, threshold_sq):
        for pot_face in potential_faces:
            if all(any((v.co - sv).length_squared < threshold_sq for sv in sym_verts) for v in pot_face.verts):
                return pot_face
        return None

    def get_symmetry_center(self, context: Context, uv_layer, loops):
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

    # 対象の頂点を収集
    def find_targets(self, bm: BMesh, uv_layer):
        kd = kdtree.KDTree(len(bm.verts))
        for i, v in enumerate(bm.verts):
            kd.insert(v.co, i)
        kd.balance()

        source_faces = set()
        source_verts = set()
        source_loops = set()
        for face in bm.faces:
            if face.select:
                for loop in face.loops:
                    if loop[uv_layer].select:
                        source_faces.add(face)
                        source_loops.add(loop)
                        for link_face in loop.vert.link_faces:
                            for fv in link_face.verts:
                                source_verts.add(fv)

        threshold = self.threshold
        target_faces = set()
        target_verts = set()
        for v in source_verts:
            symm_co = self.get_symmetric_3d_point(v.co)
            co_find = kd.find(symm_co)
            if co_find[2] < threshold:
                symm_vert = bm.verts[co_find[1]]
                target_verts.add(symm_vert)
                target_faces.update(symm_vert.link_faces)

        target_faces.update(source_faces)
        target_verts.update(source_verts)
        return target_faces, target_verts, source_loops

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
        split = layout.split(factor=0.35)
        split.label(text="")
        split.prop(self, "stack")


def register():
    bpy.utils.register_class(MIO3UV_OT_symmetrize)


def unregister():
    bpy.utils.unregister_class(MIO3UV_OT_symmetrize)
