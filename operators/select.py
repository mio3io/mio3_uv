import bpy
import bmesh
import math
from mathutils import Vector, kdtree
from bpy.props import BoolProperty, FloatProperty, EnumProperty
from ..classes.uv import UVIslandManager
from ..classes.operator import Mio3UVOperator
from ..utils import sync_uv_from_mesh_obj, sync_mesh_from_uv_obj


class MIO3UV_OT_auto_uv_sync(bpy.types.Operator):
    bl_idname = "uv.mio3_auto_uv_sync"
    bl_label = "Auto UV Sync"
    bl_description = "Auto UV Sync"
    bl_options = {"REGISTER", "UNDO", "INTERNAL"}

    def execute(self, context):
        selected_objects = [obj for obj in context.objects_in_mode if obj.type == "MESH"]
        if context.scene.tool_settings.use_uv_select_sync:
            for obj in selected_objects:
                sync_mesh_from_uv_obj(obj)
        else:
            for obj in selected_objects:
                sync_uv_from_mesh_obj(obj)
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
        self.objects = self.get_selected_objects(context)

        try:
            bpy.ops.uv.select_all("INVOKE_DEFAULT", action="DESELECT")
        except:
            pass

        for obj in self.objects:
            bm = bmesh.from_edit_mesh(obj.data)
            uv_layer = bm.loops.layers.uv.verify()
            use_global = self.orientation == "GLOBAL"

            axis = self.direction[-1].lower()
            is_negative = self.direction.startswith("NEGATIVE")

            for face in bm.faces:
                if use_global:
                    face_center = obj.matrix_world @ face.calc_center_median()
                else:
                    face_center = face.calc_center_median()

                coordinate = getattr(face_center, axis)

                if (is_negative and coordinate < 0) or (not is_negative and coordinate >= 0):
                    for loop in face.loops:
                        loop[uv_layer].select = True
                        loop[uv_layer].select_edge = True

                    if context.tool_settings.use_uv_select_sync:
                        face.select = True

            bmesh.update_edit_mesh(obj.data)
        return {"FINISHED"}


class MIO3UV_OT_select_similar(Mio3UVOperator):
    bl_idname = "uv.mio3_select_similar"
    bl_label = "Similar"
    bl_description = "Select Similar"
    bl_options = {"REGISTER", "UNDO"}

    check_edges: BoolProperty(name="Check Edges", description="", default=True)

    def execute(self, context):
        self.start_time()
        self.objects = self.get_selected_objects(context)

        use_uv_select_sync = context.tool_settings.use_uv_select_sync
        if use_uv_select_sync:
            context.tool_settings.mesh_select_mode = (False, False, True)
            try:
                bpy.ops.mesh.select_similar_region()
            except:
                pass
            return {"FINISHED"}

        island_manager = UVIslandManager(self.objects, find_all=True, uv_select=False)

        base_island = None
        for island in island_manager.islands:
            if any(all(loop[island.uv_layer].select for loop in face.loops) for face in island.faces):
                base_island = island
                base_face_count = len(base_island.faces)
                base_uv_count = self.get_island_uv_count(base_island)
                base_edge_count = self.get_island_edge_count(base_island) if self.check_edges else None
                base_island.select_all_uv()
                break

        if not base_island:
            return self.cancel_operator(context, use_uv_select_sync, island_manager)

        for island in island_manager.islands:
            if island == base_island:
                continue
            island.deselect_all_uv()
            if not self.is_different(island, base_face_count, base_uv_count, base_edge_count):
                island.select_all_uv()

        island_manager.update_uvmeshes()

        if use_uv_select_sync:
            self.sync_mesh_from_uv(context, self.objects)
            context.tool_settings.use_uv_select_sync = True
        self.print_time()
        return {"FINISHED"}

    def cancel_operator(self, context, use_uv_select_sync, island_manager):
        if use_uv_select_sync:
            island_manager.restore_vertex_selection()
            island_manager.update_uvmeshes()
            context.tool_settings.use_uv_select_sync = True
        return {"CANCELLED"}

    def get_island_uv_count(self, island):
        return sum(len(face.loops) for face in island.faces)

    def get_island_edge_count(self, island):
        return len({edge for face in island.faces for edge in face.edges})

    def is_different(self, island, base_face_count, base_uv_count, base_edge_count):
        if len(island.faces) != base_face_count:
            return True
        if self.get_island_uv_count(island) != base_uv_count:
            return True
        if self.check_edges and self.get_island_edge_count(island) != base_edge_count:
            return True
        return False


