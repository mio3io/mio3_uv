import bpy
import bmesh
from mathutils import Vector, kdtree
from bpy.types import Context
from bpy.props import BoolProperty, FloatProperty, EnumProperty
from bmesh.types import BMesh
from ..classes import Mio3UVOperator
from ..utils.utils import get_tile_co
from ..globals import get_preferences
from ..icons import icons


class MIO3UV_OT_symmetrize(Mio3UVOperator):
    bl_idname = "uv.mio3_symmetrize"
    bl_label = "Symmetrize"
    bl_description = "Symmetrize based on 3D space"
    bl_options = {"REGISTER", "UNDO"}

    def symmetry_direction_items(self, context: Context):
        symmetry_uv_axis = context.scene.mio3uv.symmetry_uv_axis
        if symmetry_uv_axis == "X":
            return [
                ("NEGATIVE", "-X", "", icons.symm_n_x, 0),
                ("AUTO", "Auto", "The direction is automatically determined based on the UV selection", icons.auto, 1),
                ("POSITIVE", "+X", "", icons.symm_p_x, 2),
            ]
        else:
            return [
                ("NEGATIVE", "-Y", "", icons.symm_n_y, 0),
                ("AUTO", "Auto", "The direction is automatically determined based on the UV selection", icons.auto, 1),
                ("POSITIVE", "+Y", "", icons.symm_p_y, 2),
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
    lock_direction: BoolProperty(
        name="Lock Direction",
        description="Does not reference the orientation of the face in 3D space",
    )
    threshold: FloatProperty(
        name="Threshold",
        default=0.001,
        min=0.0001,
        max=0.1,
        precision=3,
        step=0.1,
    )
    merge: BoolProperty(name="Merge by Distance", description="Merge by Distance", default=True)
    stack: BoolProperty(name="Stack Mirror", description="Mirror along the axis and stack the UVs", default=False)

    _threshold_uv = 0.00001

    def invoke(self, context, event):
        self.axis_uv = context.scene.mio3uv.symmetry_uv_axis
        self.axis_3d = context.scene.mio3uv.symmetry_3d_axis
        return self.execute(context)

    def check(self, context):
        self.axis_uv = context.scene.mio3uv.symmetry_uv_axis
        self.axis_3d = context.scene.mio3uv.symmetry_3d_axis
        return True

    def execute(self, context):
        self.start_time()
        objects = self.get_selected_objects(context)
        self.threshold_sq = self.threshold * self.threshold
        use_uv_select_sync = context.tool_settings.use_uv_select_sync

        if not objects:
            self.report({"WARNING"}, "Object is not selected")
            return {"CANCELLED"}

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

        for obj in objects:
            bm = bmesh.from_edit_mesh(obj.data)
            bm.verts.ensure_lookup_table()
            bm.faces.ensure_lookup_table()
            uv_layer = bm.loops.layers.uv.verify()
            if use_uv_select_sync and not bm.uv_select_sync_valid:
                bm.uv_select_sync_from_mesh()

            self.symmetrize(context, bm, uv_layer, use_uv_select_sync)
            bmesh.update_edit_mesh(obj.data)

        if self.merge:
            bpy.ops.uv.remove_doubles(threshold=self._threshold_uv)

        self.print_time()
        return {"FINISHED"}

    def symmetrize(self, context, bm, uv_layer, use_uv_select_sync):
        axis_3d = self.axis_3d
        stack = self.stack
        threshold_sq = self.threshold_sq
        get_symmetric_3d_point = self.get_symmetric_3d_point
        get_symmetric_uv_point = self.get_symmetric_uv_point
        should_symmetrize = self.should_symmetrize
        find_sym_face_strict = self.find_sym_face_strict

        target_faces, source_faces, source_loops = self.find_targets(bm, use_uv_select_sync)
        target_faces = list(target_faces)

        kd = kdtree.KDTree(len(target_faces))
        face_centers = {}
        for i, face in enumerate(target_faces):
            face_center = face.calc_center_median()
            face_centers[face] = face_center
            kd.insert(face_center, i)
        kd.balance()

        sym_center_uv = self.get_symmetry_center(context, uv_layer, source_loops)
        direction_3d = self.check_uv_3d_direction(uv_layer, sym_center_uv, face_centers, source_faces)

        target_verts = set()
        sym_positions = {}
        sym_loop_maps = {}
        for face in target_faces:
            sym_loop_maps[face] = {loop.vert: loop for loop in face.loops}
            for v in face.verts:
                if v not in target_verts:
                    target_verts.add(v)
                    sym_positions[v] = get_symmetric_3d_point(v.co)

        sym_verts = {f: [sym_positions[v] for v in f.verts if v in sym_positions] for f in target_faces}

        for face in target_faces:
            center = face_centers[face]
            sym_center = get_symmetric_3d_point(center)
            if should_symmetrize(center, direction_3d, axis_3d):
                sym_face = find_sym_face_strict(target_faces, kd, sym_center, sym_verts[face], threshold_sq)
                if not sym_face:
                    continue
                sym_face_loops = sym_loop_maps[sym_face]
                for loop in face.loops:
                    loop_uv = loop[uv_layer]
                    sym_vert = min(sym_face.verts, key=lambda v: (v.co - sym_positions[loop.vert]).length_squared)
                    sym_loop = sym_face_loops.get(sym_vert)
                    if sym_loop and (sym_loop.uv_select_vert or loop.uv_select_vert):
                        if stack:
                            sym_loop[uv_layer].uv = loop_uv.uv
                        else:
                            sym_loop[uv_layer].uv = get_symmetric_uv_point(loop_uv.uv, sym_center_uv)

    # self.direction側にあるUV面がどの方向にあるか調べる
    def check_uv_3d_direction(self, uv_layer, sym_center_uv, face_centers, source_faces):
        prefs = get_preferences()
        priority_direction = self.direction # 現在の優先

        if self.lock_direction:
            return self.direction

        if self.direction == "AUTO":
            direction = self.detect_selected_direction(uv_layer, sym_center_uv, face_centers, source_faces)
            if direction:
                return direction
            priority_direction = prefs.default_symmetry_priority

        uv_axis_index = self.uv_axis_index
        axis_3d_index = self.axis_3d_index

        for face in source_faces:
            if self.is_flipped(face, uv_layer):
                continue
            center = face_centers[face]
            face_uv_center = Vector((0, 0))
            for loop in face.loops:
                face_uv_center += loop[uv_layer].uv
            face_uv_center /= len(face.loops)

            if priority_direction == "POSITIVE":
                if face_uv_center[uv_axis_index] > sym_center_uv[uv_axis_index]:
                    return "POSITIVE" if center[axis_3d_index] > 0 else "NEGATIVE"
            else:
                if face_uv_center[uv_axis_index] < sym_center_uv[uv_axis_index]:
                    return "POSITIVE" if center[axis_3d_index] > 0 else "NEGATIVE"
        return priority_direction

    def detect_selected_direction(self, uv_layer, sym_center_uv, face_centers, source_faces):
        axis_3d_index = self.axis_3d_index
        positive_count = 0
        negative_count = 0

        if self.lock_direction:
            uv_axis_index = self.uv_axis_index
            for face in source_faces:
                if self.is_flipped(face, uv_layer):
                    continue

                face_uv_center = Vector((0, 0))
                for loop in face.loops:
                    face_uv_center += loop[uv_layer].uv
                face_uv_center /= len(face.loops)

                direction = "POSITIVE" if face_uv_center[uv_axis_index] > sym_center_uv[uv_axis_index] else "NEGATIVE"
                if direction == "POSITIVE":
                    positive_count += 1
                else:
                    negative_count += 1
        else:
            for face in source_faces:
                center = face_centers.get(face)
                if center is None:
                    continue

                direction = "POSITIVE" if center[axis_3d_index] > 0 else "NEGATIVE"
                if direction == "POSITIVE":
                    positive_count += 1
                else:
                    negative_count += 1

        if positive_count == negative_count:
            return None

        return "POSITIVE" if positive_count > negative_count else "NEGATIVE"

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

    # 対称面を見つける（頂点位置の一致も考慮する＠ミラーで三角の割が違い、近くに別の面があるケースを考慮）
    @staticmethod
    def find_sym_face_strict(target_faces, kd, sym_center, sym_verts, threshold_sq):
        for _, i, _ in kd.find_n(sym_center, 5):
            pot_face = target_faces[i]
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
    def find_targets(self, bm: BMesh, use_uv_select_sync):
        kd = kdtree.KDTree(len(bm.verts))
        for i, v in enumerate(bm.verts):
            kd.insert(v.co, i)
        kd.balance()

        source_faces = set()
        source_verts = set()
        source_loops = set()
        for face in bm.faces:
            if use_uv_select_sync:
                if face.hide:
                    continue
            else:
                if not face.select:
                    continue

            for loop in face.loops:
                if loop.vert.hide:
                    continue

                if loop.uv_select_vert:
                    source_faces.add(face)
                    source_loops.add(loop)
                    source_verts.add(loop.vert)

        threshold = self.threshold
        symmetric_faces = set()
        for v in source_verts:
            symm_co = self.get_symmetric_3d_point(v.co)
            co_find = kd.find(symm_co)
            if co_find[2] < threshold:
                symm_vert = bm.verts[co_find[1]]
                if use_uv_select_sync:
                    symmetric_faces.update(face for face in symm_vert.link_faces if not face.hide)
                else:
                    symmetric_faces.update(face for face in symm_vert.link_faces if face.select)

        target_face = symmetric_faces | source_faces
        return target_face, source_faces, source_loops

    def draw(self, context):
        layout = self.layout
        row = layout.row()
        row.prop(self, "center", expand=True)
        split = layout.split(factor=0.32)
        split.alignment = "RIGHT"
        split.label(text="Threshold")
        split.prop(self, "threshold", text="")

        split = layout.split(factor=0.32)
        split.alignment = "RIGHT"
        split.label(text="Direction")
        row = split.row()
        row.prop(self, "direction", expand=True)
        split = layout.split(factor=0.32)
        split.label(text="")
        split.prop(self, "lock_direction")
        split = layout.split(factor=0.32)
        split.label(text="")
        split.prop(self, "stack")

def register():
    bpy.utils.register_class(MIO3UV_OT_symmetrize)


def unregister():
    bpy.utils.unregister_class(MIO3UV_OT_symmetrize)
