import bpy
import bmesh
from mathutils import Vector
from dataclasses import dataclass, field
from bpy.types import Object
from bmesh.types import BMVert, BMLoop, BMLayerItem, BMesh, BMFace, BMEdge
from functools import cached_property

VER_5_0_1 = bpy.app.version >= (5, 0, 1)


@dataclass
class UVObject:
    obj: Object = None
    bm: BMesh = None
    uv_layer: BMLayerItem = None
    original_uv_select_sync_valid: bool = False


@dataclass
class UVIsland:
    faces: set[BMFace]
    obj_info: UVObject = None
    sync: bool = False
    extend: bool = True

    orientation_mode: str = "WORLD"

    original_center: Vector = field(init=False)
    original_width: float = field(init=False)
    original_height: float = field(init=False)

    min_uv: Vector = field(default_factory=lambda: Vector((float("inf"), float("inf"))))
    max_uv: Vector = field(default_factory=lambda: Vector((float("-inf"), float("-inf"))))
    width: float = field(init=False)
    height: float = field(init=False)
    center: Vector = field(init=False, default_factory=lambda: Vector((0, 0)))
    median_center: Vector = field(init=False, default_factory=lambda: Vector((0, 0)))

    selection_loops: dict[int, bool] = field(default_factory=dict)
    selection_uv_faces: dict[int, bool] = field(default_factory=dict)
    selection_uv_count: int = field(init=False, default=0)  # 削除予定
    all_uv_count: int = field(init=False, default=0)

    @property
    def obj(self):
        return self.obj_info.obj

    @property
    def bm(self):
        return self.obj_info.bm

    @property
    def uv_layer(self):
        return self.obj_info.uv_layer

    @property
    def center_3d(self):
        return self.center_3d_world if self.orientation_mode == "WORLD" else self.center_3d_local

    @cached_property
    def center_3d_world(self):
        return self.obj_info.obj.matrix_world @ self.center_3d_local

    @cached_property
    def center_3d_local(self):
        verts = [v.co for face in self.faces for v in face.verts]
        return sum(verts, Vector()) / len(verts)

    def __post_init__(self):
        self.update_bounds()
        self.original_center = self.center.copy()
        self.original_width = self.width
        self.original_height = self.height

    def __hash__(self):
        return hash((frozenset(self.faces), self.obj_info.obj))

    def __eq__(self, other):
        if not isinstance(other, UVIsland):
            return NotImplemented
        return self.faces == other.faces and self.obj_info.obj == other.obj_info.obj

    def update_bounds(self):
        uv_points = [loop[self.uv_layer].uv for face in self.faces for loop in face.loops]
        if uv_points:
            x_coords = [uv.x for uv in uv_points]
            y_coords = [uv.y for uv in uv_points]
            self.min_uv = Vector((min(x_coords), min(y_coords)))
            self.max_uv = Vector((max(x_coords), max(y_coords)))
            self.center = Vector(((self.min_uv.x + self.max_uv.x) / 2, (self.min_uv.y + self.max_uv.y) / 2))
            self.median_center = Vector((sum(x_coords) / len(uv_points), sum(y_coords) / len(uv_points)))
            self.width = self.max_uv.x - self.min_uv.x
            self.height = self.max_uv.y - self.min_uv.y
        else:
            self.min_uv = Vector((float("inf"), float("inf")))
            self.max_uv = Vector((float("-inf"), float("-inf")))
            self.center = Vector((0, 0))
            self.median_center = Vector((0, 0))
            self.width = self.height = 0

    def move(self, offset, calc=False):
        for face in self.faces:
            for loop in face.loops:
                loop[self.uv_layer].uv += offset
        if calc:
            self.update_bounds()

    def store_selection(self):
        self.all_uv_count = 0
        self.selection_loops = {}
        self.selection_uv_faces = {}
        select_uvs = {}
        all_uvs = {}

        for face in self.faces:
            self.selection_uv_faces[face.index] = face.uv_select
            for loop in face.loops:
                uv = loop[self.uv_layer]
                is_selected = loop.uv_select_vert
                is_edge_selected = loop.uv_select_edge
                self.selection_loops[loop.index] = (is_selected, is_edge_selected)
                uv_key = (uv.uv.x, uv.uv.y)
                all_uvs[uv_key] = True
                if is_selected:
                    select_uvs[uv_key] = True

        self.all_uv_count = len(all_uvs)
        self.selection_uv_count = len(select_uvs)
        # return self.original_selection_uvs

    def restore_selection(self):
        for face in self.faces:
            if face.index in self.selection_uv_faces:
                face.uv_select = self.selection_uv_faces[face.index]
            for loop in face.loops:
                if loop.index in self.selection_loops:
                    uv_select_vert, uv_select_edge = self.selection_loops[loop.index]
                    loop.uv_select_vert = uv_select_vert
                    loop.uv_select_edge = uv_select_edge

        if self.bm.uv_select_sync_valid:
            self.bm.uv_select_flush_mode()

    def uv_select_set_all(self, select):
        for face in self.faces:
            face.uv_select = select
            for loop in face.loops:
                loop.uv_select_vert = select
                loop.uv_select_edge = select

    @cached_property
    def is_any_uv_selected(self):
        for face in self.faces:
            for loop in face.loops:
                if loop.uv_select_vert:
                    return True
        return False

    @cached_property
    def is_face_selected(self):
        for face in self.faces:
            if face.select:
                if all([l.uv_select_edge for l in face.loops]):  # select_edge -> エッジ選択時の〼を許容しない
                    return True
        return False