class MIO3UV_OT_select_shared(Mio3UVOperator):
    bl_idname = "uv.mio3_select_shared"
    bl_label = "Shared Vert"
    bl_description = "Select Shared Vert"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        obj = context.active_object
        bm = bmesh.from_edit_mesh(obj.data)
        uv_layer = bm.loops.layers.uv.verify()

        selected_uvs = set()
        for face in bm.faces:
            for loop in face.loops:
                if loop[uv_layer].select:
                    selected_uvs.add(loop.vert.index)

        for face in bm.faces:
            for loop in face.loops:
                if loop.vert.index in selected_uvs:
                    loop[uv_layer].select = True

        bmesh.update_edit_mesh(obj.data)
        return {"FINISHED"}


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
        precision=4,
        step=0.01,
    )
    expand: BoolProperty(name="Expand", default=True)

    def execute(self, context):
        self.start_time()
        self.objects = self.get_selected_objects(context)
        self.threshold_sq = self.threshold * self.threshold
        if context.tool_settings.uv_select_mode == "EDGE":
            context.tool_settings.uv_select_mode = "VERTEX"

        if context.tool_settings.use_uv_select_sync:
            try:
                bpy.ops.mesh.select_mirror(extend=True)
            except:
                return {"CANCELLED"}
            return {"FINISHED"}

        for obj in self.objects:
            bm = bmesh.from_edit_mesh(obj.data)
            bm.select_mode = {"VERT"}
            bm.verts.ensure_lookup_table()
            bm.faces.ensure_lookup_table()
            uv_layer = bm.loops.layers.uv.verify()
            self.select_mirror(bm, uv_layer)
            bmesh.update_edit_mesh(obj.data)

        self.print_time()
        return {"FINISHED"}

    def select_mirror(self, bm, uv_layer):
        original_selected_verts = {v.index for v in bm.verts if v.select}

        self.select_symmetric_verts(bm, uv_layer)

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

        sym_positions = {v: self.get_symmetric_3d_point(v.co) for v in bm.verts if v.select}
        face_sym_verts = {face: [sym_positions[v] for v in face.verts] for face in bm.faces if face.select}

        for face, center in face_centers.items():
            if uv_selection[face]:
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
                                sym_loop[uv_layer].select = True
                                sym_loop[uv_layer].select_edge = True
                                break
                        if not self.expand:
                            loop[uv_layer].select = False
                            loop[uv_layer].select_edge = False

        for v in bm.verts:
            v.select = False
        for i in original_selected_verts:
            bm.verts[i].select = True
        bm.select_flush_mode()

    def get_symmetric_3d_point(self, co):
        return Vector((-co.x, co.y, co.z))

    def get_symmetric_face(self, face, potential_faces, face_sym_verts):
        face_vert_count = len(face.verts)
        sym_verts = face_sym_verts[face]
        for pot_face in potential_faces:
            if len(pot_face.verts) == face_vert_count:
                if all(any((v.co - sv).length_squared < self.threshold_sq for sv in sym_verts) for v in pot_face.verts):
                    return pot_face
        return None

    # 3Dの対称頂点を選択
    def select_symmetric_verts(self, bm, uv_layer):
        kd = kdtree.KDTree(len(bm.verts))
        for i, v in enumerate(bm.verts):
            kd.insert(v.co, i)
        kd.balance()

        selected_verts = set()
        selected_loops = set()
        for face in bm.faces:
            if face.select:
                for loop in face.loops:
                    if loop[uv_layer].select:
                        selected_loops.add(loop)
                        for connected_face in loop.vert.link_faces:
                            for v in connected_face.verts:
                                selected_verts.add(v)

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


