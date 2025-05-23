import bpy
import bmesh
from mathutils import Vector
from dataclasses import dataclass, field
from typing import Literal
from bpy.types import Object
from bmesh.types import BMVert, BMLoop, BMLayerItem, BMesh, BMFace, BMEdge
from collections import defaultdict
from functools import cached_property

@dataclass
class UVIsland:
    faces: set[BMFace]
    bm: BMesh
    uv_layer: BMLayerItem
    obj: Object
    extend: bool = True
    boundary_edge: set[BMEdge] = field(default_factory=set)

    face_count: int = field(init=False, default=0)
    uv_count: int = field(init=False, default=0)
    edge_count: int = field(init=False, default=0)

    orientation_mode: str = "WORLD"

    original_center: Vector = field(init=False)
    original_width: float = field(init=False)
    original_height: float = field(init=False)

    min_uv: Vector = field(default_factory=lambda: Vector((float("inf"), float("inf"))))
    max_uv: Vector = field(default_factory=lambda: Vector((float("-inf"), float("-inf"))))
    width: float = field(init=False)
    height: float = field(init=False)
    center: Vector = field(init=False)

    selection_loops: dict[int, bool] = field(default_factory=dict)
    selection_uv_count: int = field(init=False, default=0)
    all_uv_count: int = field(init=False, default=0)

    @property
    def center_3d(self):
        return self.center_3d_world if self.orientation_mode == "WORLD" else self.center_3d_local

    @cached_property
    def center_3d_world(self):
        return self.obj.matrix_world @ self.center_3d_local

    @cached_property
    def center_3d_local(self):
        verts = [v.co for face in self.faces for v in face.verts]
        return sum(verts, Vector()) / len(verts)

    @cached_property
    def original_selection_uvs(self):
        return self.selection_loops

    def __post_init__(self):
        self.update_bounds()
        self.original_center = self.center.copy()
        self.original_width = self.width
        self.original_height = self.height

    def __hash__(self):
        return hash((frozenset(self.faces), self.obj))

    def __eq__(self, other):
        if not isinstance(other, UVIsland):
            return NotImplemented
        return self.faces == other.faces and self.obj == other.obj

    def update_bounds(self):
        uv_points = [loop[self.uv_layer].uv for face in self.faces for loop in face.loops]
        if uv_points:
            x_coords = [uv.x for uv in uv_points]
            y_coords = [uv.y for uv in uv_points]
            self.min_uv = Vector((min(x_coords), min(y_coords)))
            self.max_uv = Vector((max(x_coords), max(y_coords)))
            self.center = Vector((sum(x_coords) / len(x_coords), sum(y_coords) / len(y_coords)))
            self.width = self.max_uv.x - self.min_uv.x
            self.height = self.max_uv.y - self.min_uv.y
        else:
            self.center = Vector((0, 0))
            self.width = self.height = 0

    def move(self, offset):
        for face in self.faces:
            for loop in face.loops:
                loop[self.uv_layer].uv += offset
        self.update_bounds()

    def store_selection(self):
        self.all_uv_count = 0
        self.selection_loops = {}
        select_uvs = {}
        all_uvs = {}

        for face in self.faces:
            for loop in face.loops:
                uv = loop[self.uv_layer]
                is_selected = uv.select
                is_edge_selected = uv.select_edge
                self.selection_loops[loop.index] = (is_selected, is_edge_selected)
                uv_key = (uv.uv.x, uv.uv.y)
                all_uvs[uv_key] = True
                if is_selected:
                    select_uvs[uv_key] = True

        self.all_uv_count = len(all_uvs)
        self.selection_uv_count = len(select_uvs)
        return self.original_selection_uvs

    def restore_selection(self):
        for face in self.faces:
            for loop in face.loops:
                if loop.index in self.selection_loops:
                    select, select_edge = self.selection_loops[loop.index]
                    loop[self.uv_layer].select = select
                    loop[self.uv_layer].select_edge = select_edge

    def select_all_uv(self):
        for face in self.faces:
            for loop in face.loops:
                loop[self.uv_layer].select = True
                loop[self.uv_layer].select_edge = True

    def deselect_all_uv(self):
        for face in self.faces:
            for loop in face.loops:
                loop[self.uv_layer].select = False
                loop[self.uv_layer].select_edge = False

    def is_any_uv_selected(self):
        for face in self.faces:
            for loop in face.loops:
                if loop[self.uv_layer].select:
                    return True
        return False


