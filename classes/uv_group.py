import bpy
import bmesh
from mathutils import Vector
from dataclasses import dataclass, field
from bpy.types import Object
from bmesh.types import BMVert, BMLoop, BMLayerItem, BMesh, BMFace, BMEdge
from functools import cached_property


@dataclass
class UVNode:
    uv: Vector
    vert: BMVert
    loops: list[BMLoop] = field(default_factory=list)
    select: bool = False
    neighbors: set["UVNode"] = field(default_factory=set, repr=False, compare=False)

    def __hash__(self):
        return hash((tuple(self.uv), self.vert))

    def __eq__(self, other):
        if not isinstance(other, UVNode):
            return NotImplemented
        return self.uv == other.uv and self.vert == other.vert

    def __lt__(self, other):
        if not isinstance(other, UVNode):
            return NotImplemented
        return (tuple(self.uv), self.vert.index) < (tuple(other.uv), other.vert.index)

    def update_uv(self, uv_layer):
        "UVノードのUVを更新"
        for loop in self.loops:
            loop[uv_layer].uv = self.uv

    def is_break(self):
        "UVノードのループがすべてシームかどうかを確認"
        for loop in self.loops:
            if not loop.edge.seam:
                return False
        return True


@dataclass
class UVNodeGroup:
    nodes: list["UVNode"] = field(default_factory=list)
    obj: Object = None
    bm: BMesh = None
    uv_layer: BMLayerItem = None

    min_uv: Vector = field(default_factory=lambda: Vector((float("inf"), float("inf"))))
    max_uv: Vector = field(default_factory=lambda: Vector((float("-inf"), float("-inf"))))
    center: Vector = field(default_factory=lambda: Vector((0.0, 0.0)))

    selection_states: dict[int, bool] = field(default_factory=dict)

    def __hash__(self):
        return hash((tuple(self.uv), self.vert))

    def __eq__(self, other):
        if not isinstance(other, UVNode):
            return NotImplemented
        return self.uv == other.uv and self.vert == other.vert

    def update_uvs(self):
        "UVノードのUVを更新"
        for node in self.nodes:
            node.update_uv(self.uv_layer)

    def deselect_all_uv(self):
        "すべてのUVを非選択にする"
        for node in self.nodes:
            for loop in node.loops:
                loop[self.uv_layer].select = False
                loop[self.uv_layer].select_edge = False

    def store_selection(self):
        "現在のUV選択状態を保存"
        self.selection_states.clear()
        for node in self.nodes:
            for loop in node.loops:
                uv = loop[self.uv_layer]
                self.selection_states[loop.index] = (uv.select, uv.select_edge)

    def restore_selection(self):
        "保存したUV選択状態を復元"
        for node in self.nodes:
            for loop in node.loops:
                if loop.index in self.selection_states:
                    select, select_edge = self.selection_states[loop.index]
                    loop[self.uv_layer].select = select
                    loop[self.uv_layer].select_edge = select_edge

    def update_bounds(self):
        "バウンディングボックス・中心・min/maxを計算"
        uv_points = [node.uv for node in self.nodes]
        x_coords = [uv.x for uv in uv_points]
        y_coords = [uv.y for uv in uv_points]
        self.min_uv = Vector((min(x_coords), min(y_coords)))
        self.max_uv = Vector((max(x_coords), max(y_coords)))
        self.center = Vector((sum(x_coords) / len(x_coords), sum(y_coords) / len(y_coords)))

    def get_ordered_nodes(self):
        "順序付けしたノードリストを取得"
        uv_nodes = self.nodes
        start_node = None
        if start_node is None:
            start_node = next((node for node in uv_nodes if len(node.neighbors) == 1), None)
        if start_node is None:
            start_node = min(uv_nodes)

        ordered_nodes = [start_node]
        visited = {start_node}
        stack = [start_node]
        while stack:
            current_node = stack.pop()
            for neighbor in current_node.neighbors:
                if neighbor in uv_nodes and neighbor not in visited:
                    ordered_nodes.append(neighbor)
                    visited.add(neighbor)
                    stack.append(neighbor)

        return ordered_nodes

    # すべてのUVエッジの長さの合計を取得
    def get_sum_length(self, ordered_nodes):
        return sum((ordered_nodes[i + 1].uv - ordered_nodes[i].uv).length for i in range(len(ordered_nodes) - 1))


@dataclass
class UVNodeGroupCollection:
    obj: Object = None
    bm: BMesh = None
    uv_layer: BMLayerItem = None
    groups: list[UVNodeGroup] = field(default_factory=list)