class MIO3UV_OT_select_boundary(Mio3UVOperator):
    bl_idname = "uv.mio3_select_boundary"
    bl_label = "Boundary"
    bl_description = "Select Boundary"
    bl_options = {"REGISTER", "UNDO"}

    use_seam: BoolProperty(name="Seam", default=True, options={"HIDDEN"})
    use_mesh_boundary: BoolProperty(name="Mesh Boundary", default=True)
    use_uv_boundary: BoolProperty(name="UV Space Boundary", default=True, options={"HIDDEN"})

    def execute(self, context):
        self.start_time()

        self.objects = self.get_selected_objects(context)

        if context.tool_settings.use_uv_select_sync:
            return self.use_uv_select_sync_process(context)

        uv_select_mode = context.tool_settings.uv_select_mode
        context.tool_settings.uv_select_mode = "EDGE"

        check_selected = self.check_selected_face_objects(self.objects)
        if not check_selected:
            bpy.ops.uv.select_all(action="SELECT")

        island_manager = UVIslandManager(self.objects)

        for obj, islands in island_manager.islands_by_object.items():
            bm = island_manager.bmesh_dict[obj]
            uv_layer = island_manager.uv_layer_dict[obj]

            for island in islands:
                original_selected_loops = {
                    loop for face in island.faces for loop in face.loops if loop[uv_layer].select
                }

                island.deselect_all_uv()
                for face in island.faces:
                    for loop in face.loops:
                        uv = loop[uv_layer]
                        if loop in original_selected_loops:
                            is_boundary = False
                            if self.use_mesh_boundary and loop.edge.is_boundary:
                                is_boundary = True
                            if self.use_seam and loop.edge.seam:
                                is_boundary = True
                            if self.use_uv_boundary and loop.edge in island.boundary_edge:
                                is_boundary = True

                            if is_boundary:
                                uv.select = True
                                uv.select_edge = True

        island_manager.update_uvmeshes()

        context.tool_settings.uv_select_mode = uv_select_mode
        self.print_time()
        return {"FINISHED"}

    def use_uv_select_sync_process(self, context):
        self.sync_uv_from_mesh(context, self.objects)

        check_selected = self.check_selected_face_objects(self.objects)
        if not check_selected:
            bpy.ops.mesh.select_all(action="SELECT")

        for obj in self.objects:
            bm = bmesh.from_edit_mesh(obj.data)
            selected_verts = set(v for v in bm.verts if v.select)
            boundary_verts = set()
            for edge in bm.edges:
                if check_selected and not edge.select:
                    continue
                edge_verts = set(edge.verts)
                if edge_verts.issubset(selected_verts):
                    if edge.is_boundary or edge.seam:
                        boundary_verts.update(edge_verts)

            for v in bm.verts:
                v.select = False
            bm.select_flush(False)
            for vert in boundary_verts:
                vert.select = True
            bm.select_flush(True)

            bmesh.update_edit_mesh(obj.data)
        return {"FINISHED"}


class MIO3UV_OT_select_edge_direction(Mio3UVOperator):
    bl_idname = "uv.mio3_select_edge_direction"
    bl_label = "Select Edge Loops"
    bl_description = "Select only vertical or horizontal edges"
    bl_options = {"REGISTER", "UNDO"}
    axis: EnumProperty(
        name="Direction",
        items=[
            ("Y", "Vertical", ""),
            ("X", "Horizontal", ""),
        ],
        default="X",
    )
    threshold: FloatProperty(name="Threshold", default=0.3, min=0.01, max=0.8, step=1)

    @classmethod
    def poll(cls, context):
        obj = context.active_object
        return cls.is_valid_object(obj) and not context.tool_settings.use_uv_select_sync

    def execute(self, context):
        self.objects = self.get_selected_objects(context)
        context.tool_settings.uv_select_mode = "EDGE"

        for obj in self.objects:
            bm = bmesh.from_edit_mesh(obj.data)
            uv_layer = bm.loops.layers.uv.verify()
            self.process_uv_selection(bm, uv_layer, self.axis)
            bmesh.update_edit_mesh(obj.data)
        return {"FINISHED"}

    def process_uv_selection(self, bm, uv_layer, axis):
        selected_uv_edges = set()
        for face in bm.faces:
            if not face.select:
                continue
            for loop in face.loops:
                if loop[uv_layer].select_edge:
                    edge = loop.edge
                    selected_uv_edges.add((edge, loop))

        for edge, loop in selected_uv_edges:
            if not self.is_uv_edge_aligned(loop, axis, uv_layer):
                for l in edge.link_loops:
                    l[uv_layer].select_edge = False

    def is_uv_edge_aligned(self, loop, axis, uv_layer):
        uv1 = loop[uv_layer].uv
        uv2 = loop.link_loop_next[uv_layer].uv
        edge_vector = uv2 - uv1
        angle = math.atan2(edge_vector.y, edge_vector.x)
        if axis == "X":
            return abs(math.sin(angle)) < self.threshold
        else:
            return abs(math.cos(angle)) < self.threshold


