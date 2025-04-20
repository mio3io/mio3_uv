import bpy
import bmesh
from mathutils import Vector, kdtree
from bpy.props import BoolProperty, FloatProperty, EnumProperty
from ..classes.operator import Mio3UVOperator
from ..utils import get_tile_co
from ..icons import preview_collections


class MIO3UV_OT_symmetrize(Mio3UVOperator):
    bl_idname = "uv.mio3_symmetrize"
    bl_label = "Symmetrize"
    bl_description = "Symmetrize based on 3D space"
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
            context.tool_settings.use_uv_select_sync = False
            context.scene.mio3uv.auto_uv_sync_skip = True

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

        current_mode = context.tool_settings.mesh_select_mode[:]
        context.tool_settings.mesh_select_mode = (True, False, False)

        for obj in self.objects:
            bm = bmesh.from_edit_mesh(obj.data)
            bm.verts.ensure_lookup_table()
            bm.faces.ensure_lookup_table()
            uv_layer = bm.loops.layers.uv.verify()
            original_selected_verts = {v.index for v in bm.verts if v.select}

            self.symmetrize(context, bm, uv_layer, use_uv_select_sync)

            for v in bm.verts:
                v.select = False
            for i in original_selected_verts:
                bm.verts[i].select = True
            bm.select_flush_mode()
            bmesh.update_edit_mesh(obj.data)

        if self.merge:
            bpy.ops.uv.remove_doubles(threshold=self.threshold_uv)

        context.tool_settings.mesh_select_mode = current_mode
        if use_uv_select_sync:
            context.tool_settings.use_uv_select_sync = True
        self.print_time()
        return {"FINISHED"}

    def check_uv_3d_direction(self, uv_layer, sym_center_uv, face_centers, uv_selection):
        uv_axis_index = 0 if self.axis_uv == "X" else 1
        axis_3d_index = {"X": 0, "Y": 1, "Z": 2}[self.axis_3d]

        for face, center in face_centers.items():
            if uv_selection[face]:
                face_uv_center = Vector((0, 0))
                for loop in face.loops:
                    face_uv_center += loop[uv_layer].uv
                face_uv_center /= len(face.loops)
                if self.direction == "POSITIVE":
                    if face_uv_center[uv_axis_index] > sym_center_uv[uv_axis_index]:
                        return "POSITIVE" if center[axis_3d_index] > 0 else "NEGATIVE"
                else:
                    if face_uv_center[uv_axis_index] < sym_center_uv[uv_axis_index]:
                        return "POSITIVE" if center[axis_3d_index] > 0 else "NEGATIVE"

        return self.direction

    def symmetrize(self, context, bm, uv_layer, use_uv_select_sync):
        selected_verts = set()
        selected_loops = set()
        for face in bm.faces:
            if face.select:
                for loop in face.loops:
                    if loop[uv_layer].select:
                        selected_loops.add(loop)
                        if use_uv_select_sync:
                            selected_verts.add(loop.vert)
                            continue
                        for connected_face in loop.vert.link_faces:
                            for fv in connected_face.verts:
                                selected_verts.add(fv)

        self.select_symmetric_verts(bm, selected_verts)

        kd = kdtree.KDTree(len(bm.faces))
        face_centers = {}
        uv_selection = {}
        for i, face in enumerate(bm.faces):
            if face.select:
                face_center = face.calc_center_median()
                face_centers[face] = face_center
                uv_selection[face] = any(l[uv_layer].select for l in face.loops)
                kd.insert(face_center, i)
        kd.balance()

        sym_center_uv = self.get_symmetry_center(context, uv_layer, selected_loops)
        direction_3d = self.check_uv_3d_direction(uv_layer, sym_center_uv, face_centers, uv_selection)

        sym_positions = {v: self.get_symmetric_3d_point(v.co) for v in bm.verts if v.select}
        face_sym_verts = {face: [sym_positions[v] for v in face.verts] for face in bm.faces if face.select}

        for face, center in face_centers.items():
            if uv_selection[face] and self.should_symmetrize(center, direction_3d):
                sym_center = self.get_symmetric_3d_point(center)
                potential_sym_faces = [bm.faces[i] for (_, i, _) in kd.find_n(sym_center, 5)]
                sym_face = self.get_symmetric_face(face, potential_sym_faces, face_sym_verts)
                if not sym_face:
                    continue
                for loop in face.loops:
                    if loop[uv_layer].select:
                        sym_vert = min(
                            sym_face.verts,
                            key=lambda v: (v.co - sym_positions[loop.vert]).length_squared,
                        )
                        for sym_loop in sym_face.loops:
                            if sym_loop.vert == sym_vert:
                                source_uv = loop[uv_layer].uv
                                new_uv = self.get_symmetric_uv_point(source_uv, sym_center_uv)
                                sym_loop[uv_layer].uv = new_uv

    # 対称化化するか判定
    def should_symmetrize(self, point, direction_3d):
        axis_index = {"X": 0, "Y": 1, "Z": 2}[self.axis_3d]
        return (direction_3d == "POSITIVE" and point[axis_index] > 0) or (
            direction_3d == "NEGATIVE" and point[axis_index] < 0
        )

    # 対称的な面を見つける
    def get_symmetric_face(self, face, potential_faces, face_sym_verts):
        face_vert_count = len(face.verts)
        sym_verts = face_sym_verts[face]
        for pot_face in potential_faces:
            if len(pot_face.verts) == face_vert_count:
                if all(any((v.co - sv).length_squared < self.threshold_sq for sv in sym_verts) for v in pot_face.verts):
                    return pot_face
        return None

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

    # 3Dの対称頂点を選択
    def select_symmetric_verts(self, bm, selected_verts):
        kd = kdtree.KDTree(len(bm.verts))
        for i, v in enumerate(bm.verts):
            kd.insert(v.co, i)
        kd.balance()

        for face in bm.faces:
            face.select = False

        for v in selected_verts:
            symm_co = self.get_symmetric_3d_point(v.co)
            co_find = kd.find(symm_co)
            if co_find[2] < self.threshold:
                symm_vert = bm.verts[co_find[1]]
                symm_vert.select = True
            v.select = True
        bm.select_flush_mode()

    def draw(self, context):
        layout = self.layout
        row = layout.row()
        row.prop(self, "center", expand=True)
        split = layout.split(factor=0.35)
        split.alignment ="RIGHT"
        split.label(text="Direction")
        row = split.row()
        row.prop(self, "direction", expand=True)
        split = layout.split(factor=0.35)
        split.alignment ="RIGHT"
        split.label(text="Threshold")
        split.prop(self, "threshold", text="")


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
        split.alignment ="RIGHT"
        split.label(text="Direction")
        row = split.row()
        row.prop(self, "direction", expand=True)
        split = layout.split(factor=0.35)
        split.alignment ="RIGHT"
        split.label(text="Threshold")
        split.prop(self, "threshold", text="")


classes = [MIO3UV_OT_symmetrize, MIO3UV_OT_symmetry_snap]


def register():
    for c in classes:
        bpy.utils.register_class(c)


def unregister():
    for c in classes:
        bpy.utils.unregister_class(c)