@dataclass
class UVIslandManager:
    objects: list[Object]
    islands: list[UVIsland] = field(default_factory=list, init=False)
    bmesh_dict: dict[Object, BMesh] = field(default_factory=dict, init=False)
    uv_layer_dict: dict[Object, BMLayerItem] = field(default_factory=dict, init=False)

    sync: bool = False # 選択同期
    sync_any: bool = False
    extend: bool = True # 選択しているUVを境界まで拡張する
    uv_select: bool = True # UVを選択しているもののみ
    mesh_link_uv: bool = False # メッシュのアイランドを境界まで拡張する（選択同期用）
    find_all: bool = False # すべてのアイランドを対象にする
    mesh_all: bool = False # すべてのメッシュを対象にする

    islands_by_object: dict[Object, list[UVIsland]] = field(default_factory=lambda: defaultdict(list), init=False)
    orientation_mode: Literal["WORLD", "LOCAL"] = "WORLD"

    original_selected_verts: dict[Object, dict[BMVert, bool]] = field(default_factory=dict, init=False)

    def __post_init__(self):
        self.find_all_islands()

    def find_all_islands(self):
        original_edge_seam = {}
        original_uv_select = {}

        # シームを区切る 元の選択を保存
        for obj in self.objects:
            bm = bmesh.from_edit_mesh(obj.data)
            uv_layer = bm.loops.layers.uv.verify()
            if not uv_layer:
                continue
            self.bmesh_dict[obj] = bm
            self.uv_layer_dict[obj] = uv_layer

            original_edge_seam[obj] = {edge: edge.seam for edge in bm.edges}
            original_uv_select[obj] = {}
            self.original_selected_verts[obj] = {vert: vert.select for vert in bm.verts}

            for face in bm.faces:
                for loop in face.loops:
                    uv = loop[uv_layer]
                    original_uv_select[obj][uv] = (uv.select, uv.select_edge)

        if self.mesh_all:
            bpy.ops.mesh.select_all(action="SELECT")
        elif self.mesh_link_uv or self.sync:
            bpy.ops.mesh.select_linked(delimit={"UV"})

        if self.find_all:
            bpy.ops.uv.select_all(action="SELECT")  # シームを切る
        elif self.extend:
            bpy.ops.uv.select_linked()

        bpy.ops.uv.seams_from_islands(mark_seams=True)

        for obj in self.objects:
            bm = self.bmesh_dict[obj]
            uv_layer = self.uv_layer_dict[obj]

            # if self.mesh_link_uv:
            #     self.sync_uv_from_mesh(bm, uv_layer)

            obj_islands = self.find_islands(bm, uv_layer, obj)
            if obj_islands:
                self.islands.extend(obj_islands)
                self.islands_by_object[obj] = obj_islands

            # 元の選択に戻す
            for uv, (select, select_edge) in original_uv_select[obj].items():
                uv.select = select
                uv.select_edge = select_edge
            for edge, seam in original_edge_seam[obj].items():
                edge.seam = seam
            if self.sync:
                for vert, select in self.original_selected_verts[obj].items():
                    vert.select = select
                bm.select_flush(False)

    def find_islands(self, bm: BMesh, uv_layer: BMLayerItem, obj: Object) -> list[UVIsland]:
        target_faces = set()
        if self.find_all:
            for face in bm.faces:
                target_faces.add(face)
        else:
            if self.extend:
                if self.sync:
                    for face in bm.faces:
                        target_faces.add(face)
                else:
                    for face in bm.faces:
                        for loop in face.loops:
                            uv = loop[uv_layer]
                            if uv.select and face not in target_faces:
                                target_faces.add(face)
                                break
            else:
                if self.sync:
                    for face in bm.faces:
                        if any(loop[uv_layer].select for loop in face.loops):
                            target_faces.add(face) 
                else:
                    for face in bm.faces:
                        if all(loop[uv_layer].select for loop in face.loops):
                            target_faces.add(face) 

        islands = []
        processed_faces = set()
        for face in target_faces:
            if face not in processed_faces:
                island_faces = set()
                island_edges = set()
                boundary_edges = set()
                faces_to_check = [face]
                face_count = 0
                uv_count = 0
                while faces_to_check:
                    current_face = faces_to_check.pop()
                    if current_face in target_faces and current_face not in processed_faces:
                        island_faces.add(current_face)
                        processed_faces.add(current_face)
                        face_count += 1
                        uv_count += len(current_face.loops)
                        for edge in current_face.edges:
                            island_edges.add(edge)
                            if not edge.seam:
                                faces_to_check.extend(edge.link_faces)
                            else:
                                boundary_edges.add(edge)

                if island_faces:
                    new_island = UVIsland(island_faces, bm, uv_layer, obj, self.extend)
                    new_island.face_count = face_count
                    new_island.uv_count = uv_count
                    new_island.edge_count = len(island_edges)
                    new_island.boundary_edge = boundary_edges
                    islands.append(new_island)

        if self.find_all:
            return islands

        if self.sync and not self.sync_any:
            # Sync 面選択しているアイランド
            # bpy.ops.uv.select_linked() で選択されてる…
            # islands = [i for i in islands if any(face.select for face in i.faces)]
            islands = [i for i in islands if any(all(loop[uv_layer].select for loop in face.loops) for face in i.faces)]
        else:
            islands = [i for i in islands if any(any(loop[uv_layer].select for loop in face.loops) for face in i.faces)]
        return islands

    def sync_uv_from_mesh(self, bm, uv_layer):
        for face in bm.faces:
            for loop in face.loops:
                loop[uv_layer].select = False
                loop[uv_layer].select_edge = False
        for vert in bm.verts:
            if vert.select:
                for loop in vert.link_loops:
                    loop[uv_layer].select = True
        for edge in bm.edges:
            if edge.select:
                for loop in edge.link_loops:
                    loop[uv_layer].select_edge = True

    def restore_vertex_selection(self):
        for obj, original_selection in self.original_selected_verts.items():
            bm = self.bmesh_dict[obj]
            for vert, was_selected in original_selection.items():
                vert.select = was_selected
            bm.select_flush(False)

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

    def sort_all_islands(self, key, reverse=False):
        self.islands.sort(key=key, reverse=reverse)
        for obj in self.islands_by_object:
            self.islands_by_object[obj].sort(key=key, reverse=reverse)

    def set_orientation_mode(self, mode):
        if self.orientation_mode != mode:
            self.orientation_mode = mode
            for island in self.islands:
                island.orientation_mode = mode

    def update_uvmeshes(self):
        unique_bms = {island.bm for island in self.islands if island.bm is not None}
        for bm in unique_bms:
            obj = next(island.obj for island in self.islands if island.bm == bm)
            bmesh.update_edit_mesh(obj.data)

    def remove_island(self, island):
        if island in self.islands:
            self.islands.remove(island)
            for obj, obj_islands in self.islands_by_object.items():
                if island in obj_islands:
                    obj_islands.remove(island)
                    break