class MIO3UV_OT_select_flipped_faces(Mio3UVOperator):
    bl_idname = "uv.mio3_select_flipped_faces"
    bl_label = "Flipped"
    bl_description = "Select Flipped UV Faces"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        self.start_time()
        self.objects = self.get_selected_objects(context)
        use_uv_select_sync = context.tool_settings.use_uv_select_sync
        if use_uv_select_sync:
            self.sync_uv_from_mesh(context, self.objects)
            context.tool_settings.mesh_select_mode = (False, False, True)

        check_selected = self.check_selected_face_objects(self.objects)

        if not check_selected and use_uv_select_sync:
            bpy.ops.mesh.select_all(action="SELECT")

        for obj in self.objects:
            bm = bmesh.from_edit_mesh(obj.data)
            bm.faces.ensure_lookup_table()
            uv_layer = bm.loops.layers.uv.verify()

            for face in bm.faces:
                if not face.select:
                    continue

                face_uvs = [loop[uv_layer].uv for loop in face.loops]

                area = 0
                for i in range(len(face_uvs)):
                    j = (i + 1) % len(face_uvs)
                    area += face_uvs[i].x * face_uvs[j].y - face_uvs[j].x * face_uvs[i].y
                area *= 0.5

                threshold = 1e-7
                is_flipped = area < -threshold
                should_select = (not check_selected) or (
                    check_selected and all(loop[uv_layer].select for loop in face.loops)
                )

                if is_flipped and should_select:
                    for loop in face.loops:
                        loop[uv_layer].select = True
                        loop[uv_layer].select_edge = True
                else:
                    for loop in face.loops:
                        loop[uv_layer].select = False
                        loop[uv_layer].select_edge = False

            bmesh.update_edit_mesh(obj.data)

        if use_uv_select_sync:
            self.sync_mesh_from_uv(context, self.objects)

        self.print_time()
        return {"FINISHED"}


class MIO3UV_OT_select_zero(Mio3UVOperator, bpy.types.Operator):
    bl_idname = "uv.mio3_select_zero"
    bl_label = "No Region"
    bl_description = "Select Zero Area UV Faces"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        self.start_time()
        self.objects = self.get_selected_objects(context)
        use_uv_select_sync = context.tool_settings.use_uv_select_sync
        if use_uv_select_sync:
            self.sync_uv_from_mesh(context, self.objects)
            context.tool_settings.mesh_select_mode = (False, False, True)

        check_selected = self.check_selected_face_objects(self.objects)

        if not check_selected and use_uv_select_sync:
            bpy.ops.mesh.select_all(action="SELECT")

        for obj in self.objects:
            bm = bmesh.from_edit_mesh(obj.data)
            uv_layer = bm.loops.layers.uv.verify()

            for face in bm.faces:
                if not face.select:
                    continue

                is_selected = any(loop[uv_layer].select for loop in face.loops)

                if check_selected and not is_selected:
                    continue

                face_uvs = [loop[uv_layer].uv.copy() for loop in face.loops]

                if len(face_uvs) >= 3:
                    a, b, c = face_uvs[:3]
                    area = abs((b.x - a.x) * (c.y - a.y) - (c.x - a.x) * (b.y - a.y)) * 0.5
                else:
                    area = 0.0

                if area < 1e-8:
                    for loop in face.loops:
                        loop[uv_layer].select = True
                        loop[uv_layer].select_edge = True
                else:
                    for loop in face.loops:
                        loop[uv_layer].select = False
                        loop[uv_layer].select_edge = False

            bmesh.update_edit_mesh(obj.data)

        if use_uv_select_sync:
            self.sync_mesh_from_uv(context, self.objects)

        self.print_time()
        return {"FINISHED"}


classes = [
    MIO3UV_OT_auto_uv_sync,
    MIO3UV_OT_select_half,
    MIO3UV_OT_select_similar,
    MIO3UV_OT_select_shared,
    MIO3UV_OT_select_mirror3d,
    MIO3UV_OT_select_boundary,
    MIO3UV_OT_select_edge_direction,
    MIO3UV_OT_select_flipped_faces,
    MIO3UV_OT_select_zero,
]


def register():
    for c in classes:
        bpy.utils.register_class(c)


def unregister():
    for c in classes:
        bpy.utils.unregister_class(c)
