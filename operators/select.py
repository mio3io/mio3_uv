import bpy
import bmesh
import math
from mathutils import Vector, kdtree
from bpy.props import BoolProperty, FloatProperty, EnumProperty
from ..classes import UVIslandManager, Mio3UVOperator
from ..utils.utils import uv_select_set_face, uv_select_set_all


class MIO3UV_OT_auto_uv_sync(bpy.types.Operator):
    bl_idname = "uv.mio3_auto_uv_sync"
    bl_label = "Auto UV Sync"
    bl_description = "Auto UV Sync"
    bl_options = {"REGISTER", "UNDO", "INTERNAL"}

    def execute(self, context):
        selected_objects = [obj for obj in context.objects_in_mode if obj.type == "MESH"]
        if context.scene.tool_settings.use_uv_select_sync:
            # 選択同期：UVからメッシュに選択状態を同期する
            for obj in selected_objects:
                bm = bmesh.from_edit_mesh(obj.data)
                if bm.uv_select_sync_valid:
                    bm.uv_select_sync_to_mesh()
                bmesh.update_edit_mesh(obj.data)
        else:
            # 同期解除：メッシュをすべて選択
            for obj in selected_objects:
                bm = bmesh.from_edit_mesh(obj.data)
                for face in bm.faces:
                    face.select = True
                bm.select_flush(True)
                bmesh.update_edit_mesh(obj.data)
        return {"FINISHED"}


class MIO3UV_OT_select_half(Mio3UVOperator):
    bl_idname = "uv.mio3_select_half"
    bl_label = "Select Half"
    bl_description = "Select UVs on one side of the axis in 3D space"
    bl_options = {"REGISTER", "UNDO"}

    direction: EnumProperty(
        name="Direction",
        items=[
            ("NEGATIVE_X", "- X", ""),
            ("POSITIVE_X", "+ X", ""),
            ("NEGATIVE_Y", "- Y", ""),
            ("POSITIVE_Y", "+ Y", ""),
            ("NEGATIVE_Z", "- Z", ""),
            ("POSITIVE_Z", "+ Z", ""),
        ],
        default="NEGATIVE_X",
    )

    orientation: EnumProperty(
        name="Orientation",
        items=[("LOCAL", "Local", ""), ("GLOBAL", "Global", "")],
        default="LOCAL",
    )

    def execute(self, context):
        self.start_time()

        objects = self.get_selected_objects(context)
        use_uv_select_sync = context.tool_settings.use_uv_select_sync

        use_global = self.orientation == "GLOBAL"
        is_negative = self.direction.startswith("NEGATIVE")
        axis = self.direction[-1].lower()

        for obj in objects:
            bm = bmesh.from_edit_mesh(obj.data)
            if use_uv_select_sync and not bm.uv_select_sync_valid:
                bm.uv_select_sync_from_mesh()

            if use_uv_select_sync:
                for face in bm.faces:
                    face.select = False

            uv_select_set_all(bm.faces, False)

            for face in bm.faces:
                if use_global:
                    face_center = obj.matrix_world @ face.calc_center_median()
                else:
                    face_center = face.calc_center_median()

                coordinate = getattr(face_center, axis)

                if (is_negative and coordinate < 0) or (not is_negative and coordinate >= 0):
                    face.select = True
                    uv_select_set_face(face, True)

            bmesh.update_edit_mesh(obj.data)

        self.print_time()
        return {"FINISHED"}