@dataclass
class UVNodeManager:
    objects: list[Object]
    sync: bool = False
    obj: Object = None
    bm: BMesh = None
    uv_layer: BMLayerItem = None

    collections: list[UVNodeGroupCollection] = field(default_factory=list)

    @cached_property
    def groups(self) -> list[UVNodeGroup]:
        return [item for colle in self.collections for item in colle.groups]

    def __post_init__(self):
        for obj in self.objects:
            bm = bmesh.from_edit_mesh(obj.data)
            uv_layer = bm.loops.layers.uv.verify()
            if uv_groups := self.find_uv_nodes(bm, uv_layer):
                colle = UVNodeGroupCollection(obj, bm, uv_layer)
                self.collections.append(colle)
                for group in uv_groups:
                    colle.groups.append(UVNodeGroup(group, obj, bm, uv_layer))

    def find_uv_nodes(self, bm, uv_layer, edges=None, faces=None, sub_faces=None):
        uv_nodes = {}

        def add_uv_node(loop):
            key = self.get_key(loop[uv_layer].uv)
            if key not in uv_nodes:
                uv_nodes[key] = UVNode(uv=Vector(key), vert=loop.vert, select=loop[uv_layer].select)
            else:
                if loop[uv_layer].select and not uv_nodes[key].select:
                    uv_nodes[key].select = True
            uv_nodes[key].loops.append(loop)

        # 選択されているループを座標をキーにしたノードグループにする（!!sync_uv_from_meshしていること）
        # ToDo: 座標をキーにすると閉じたループの場合一緒に始点と終点のノードができない

        # !!共有頂点の除外に影響が出るのでfaces検索は消さないこと
        if faces:
            target_edges = {edge for face in faces for edge in face.edges}
        else:
            target_edges = edges if edges else bm.edges
        if self.sync:
            target_verts = {vert for edge in target_edges for vert in edge.verts}
            if sub_faces:
                # sub_facesは選択とは無関係
                for vert in target_verts:
                    if vert.select:
                        for loop in vert.link_loops:
                            if loop[uv_layer].select and loop.face in sub_faces:
                                add_uv_node(loop)
            else:
                for vert in target_verts:
                    if vert.select:
                        sub_faces = {face for face in vert.link_faces if face.select}
                        for loop in vert.link_loops:
                            if loop[uv_layer].select and loop.face in sub_faces:
                                add_uv_node(loop)
        else:
            if faces:
                # facesが指定されている場合は、選択された面のループを対象にする
                for face in faces:
                    if face.select:
                        for loop in face.loops:
                            if loop[uv_layer].select:
                                add_uv_node(loop)
            else:
                for edge in target_edges:
                    if edge.select:
                        selected_faces = {face for face in edge.link_faces if face.select}
                        for loop in edge.link_loops:
                            if loop[uv_layer].select and loop.face in selected_faces:
                                add_uv_node(loop)

        # UVノードの隣接リストを作成
        for node in uv_nodes.values():
            for loop in node.loops:
                edge = loop.edge
                # 選択されていないエッジループがある場合は接続を無視
                if not any(loop[uv_layer].select_edge for loop in edge.link_loops):
                    continue
                for loop in edge.link_loops:
                    prev_key = self.get_key(loop[uv_layer].uv)
                    next_key = self.get_key(loop.link_loop_next[uv_layer].uv)
                    if prev_key in uv_nodes and next_key in uv_nodes:
                        uv_nodes[prev_key].neighbors.add(uv_nodes[next_key])
                        uv_nodes[next_key].neighbors.add(uv_nodes[prev_key])

        # 接続ごとにグループ分けして返す
        return self.group_uv_nodes(list(uv_nodes.values()))

    @staticmethod
    def get_key(uv):
        return (round(uv.x, 6), round(uv.y, 6))

    @staticmethod
    def group_uv_nodes(uv_nodes):
        visited = set()
        islands = []
        stack = []
        for start_node in uv_nodes:
            if start_node not in visited:
                island = set()
                stack.append(start_node)
                while stack:
                    node = stack.pop()
                    if node not in visited:
                        visited.add(node)
                        island.add(node)
                        stack.extend(node.neighbors - visited)
                islands.append(island)
        return islands

    def remove_group(self, group_to_remove):
        if group_to_remove in self.groups:
            self.groups.remove(group_to_remove)

    def update_uvmeshes(self):
        for colle in self.collections:
            bmesh.update_edit_mesh(colle.obj.data)

    @classmethod
    def from_object(cls, obj, bm, uv_layer, sync=False, edges=None, faces=None, sub_faces=None):
        manager = cls(objects=[], sync=sync)
        if uv_groups := manager.find_uv_nodes(bm, uv_layer, edges=edges, faces=faces, sub_faces=sub_faces):
            colle = UVNodeGroupCollection(obj, bm, uv_layer)
            manager.collections.append(colle)
            for group in uv_groups:
                colle.groups.append(UVNodeGroup(group, obj, bm, uv_layer))
        return manager
