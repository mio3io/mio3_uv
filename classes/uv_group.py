import bpy
import bmesh
from mathutils import Vector
from dataclasses import dataclass, field
from bpy.types import Object
from bmesh.types import BMVert, BMLoop, BMLayerItem, BMesh, BMFace, BMEdge


@dataclass
class UVNode:
    uv: Vector
    vert: BMVert
    loops: list[BMLoop] = field(default_factory=list)
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
        for loop in self.loops:
            loop[uv_layer].uv = self.uv

    def is_break(self):
        for loop in self.loops:
            if not loop.edge.seam:
                return False
        return True

@dataclass
class UVNodeGroup:
    nodes: set["UVNode"] = field(default_factory=set)
    obj: Object = None
    bm: BMesh = None
    uv_layer: BMLayerItem = None

    min_uv: Vector = field(default_factory=lambda: Vector((float("inf"), float("inf"))))
    max_uv: Vector = field(default_factory=lambda: Vector((float("-inf"), float("-inf"))))
    center: Vector = field(init=False)

    selection_states: dict[int, bool] = field(default_factory=dict)

    def __hash__(self):
        return hash(frozenset(self.nodes))

    def __eq__(self, other):
        if not isinstance(other, UVNodeGroup):
            return NotImplemented
        return frozenset(self.nodes) == frozenset(other.nodes)

    def update_bounds(self):
        uv_points = [node.uv for node in self.nodes]
        if uv_points:
            x_coords = [uv.x for uv in uv_points]
            y_coords = [uv.y for uv in uv_points]
            self.min_uv = Vector((min(x_coords), min(y_coords)))
            self.max_uv = Vector((max(x_coords), max(y_coords)))
            self.center = Vector((sum(x_coords) / len(x_coords), sum(y_coords) / len(y_coords)))
        else:
            self.min_uv = Vector((0, 0))
            self.max_uv = Vector((0, 0))
            self.center = Vector((0, 0))

    def update_uvs(self):
        for node in self.nodes:
            node.update_uv(self.uv_layer)

    def deselect_all_uv(self):
        for node in self.nodes:
            for loop in node.loops:
                loop[self.uv_layer].select = False
                loop[self.uv_layer].select_edge = False

    def store_selection(self):
        self.selection_states.clear()
        for node in self.nodes:
            for loop in node.loops:
                uv = loop[self.uv_layer]
                self.selection_states[loop.index] = (uv.select, uv.select_edge)

    def restore_selection(self):
        for node in self.nodes:
            for loop in node.loops:
                if loop.index in self.selection_states:
                    select, select_edge = self.selection_states[loop.index]
                    loop[self.uv_layer].select = select
                    loop[self.uv_layer].select_edge = select_edge

    # 順序付けしたリストを取得
    def get_ordered_nodes(self):
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
class UVNodeManager:
    objects: list[Object]
    sync: bool = False

    groups: list[UVNodeGroup] = field(default_factory=list)

    def __post_init__(self):
        for obj in self.objects:
            bm = bmesh.from_edit_mesh(obj.data)
            uv_layer = bm.loops.layers.uv.verify()
            uv_groups = self.find_uv_nodes(bm, uv_layer)
            for group in uv_groups:
                self.add_group(group, obj, bm, uv_layer)

    def add_group(self, group, obj, bm, uv_layer):
        self.groups.append(UVNodeGroup(nodes=group, obj=obj, bm=bm, uv_layer=uv_layer))

    def find_uv_nodes(self, bm, uv_layer, selected=None):
        uv_nodes = {}

        # 選択されているループを座標をキーにしたノードグループにする（sync_uv_from_meshしていること）
        # ToDo: 座標をキーにすると閉じたループの場合一緒に始点と終点のノードができない
        edges = selected if selected else bm.edges
        for edge in edges:
            if any(v.select for v in edge.verts):
                for loop in edge.link_loops:
                    if loop[uv_layer].select:
                        key = self.get_key(loop[uv_layer].uv)
                        if key not in uv_nodes:
                            uv_nodes[key] = UVNode(uv=Vector(key), vert=loop.vert)
                        uv_nodes[key].loops.append(loop)

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
        unique_bms = {group.bm for group in self.groups if group.bm is not None}
        for bm in unique_bms:
            obj = next(group.obj for group in self.groups if group.bm == bm)
            bmesh.update_edit_mesh(obj.data)

    @classmethod
    def from_object(cls, obj, bm, uv_layer, selected=None):
        manager = cls(objects=[])
        if not bm and not uv_layer:
            bm = bmesh.from_edit_mesh(obj.data)
            uv_layer = bm.loops.layers.uv.verify()
        uv_groups = manager.find_uv_nodes(bm, uv_layer, selected)
        if uv_groups:
            for group in uv_groups:
                manager.add_group(group, obj, bm, uv_layer)
        return manager