class MIO3UV_OT_select_similar(Mio3UVOperator):
    bl_idname = "uv.mio3_select_similar"
    bl_label = "Similar"
    bl_description = "Select Similar"
    bl_options = {"REGISTER", "UNDO"}

    check_edges: BoolProperty(name="Check Edges", description="", default=True)

    def execute(self, context):
        self.start_time()
        objects = self.get_selected_objects(context)
        use_uv_select_sync = context.tool_settings.use_uv_select_sync

        island_manager = UVIslandManager(objects, sync=use_uv_select_sync, find_all=True)

        check_edges = self.check_edges
        source_island = None
        source_face_count = 0
        source_edge_count = 0
        for island in island_manager.islands:
            if any(all(loop.uv_select_vert for loop in face.loops) for face in island.faces):
                source_island = island
                source_face_count = len(source_island.faces)
                source_edge_count = self.get_island_edge_count(source_island) if check_edges else None
                break

        if not source_island:
            return {"CANCELLED"}

        source_island.uv_select_set_all(True)

        for island in island_manager.islands:
            if island == source_island:
                continue
            island.uv_select_set_all(False)
            if not self.is_different(island, source_face_count, source_edge_count):
                island.uv_select_set_all(True)

        island_manager.update_uvmeshes(True)

        self.print_time()
        return {"FINISHED"}

    def get_island_edge_count(self, island):
        return len({edge for face in island.faces for edge in face.edges})

    def is_different(self, island, base_face_count, base_edge_count):
        if len(island.faces) != base_face_count:
            return True
        if self.check_edges and self.get_island_edge_count(island) != base_edge_count:
            return True
        return False


class MIO3UV_OT_select_mirror3d(Mio3UVOperator):
    bl_idname = "uv.mio3_select_mirror3d"
    bl_label = "Mirror"
    bl_description = "Select Mirror 3D"
    bl_options = {"REGISTER", "UNDO"}

    threshold: FloatProperty(
        name="Threshold",
        default=0.001,
        min=0.0001,
        max=0.1,
        precision=3,
        step=0.1,
    )
    expand: BoolProperty(name="Expand", default=True)
    fast: BoolProperty(
        name="Fast Mode",
        description="Performs a simplified search for mirrored UVs\n(may not work correctly if multiple faces are too close together in 3D space",
        default=True,
    )

    def execute(self, context):
        self.start_time()
        objects = self.get_selected_objects(context)
        self.threshold_sq = self.threshold * self.threshold
        use_uv_select_sync = context.tool_settings.use_uv_select_sync

        for obj in objects:
            bm = bmesh.from_edit_mesh(obj.data)
            bm.select_mode = {"VERT"}
            bm.verts.ensure_lookup_table()
            bm.faces.ensure_lookup_table()
            if use_uv_select_sync and not bm.uv_select_sync_valid:
                bm.uv_select_sync_from_mesh()

            self.select_mirror(bm, use_uv_select_sync)

            if bm.uv_select_sync_valid:
                bm.uv_select_sync_to_mesh()

            bmesh.update_edit_mesh(obj.data)

        self.print_time()
        return {"FINISHED"}

    def select_mirror(self, bm, use_uv_select_sync):
        target_faces, source_faces, source_verts = self.find_targets(bm, use_uv_select_sync)

        kd = kdtree.KDTree(len(bm.faces))
        face_centers = {}
        for i, face in enumerate(bm.faces):
            if face in target_faces:
                face_center = face.calc_center_median()
                face_centers[face] = face_center
                kd.insert(face_center, i)
        kd.balance()

        fast, expand = self.fast, self.expand
        threshold, threshold_sq = self.threshold, self.threshold * self.threshold
        get_symmetric_3d_point = self.get_symmetric_3d_point
        find_sym_face_single = self.find_sym_face_single
        find_sym_face_strict = self.find_sym_face_strict

        sym_positions = {v: get_symmetric_3d_point(v.co) for v in source_verts}
        if fast:
            sym_verts = {}
        else:
            sym_verts = {f: [sym_positions[v] for v in f.verts if v in sym_positions] for f in source_faces}

        processed = set()
        for face in source_faces:
            sym_center = get_symmetric_3d_point(face_centers[face])
            if fast:
                sym_face = find_sym_face_single(bm, kd, sym_center, threshold)
            else:
                sym_face = find_sym_face_strict(bm, kd, sym_center, sym_verts[face], threshold_sq)
            if not sym_face:
                continue
            for loop in face.loops:
                if loop in processed:
                    continue
                if loop.uv_select_vert:
                    sym_vert = min(sym_face.verts, key=lambda v: (v.co - sym_positions[loop.vert]).length_squared)
                    for sym_loop in sym_face.loops:
                        if sym_loop in processed:
                            continue
                        if sym_loop.vert == sym_vert:
                            sym_loop.uv_select_vert = True
                            processed.add(sym_loop)
                            break
                if not expand:
                    loop.uv_select_vert = False
                processed.add(loop)

        for face in target_faces:
            for loop in face.loops:
                if loop.uv_select_vert and loop.link_loop_next.uv_select_vert:
                    loop.uv_select_edge = True
                else:
                    loop.uv_select_edge = False

        if bm.uv_select_sync_valid:
            bm.uv_select_flush(True)

    @staticmethod
    def get_symmetric_3d_point(co):
        return Vector((-co.x, co.y, co.z))

    # 対称面を見つける
    @staticmethod
    def find_sym_face_single(bm, kd, sym_center, threshold):
        _, i, dist = kd.find(sym_center)
        if dist > threshold:
            return None
        return bm.faces[i]

    # 対称面を見つける（頂点位置の一致も考慮する＠ミラーで三角の割が違い、近くに別の面があるケースを考慮）
    @staticmethod
    def find_sym_face_strict(bm, kd, sym_center, sym_verts, threshold_sq):
        potential_faces = [bm.faces[i] for (_, i, _) in kd.find_n(sym_center, 5)]
        for pot_face in potential_faces:
            if all(any((v.co - sv).length_squared < threshold_sq for sv in sym_verts) for v in pot_face.verts):
                return pot_face
        return None

    # 対象の頂点を収集
    def find_targets(self, bm, use_uv_select_sync):
        kd = kdtree.KDTree(len(bm.verts))
        for i, v in enumerate(bm.verts):
            kd.insert(v.co, i)
        kd.balance()

        source_faces = set()
        source_verts = set()
        source_face_verts = set()
        for face in bm.faces:
            if not face.select and not use_uv_select_sync:
                continue

            for loop in face.loops:
                if loop.uv_select_vert:
                    source_faces.add(face)
                    source_verts.add(loop.vert)
                    source_face_verts.update(face.verts)  # extend

        threshold = self.threshold
        symmetric_faces = set()
        for v in source_verts:
            symm_co = self.get_symmetric_3d_point(v.co)
            co_find = kd.find(symm_co)
            if co_find[2] < threshold:
                symm_vert = bm.verts[co_find[1]]
                symmetric_faces.update(symm_vert.link_faces)

        target_faces = source_faces | symmetric_faces
        return target_faces, source_faces, source_face_verts


