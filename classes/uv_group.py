import bpy
import bmesh
from mathutils import Vector
from dataclasses import dataclass, field
from typing import Literal
from bpy.types import Object
from bmesh.types import BMVert, BMLoop, BMLayerItem, BMesh, BMFace, BMEdge
from .uv_island import UVIslandManager

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
        return hash((self.obj, id(self.bm), id(self.uv_layer)))

    def __eq__(self, other):
        if not isinstance(other, UVNodeGroup):
            return NotImplemented
        return (self.obj, id(self.bm), id(self.uv_layer)) == (other.obj, id(other.bm), id(other.uv_layer))

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

@dataclass
class UVNodeManager:
    objects: list[Object]
    mode: Literal["VERT", "EDGE", "FACE"] = "FACE"
    island_manager: UVIslandManager | None = None

    groups: list[UVNodeGroup] = field(default_factory=list)

    def __post_init__(self):
        self.find_all_groups()

    def find_all_groups(self):
        for obj in self.objects:
            if self.island_manager and obj in self.island_manager.bmesh_dict:
                bm = self.island_manager.bmesh_dict[obj]
                uv_layer = self.island_manager.uv_layer_dict[obj]
            else:
                bm = bmesh.from_edit_mesh(obj.data)
                uv_layer = bm.loops.layers.uv.verify()

            uv_groups = self.find_uv_nodes(bm, uv_layer)
            self.add_group(obj, bm, uv_layer, uv_groups)

    def add_group(self, obj, bm, uv_layer, uv_groups):
        self.groups.extend([UVNodeGroup(nodes=group, obj=obj, bm=bm, uv_layer=uv_layer) for group in uv_groups])

    def find_uv_nodes(self, bm, uv_layer, selected=None):
        uv_nodes = {}

        def round_uv(uv):
            return (round(uv.x, 6), round(uv.y, 6))

        def add_uv_node(loop):
            key = round_uv(loop[uv_layer].uv)
            if key not in uv_nodes:
                uv_nodes[key] = UVNode(uv=Vector(key), vert=loop.vert)
            uv_nodes[key].loops.append(loop)

        if self.mode == "EDGE":  # Edge Mode
            edges = selected if selected else bm.edges
            for edge in edges:
                if edge.select:
                    selected_faces = [face for face in edge.link_faces if face.select]
                    # if any(face.select for face in edge.link_faces):
                    for loop in edge.link_loops:
                        if loop.face in selected_faces:
                            if loop[uv_layer].select:
                                add_uv_node(loop)

        elif self.mode == "VERT":  # Sync Mode
            verts = selected if selected else bm.verts
            for vert in verts:
                if vert.select:
                    for loop in vert.link_loops:
                        if loop[uv_layer].select:
                            add_uv_node(loop)
        else:  # fast
            faces =  selected if selected else bm.faces
            for face in faces:
                if face.select:
                    for loop in face.loops:
                        if loop[uv_layer].select:
                            add_uv_node(loop)

        if self.mode == "EDGE":
            for key, node in uv_nodes.items():
                for loop in node.loops:
                    edge = loop.edge
                    if not any(loop[uv_layer].select_edge for loop in edge.link_loops):
                        continue
                    for loop in edge.link_loops:
                        current_key = round_uv(loop[uv_layer].uv)
                        next_key = round_uv(loop.link_loop_next[uv_layer].uv)
                        if current_key in uv_nodes and next_key in uv_nodes:
                            uv_nodes[current_key].neighbors.add(uv_nodes[next_key])
                            uv_nodes[next_key].neighbors.add(uv_nodes[current_key])
        else:
            for key, node in uv_nodes.items():
                for loop in node.loops:
                    prev_key = round_uv(loop.link_loop_prev[uv_layer].uv)
                    next_key = round_uv(loop.link_loop_next[uv_layer].uv)
                    if prev_key in uv_nodes:
                        node.neighbors.add(uv_nodes[prev_key])
                    if next_key in uv_nodes:
                        node.neighbors.add(uv_nodes[next_key])

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

    def remove_group(self, group_to_remove):
        if group_to_remove in self.groups:
            self.groups.remove(group_to_remove)

    def update_uvmeshes(self):
        unique_bms = {group.bm for group in self.groups if group.bm is not None}
        for bm in unique_bms:
            obj = next(group.obj for group in self.groups if group.bm == bm)
            bmesh.update_edit_mesh(obj.data)

    @classmethod
    def from_object(cls, obj, bm, uv_layer, selected=None, mode="FACE"):
        manager = cls(objects=[], mode=mode)
        if not bm and not uv_layer:
            bm = bmesh.from_edit_mesh(obj.data)
            uv_layer = bm.loops.layers.uv.verify()
        uv_groups = manager.find_uv_nodes(bm, uv_layer, selected)
        if uv_groups:
            manager.add_group(obj, bm, uv_layer, uv_groups)
        return manager
