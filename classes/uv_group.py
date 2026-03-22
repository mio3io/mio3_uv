import bmesh
from mathutils import Vector
from dataclasses import dataclass, field
from bpy.types import Object
from bmesh.types import BMVert, BMLoop, BMLayerItem, BMesh, BMFace, BMEdge


@dataclass
class UVNodeObject:
    obj: Object = None
    bm: BMesh = None
    uv_layer: BMLayerItem = None
    uv_sync_valid: bool = False


@dataclass
class UVNode:
    uv: Vector
    vert: BMVert
    loops: set[BMLoop] = field(default_factory=set)
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
    obj_info: UVNodeObject = None

    min_uv: Vector = field(default_factory=lambda: Vector((float("inf"), float("inf"))))
    max_uv: Vector = field(default_factory=lambda: Vector((float("-inf"), float("-inf"))))
    center: Vector = field(default_factory=lambda: Vector((0, 0)))
    median_center: Vector = field(default_factory=lambda: Vector((0, 0)))

    selection_states: dict[int, bool] = field(default_factory=dict)

    def __post_init__(self):
        if self.nodes:
            self.update_bounds()

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
    def uv_sync_valid(self):
        return self.obj_info.uv_sync_valid

    def has_selected_uv_face(self):
        "グループ内にUV面選択が含まれるか調べる"
        faces = {loop.face for node in self.nodes for loop in node.loops}
        if self.obj_info.uv_sync_valid:
            return any(face.select for face in faces)
        return any(face.select and all(loop.uv_select_edge for loop in face.loops) for face in faces)

    def __hash__(self):
        return hash((tuple(self.uv), self.vert))

    def __eq__(self, other):
        if not isinstance(other, UVNode):
            return NotImplemented
        return self.uv == other.uv and self.vert == other.vert

    def update_uvs(self):
        "UVノードのUVを更新"
        for node in self.nodes:
            node.update_uv( self.obj_info.uv_layer)

    def deselect_all_uv(self):
        "すべてのUVを非選択にする"
        for node in self.nodes:
            for loop in node.loops:
                loop.uv_select_vert = False
                loop.uv_select_edge = False

        if self.obj_info.bm.uv_select_sync_valid:
            self.obj_info.bm.uv_select_flush(False)

    def store_selection(self):
        "現在のUV選択状態を保存"
        self.selection_states.clear()
        for node in self.nodes:
            for loop in node.loops:
                self.selection_states[loop.index] = (loop.uv_select_vert, loop.uv_select_edge)

    def restore_selection(self):
        "保存したUV選択状態を復元"
        for node in self.nodes:
            for loop in node.loops:
                if loop.index in self.selection_states:
                    uv_select_vert, uv_select_edge = self.selection_states[loop.index]
                    loop.uv_select_vert = uv_select_vert
                    loop.uv_select_edge = uv_select_edge

        if self.obj_info.bm.uv_select_sync_valid:
            self.obj_info.bm.uv_select_flush_mode()

    def update_bounds(self):
        "バウンディングボックス・中心・min/maxを計算"
        uv_points = [node.uv for node in self.nodes]
        x_coords = [uv.x for uv in uv_points]
        y_coords = [uv.y for uv in uv_points]
        self.min_uv = Vector((min(x_coords), min(y_coords)))
        self.max_uv = Vector((max(x_coords), max(y_coords)))
        self.center = Vector(((self.min_uv.x + self.max_uv.x) / 2, (self.min_uv.y + self.max_uv.y) / 2))
        self.median_center = Vector((sum(x_coords) / len(uv_points), sum(y_coords) / len(uv_points)))

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
class UVNodeManager:
    objects: list[Object]
    sync: bool = False
    node_key_mode: str = "UV" # "UV" or "VERT_AND_UV"
    obj: Object = None
    bm: BMesh = None
    uv_layer: BMLayerItem = None

    object_colle: list[UVNodeObject] = field(default_factory=list)
    groups: list[UVNodeGroup] = field(default_factory=list)

    def __post_init__(self):
        for obj in self.objects:
            bm = bmesh.from_edit_mesh(obj.data)
            uv_layer = bm.loops.layers.uv.verify()
            uv_sync_valid = bm.uv_select_sync_valid

            if self.sync and not uv_sync_valid:
                bm.uv_select_sync_from_mesh()

            obj_info = UVNodeObject(obj, bm, uv_layer, uv_sync_valid)
            self.object_colle.append(obj_info)

            uv_groups = self.find_uv_nodes(bm, uv_layer, uv_sync_valid)
            for group in uv_groups:
                self.groups.append(UVNodeGroup(group, obj_info))

    def find_uv_nodes(self, bm, uv_layer, uv_sync_valid, sub_faces=None):
        uv_nodes = {}

        def add_uv_node(loop):
            key = self.get_loop_key(loop, uv_layer)
            uv_key = self.get_uv_key(loop[uv_layer].uv)
            if key not in uv_nodes:
                uv_nodes[key] = UVNode(uv=Vector(uv_key), vert=loop.vert, select=loop.uv_select_vert)
            else:
                if loop.uv_select_vert and not uv_nodes[key].select:
                    uv_nodes[key].select = True
            uv_nodes[key].loops.add(loop)

        # faces = 面の頂点のループを含めて対象にする
        # sub_faces = 面のループのみを対象にする
        
        # 選択されているループを座標をキーにしたノードグループにする（!!sync_uv_from_meshしていること）
        # ToDo: 座標をキーにすると閉じたループの場合一緒に始点と終点のノードができない

        if self.sync:
            # !!共有頂点の除外に影響が出るのでfaces検索は消さないこと
            # sub_faces から頂点
            target_verts = {vert for face in sub_faces for vert in face.verts} if sub_faces else bm.verts
            if sub_faces:
                # sub_facesは選択とは無関係
                for vert in target_verts:
                    if vert.select:
                        for loop in vert.link_loops:
                            if loop.uv_select_vert and loop.face in sub_faces:
                                add_uv_node(loop)
            else:
                for vert in target_verts:
                    if vert.select:
                        for loop in vert.link_loops:
                            if loop.uv_select_vert:
                                add_uv_node(loop)

        else:
            target_faces = sub_faces if sub_faces else bm.faces
            for face in target_faces:
                if not self.sync and not face.select:
                    continue
                for loop in face.loops:
                    if loop.uv_select_vert:
                        add_uv_node(loop)

        # UVノードの隣接リストを作成
        for node in uv_nodes.values():
            for loop in node.loops:
                edge = loop.edge
                # 選択されていないエッジループがある場合は接続を無視
                if not any(loop.uv_select_edge for loop in edge.link_loops):
                    continue
                for loop in edge.link_loops:
                    prev_key = self.get_loop_key(loop, uv_layer)
                    next_key = self.get_loop_key(loop.link_loop_next, uv_layer)
                    if prev_key in uv_nodes and next_key in uv_nodes:
                        uv_nodes[prev_key].neighbors.add(uv_nodes[next_key])
                        uv_nodes[next_key].neighbors.add(uv_nodes[prev_key])

        # 接続ごとにグループ分けして返す
        return self.group_uv_nodes(list(uv_nodes.values()))

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

    @staticmethod
    def get_uv_key(uv):
        return (round(uv.x, 6), round(uv.y, 6))

    def get_loop_key(self, loop, uv_layer):
        uv_key = self.get_uv_key(loop[uv_layer].uv)
        if self.node_key_mode == "VERT_AND_UV":
            return (loop.vert, uv_key)
        return uv_key

    def get_median_center(self):
        if not (groups := self.groups):
            return Vector((0, 0))
        total_count = sum(len(group.nodes) for group in groups)
        if total_count == 0:
            return Vector((0, 0))
        sum_x = sum(group.median_center.x * len(group.nodes) for group in groups)
        sum_y = sum(group.median_center.y * len(group.nodes) for group in groups)
        return Vector((sum_x / total_count, sum_y / total_count))

    def get_bbox_center(self):
        if not (groups := self.groups):
            return Vector((0, 0))
        min_x = min(group.min_uv.x for group in groups)
        min_y = min(group.min_uv.y for group in groups)
        max_x = max(group.max_uv.x for group in groups)
        max_y = max(group.max_uv.y for group in groups)
        return Vector(((min_x + max_x) / 2, (min_y + max_y) / 2))

    def uv_select_set_all(self, select):
        for obj_info in self.object_colle:
            bm = obj_info.bm
            for face in bm.faces:
                face.uv_select = select
                for loop in face.loops:
                    loop.uv_select_vert = select
                    loop.uv_select_edge = select

    def remove_group(self, group_to_remove):
        for group in self.groups:
            if group is group_to_remove:
                self.groups.remove(group)
                break

    def update_uvmeshes(self, mesh_sync=False):
        for obj_info in self.object_colle:
            if self.sync and mesh_sync and obj_info.uv_sync_valid:
                obj_info.bm.uv_select_sync_to_mesh()
            bmesh.update_edit_mesh(obj_info.obj.data)

    @classmethod
    def from_island(cls, island, sync=False, sub_faces=None):
        manager = cls(objects=[], sync=sync)
        uv_sync_valid = island.uv_sync_valid
        uv_groups = manager.find_uv_nodes(island.bm, island.uv_layer, uv_sync_valid, sub_faces=sub_faces)
        obj_info = UVNodeObject(island.obj, island.bm, island.uv_layer, uv_sync_valid)
        for group in uv_groups:
            manager.groups.append(UVNodeGroup(group, obj_info))
        return manager