class MIO3UV_OT_select_edge(Mio3UVOperator):
    bl_idname = "uv.mio3_select_edge"
    bl_label = "Edges"
    bl_description = "Select edges based on their direction in UV space"
    bl_options = {"REGISTER", "UNDO"}

    method: EnumProperty(
        name="Method",
        items=[
            ("BOUNDARY", "Boundary", "Select boundary edges"),
            ("Y", "Vertical", "Select only vertical edges"),
            ("X", "Horizontal", "Select only horizontal edges"),
        ],
        default="BOUNDARY",
    )
    threshold: FloatProperty(name="Threshold", default=0.3, min=0.01, max=0.8, step=1)

    def draw(self, context):
        layout = self.layout
        layout.row().prop(self, "method", expand=True)
        layout.use_property_split = True
        layout.use_property_decorate = False
        col = layout.column()
        col.prop(self, "threshold")
        if self.method == "BOUNDARY":
            col.enabled = False

    def execute(self, context):
        self.start_time()

        use_uv_select_sync = context.tool_settings.use_uv_select_sync
        objects = self.get_selected_objects(context)

        if self.method == "BOUNDARY":
            self.select_boundary(objects, use_uv_select_sync)
        else:
            if use_uv_select_sync:
                context.tool_settings.mesh_select_mode = (False, True, False)
            else:
                context.tool_settings.uv_select_mode = "EDGE"
            self.select_direction(objects, use_uv_select_sync)

        self.print_time()
        return {"FINISHED"}
    
    def select_boundary(self, objects, use_uv_select_sync):
        check_selected = self.check_selected_face_objects(objects)
        island_manager = UVIslandManager(objects, sync=use_uv_select_sync, find_all=True)

        for island in island_manager.islands:
            uv_layer = island.uv_layer
            island_faces = set(island.faces)
            uv_boundary_edges = self.find_uv_boundary_edges(island_faces, uv_layer)

            uv_to_loops = {}
            selected_uv_coords = set()
            selected_edges = set()
            for face in island.faces:
                for loop in face.loops:
                    uv_key = tuple(loop[uv_layer].uv)
                    bucket = uv_to_loops.get(uv_key)
                    if bucket is None:
                        bucket = []
                        uv_to_loops[uv_key] = bucket
                    bucket.append(loop)

                    if check_selected:
                        if loop.uv_select_vert:
                            selected_uv_coords.add(uv_key)
                        if loop.uv_select_edge:
                            selected_edges.add(loop.edge)
                    else:
                        selected_uv_coords.add(uv_key)
                        selected_edges.add(loop.edge)

            island.uv_select_set_all(False)

            for uv_key in selected_uv_coords:
                loops = uv_to_loops[uv_key]
                for loop in loops:
                    edge = loop.edge
                    if edge in uv_boundary_edges:
                        if edge in selected_edges:
                            loop.uv_select_edge = True
                        for shared_loop in loops:
                            shared_loop.uv_select_vert = True
                        break
        island_manager.update_uvmeshes(True)

    @staticmethod
    def is_uv_continuous(loop, linked_loop, uv_layer, eps2):
        a = loop[uv_layer].uv
        b = loop.link_loop_next[uv_layer].uv
        c = linked_loop[uv_layer].uv
        d = linked_loop.link_loop_next[uv_layer].uv

        if loop.vert is linked_loop.vert:
            du = a.x - c.x
            dv = a.y - c.y
            if du * du + dv * dv > eps2:
                return False
            du = b.x - d.x
            dv = b.y - d.y
        else:
            du = a.x - d.x
            dv = a.y - d.y
            if du * du + dv * dv > eps2:
                return False
            du = b.x - c.x
            dv = b.y - c.y

        return du * du + dv * dv <= eps2

    @classmethod
    def find_uv_boundary_edges(cls, island_faces, uv_layer):
        eps_eq = 1e-14
        island_edges = {edge for face in island_faces for edge in face.edges}
        uv_boundary_edges = set()
        for edge in island_edges:
            island_loops = [ll for ll in edge.link_loops if ll.face in island_faces]
            is_boundary = False

            if len(island_loops) != 2:
                is_boundary = True
            else:
                loop_a, loop_b = island_loops
                if loop_a.face is loop_b.face:
                    is_boundary = True
                else:
                    is_boundary = not cls.is_uv_continuous(loop_a, loop_b, uv_layer, eps_eq)

            if is_boundary:
                uv_boundary_edges.add(edge)
        return uv_boundary_edges

    def select_direction(self, objects, use_uv_select_sync):
        check_selected = self.check_selected_face_objects(objects)
        island_manager = UVIslandManager(objects, sync=use_uv_select_sync, find_all=True)

        axis = self.method

        for island in island_manager.islands:
            uv_to_loops = {}
            uv_layer = island.uv_layer
            selected_edges = set()

            for face in island.faces:
                for loop in face.loops:
                    uv_key = tuple(loop[uv_layer].uv)
                    bucket = uv_to_loops.get(uv_key)
                    if bucket is None:
                        bucket = []
                        uv_to_loops[uv_key] = bucket
                    bucket.append(loop)

                    if check_selected:
                        if loop.uv_select_edge:
                            selected_edges.add(loop.edge)
                    else:
                        selected_edges.add(loop.edge)

            island.uv_select_set_all(False)

            for edge in selected_edges:
                for loop in edge.link_loops:
                    if loop.face not in island.faces:
                        continue

                    if self.is_direction(loop, axis, uv_layer):
                        for shared_loop in edge.link_loops:
                            if shared_loop.face in island.faces:
                                shared_loop.uv_select_edge = True
                                for uv_loops in (
                                    uv_to_loops[tuple(shared_loop[uv_layer].uv)],
                                    uv_to_loops[tuple(shared_loop.link_loop_next[uv_layer].uv)],
                                ):
                                    for uv_loop in uv_loops:
                                        uv_loop.uv_select_vert = True
                        break

        island_manager.update_uvmeshes(True)

    def is_direction(self, loop, axis, uv_layer):
        uv1 = loop[uv_layer].uv
        uv2 = loop.link_loop_next[uv_layer].uv
        edge_vector = uv2 - uv1
        if edge_vector.length < 1e-7:
            return False

        angle = math.atan2(edge_vector.y, edge_vector.x)
        if axis == "X":
            return abs(math.sin(angle)) < self.threshold
        else:
            return abs(math.cos(angle)) < self.threshold