@dataclass
class UVIslandManager:
    objects: list[Object]

    sync: bool = False  # 選択同期
    extend: bool = True  # 選択しているUVを境界まで拡張する
    find_all: bool = False  # すべてのアイランドを対象にする
    mesh_all: bool = False  # メッシュ全体を対象にする

    orientation_mode = "WORLD"  # "WORLD" or "LOCAL"

    collections: list[UVObject] = field(default_factory=list)
    islands: list[UVIsland] = field(default_factory=list)

    def __post_init__(self):
        self.find_all_islands()

    def find_all_islands(self):
        for obj in self.objects:
            bm = bmesh.from_edit_mesh(obj.data)
            uv_layer = bm.loops.layers.uv.verify()
            if not uv_layer:
                continue

            uv_sync_valid = bm.uv_select_sync_valid

            obj_info = UVObject(obj, bm, uv_layer, uv_sync_valid)
            self.collections.append(obj_info)

            if self.sync and not uv_sync_valid:
                bm.uv_select_sync_from_mesh()

            self.find_islands(obj_info, all=self.find_all, extend=self.extend, sync=self.sync)

    def find_islands(self, obj_info: UVObject, all=False, extend=False, sync=False):
        bm = obj_info.bm
        uv_layer = obj_info.uv_layer
        eps_eq = 1e-14

        def get_selected_faces(bm, sync):
            selected_faces = set()
            if sync:
                if extend:
                    for face in bm.faces:
                        if face.hide:
                            continue
                        for loop in face.loops:
                            if loop.uv_select_vert:
                                selected_faces.add(face)
                                break
                else:
                    for face in bm.faces:
                        if face.hide:
                            continue
                        if face.uv_select:
                            selected_faces.add(face)
            else:
                if extend:
                    for face in bm.faces:
                        if face.hide:
                            continue
                        if face.select:
                            for loop in face.loops:
                                if loop.uv_select_vert:
                                    selected_faces.add(face)
                                    break
                else:
                    for face in bm.faces:
                        if face.hide:
                            continue
                        if face.select and face.uv_select:
                            selected_faces.add(face)
            return selected_faces

        if self.mesh_all:
                seed_faces = set(bm.faces) # hideメッシュも入れるべき？
        else:
            if all:
                if sync:
                    seed_faces = {f for f in bm.faces if not f.hide}
                else:
                    seed_faces = {f for f in bm.faces if not f.hide and f.select}
            else:
                seed_faces = get_selected_faces(bm, sync)
        if not seed_faces:
            return

        can_extend = all or extend
        visited = set()
        visited_add = visited.add

        for seed in seed_faces:
            if seed in visited:
                continue

            island = set()
            island_add = island.add
            stack = [seed]
            stack_append = stack.append

            while stack:
                face = stack.pop()
                if face in visited:
                    continue
                visited_add(face)
                island_add(face)

                for loop in face.loops:
                    edge = loop.edge
                    if edge.seam:
                        continue
                    link_loops = edge.link_loops
                    if len(link_loops) != 2:
                        continue

                    linked_loop = link_loops[1] if link_loops[0].face is face else link_loops[0]
                    linked_face = linked_loop.face
                    if linked_face in visited or linked_face.hide:
                        continue
                    if not can_extend and linked_face not in seed_faces:
                        continue

                    a = loop[uv_layer].uv
                    b = loop.link_loop_next[uv_layer].uv
                    c = linked_loop[uv_layer].uv
                    d = linked_loop.link_loop_next[uv_layer].uv

                    if loop.vert is linked_loop.vert:
                        du = a.x - c.x
                        dv = a.y - c.y
                        if du * du + dv * dv > eps_eq:
                            continue
                        du = b.x - d.x
                        dv = b.y - d.y
                    else:
                        du = a.x - d.x
                        dv = a.y - d.y
                        if du * du + dv * dv > eps_eq:
                            continue
                        du = b.x - c.x
                        dv = b.y - c.y

                    if du * du + dv * dv > eps_eq:
                        continue

                    stack_append(linked_face)

            if island:
                new_island = UVIsland(island, obj_info, self.sync, self.extend)
                self.islands.append(new_island)

    def get_median_center(self):
        if not self.islands:
            return Vector((0, 0))
        total_count = 0
        sum_x = 0.0
        sum_y = 0.0

        for island in self.islands:
            uv_count = sum(len(face.loops) for face in island.faces)
            if uv_count == 0:
                continue
            center = island.median_center
            total_count += uv_count
            sum_x += center.x * uv_count
            sum_y += center.y * uv_count

        if total_count == 0:
            return Vector((0, 0))
        return Vector((sum_x / total_count, sum_y / total_count))

    def get_bbox_center(self):
        if not self.islands:
            return Vector((0, 0))
        min_x = min(island.min_uv.x for island in self.islands)
        min_y = min(island.min_uv.y for island in self.islands)
        max_x = max(island.max_uv.x for island in self.islands)
        max_y = max(island.max_uv.y for island in self.islands)
        return Vector(((min_x + max_x) / 2, (min_y + max_y) / 2))

    def get_axis_3d(self):
        centers = [island.center_3d for island in self.islands]
        x_range = max(c.x for c in centers) - min(c.x for c in centers)
        y_range = max(c.y for c in centers) - min(c.y for c in centers)
        z_range = max(c.z for c in centers) - min(c.z for c in centers)
        ranges = [x_range, y_range, z_range]
        return ["X", "Y", "Z"][ranges.index(max(ranges))]

    def get_axis_uv(self):
        centers = [island.center for island in self.islands]
        x_range = max(c.x for c in centers) - min(c.x for c in centers)
        y_range = max(c.y for c in centers) - min(c.y for c in centers)
        ranges = [x_range, y_range]
        return ["X", "Y"][ranges.index(max(ranges))]

    def uv_select_set_all(self, select):
        for info in self.collections:
            bm = info.bm
            if bm.uv_select_sync_valid:
                bm.uv_select_foreach_set(select, faces=bm.faces)
                bm.uv_select_flush_mode()
            else:
                for island in [island for island in self.islands if island.obj_info == info]:
                    island.uv_select_set_all(select)

    def sort_all_islands(self, key, reverse=False):
        self.islands.sort(key=key, reverse=reverse)

    def set_orientation_mode(self, mode):
        if self.orientation_mode != mode:
            self.orientation_mode = mode
            for island in self.islands:
                island.orientation_mode = mode

    def update_uvmeshes(self, mesh_sync=False):
        for info in self.collections:
            if self.sync and mesh_sync and info.bm.uv_select_sync_valid:
                info.bm.uv_select_sync_to_mesh()
            bmesh.update_edit_mesh(info.obj.data)