class MIO3UV_OT_select_zero(Mio3UVOperator, bpy.types.Operator):
    bl_idname = "uv.mio3_select_zero"
    bl_label = "No Region"
    bl_description = "Select Zero Area UV Faces"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        self.start_time()
        objects = self.get_selected_objects(context)
        use_uv_select_sync = context.tool_settings.use_uv_select_sync

        for obj in objects:
            bm = bmesh.from_edit_mesh(obj.data)
            uv_layer = bm.loops.layers.uv.verify()

            if use_uv_select_sync and not bm.uv_select_sync_valid:
                bm.uv_select_sync_from_mesh()

            if use_uv_select_sync:
                for face in bm.faces:
                    face.select = False

            uv_select_set_all(bm.faces, False)

            for face in bm.faces:
                if not face.select and not use_uv_select_sync:
                    continue

                face_uvs = [loop[uv_layer].uv.copy() for loop in face.loops]

                if len(face_uvs) >= 3:
                    a, b, c = face_uvs[:3]
                    area = abs((b.x - a.x) * (c.y - a.y) - (c.x - a.x) * (b.y - a.y)) * 0.5
                else:
                    area = 0.0

                if area < 1e-8:
                    face.select = True
                    uv_select_set_face(face, True)

            bmesh.update_edit_mesh(obj.data)

        self.print_time()
        return {"FINISHED"}


class MIO3UV_OT_select_flipped_faces(Mio3UVOperator):
    bl_idname = "uv.mio3_select_flipped_faces"
    bl_label = "Flipped"
    bl_description = "Select Flipped UV Faces"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        self.start_time()
        objects = self.get_selected_objects(context)
        use_uv_select_sync = context.tool_settings.use_uv_select_sync

        for obj in objects:
            bm = bmesh.from_edit_mesh(obj.data)
            uv_layer = bm.loops.layers.uv.verify()

            if use_uv_select_sync and not bm.uv_select_sync_valid:
                bm.uv_select_sync_from_mesh()

            if use_uv_select_sync:
                for face in bm.faces:
                    face.select = False

            uv_select_set_all(bm.faces, False)

            for face in bm.faces:
                if not face.select and not use_uv_select_sync:
                    continue

                face_uvs = [loop[uv_layer].uv for loop in face.loops]

                area = 0
                for i in range(len(face_uvs)):
                    j = (i + 1) % len(face_uvs)
                    area += face_uvs[i].x * face_uvs[j].y - face_uvs[j].x * face_uvs[i].y
                area *= 0.5

                threshold = 1e-7
                is_flipped = area < -threshold

                if is_flipped:
                    face.select = True
                    uv_select_set_face(face, True)

            bmesh.update_edit_mesh(obj.data)

        self.print_time()
        return {"FINISHED"}


classes = [
    MIO3UV_OT_auto_uv_sync,
    MIO3UV_OT_select_half,
    MIO3UV_OT_select_similar,
    MIO3UV_OT_select_mirror3d,
    MIO3UV_OT_select_edge,
    MIO3UV_OT_select_flipped_faces,
    MIO3UV_OT_select_zero,
]


def register():
    for c in classes:
        bpy.utils.register_class(c)


def unregister():
    for c in classes:
        bpy.utils.unregister_class(c)
