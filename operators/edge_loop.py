import bpy
import time
import math
from mathutils import Vector
from bpy.props import BoolProperty, IntProperty, FloatProperty, EnumProperty
from ..classes.uv import UVNodeManager, UVNodeGroup
from ..classes.operator import Mio3UVOperator


class MIO3UV_OT_circle(Mio3UVOperator):
    bl_idname = "uv.mio3_circle"
    bl_label = "Circular"
    bl_description = "Shape the edge loop into a circular shape"
    bl_options = {"REGISTER", "UNDO"}

    composite: BoolProperty(
        name="Composite Edges",
        description="Process multiple edge loops as a single group",
    )

    def invoke(self, context, event):
        self.objects = self.get_selected_objects(context)
        if not self.objects:
            self.report({"WARNING"}, "Object is not selected")
            return {"CANCELLED"}
        return self.execute(context)

    def execute(self, context):
        self.start_time = time.time()
        use_uv_select_sync = context.tool_settings.use_uv_select_sync
        if use_uv_select_sync:
            self.sync_uv_from_mesh(context, self.objects)
            context.tool_settings.use_uv_select_sync = False
            node_manager = UVNodeManager(self.objects, mode="VERT")
        else:
            node_manager = UVNodeManager(self.objects, mode="EDGE")

        if not node_manager.groups:
            return {"CANCELLED"}

        if self.composite:
            base_group = node_manager.groups[0]
            all_nodes = {node for group in node_manager.groups for node in group.nodes}
            composite_group = UVNodeGroup(
                nodes=all_nodes, obj=base_group.obj, bm=base_group.bm, uv_layer=base_group.uv_layer
            )
            self.make_circular(composite_group)
            composite_group.update_uvs()
        else:
            for group in node_manager.groups:
                self.make_circular(group)
                group.update_uvs()

        node_manager.update_uvmeshes()

        if use_uv_select_sync:
            context.tool_settings.use_uv_select_sync = True
        self.print_time(time.time() - self.start_time)
        return {"FINISHED"}

    def make_circular(self, group):
        center = sum((node.uv for node in group.nodes), Vector((0, 0))) / len(group.nodes)
        avg_radius = sum((node.uv - center).length for node in group.nodes) / len(group.nodes)
        for node in group.nodes:
            direction = node.uv - center
            if direction.length > 0:
                node.uv = center + direction.normalized() * avg_radius


class MIO3UV_OT_adjust_edge(Mio3UVOperator):
    bl_idname = "uv.mio3_adjust_edge"
    bl_label = "Distribute UV"
    bl_description = "Distribute UVs evenly or based on geometry"
    bl_options = {"REGISTER", "UNDO"}

    method: EnumProperty(
        name="Method",
        items=[
            ("GEOMETRY", "Geometry", ""),
            ("EVENLY", "Even", ""),
        ],
    )
    iteration: IntProperty(
        name="Iterations",
        default=20,
        min=1,
        max=100,
    )
    smooth_factor: FloatProperty(
        name="Smooth",
        description="",
        default=0.01,
        min=0.0,
        max=1.0,
    )

    def invoke(self, context, event):
        self.objects = self.get_selected_objects(context)
        if not self.objects:
            self.report({"WARNING"}, "No object selected")
            return {"CANCELLED"}
        return self.execute(context)

    def execute(self, context):
        self.start_time = time.time()
        use_uv_select_sync = context.tool_settings.use_uv_select_sync
        if use_uv_select_sync:
            self.sync_uv_from_mesh(context, self.objects)
            context.tool_settings.use_uv_select_sync = False
            node_manager = UVNodeManager(self.objects, mode="VERT")
        else:
            node_manager = UVNodeManager(self.objects, mode="EDGE")

        for group in node_manager.groups:
            self.adjust_edges(group)
            group.update_uvs()

        node_manager.update_uvmeshes()

        if use_uv_select_sync:
            context.tool_settings.use_uv_select_sync = True
        self.print_time(time.time() - self.start_time)
        return {"FINISHED"}

    def adjust_edges(self, group):
        method = self.method
        nodes = list(group.nodes)
        node_indices = {node: i for i, node in enumerate(group.nodes)}
        edges = []

        for node in nodes:
            for neighbor in node.neighbors:
                if neighbor in nodes:
                    edge = tuple(sorted([node_indices[node], node_indices[neighbor]]))
                    if edge not in edges:
                        edges.append(edge)

        endpoints = [node for node in nodes if sum(1 for neighbor in node.neighbors if neighbor in nodes) == 1]

        if method == "GEOMETRY":
            total_3d_length = sum((nodes[edge[0]].vert.co - nodes[edge[1]].vert.co).length for edge in edges)
            total_uv_length = sum((nodes[edge[0]].uv - nodes[edge[1]].uv).length for edge in edges)
            scale = total_uv_length / total_3d_length if total_3d_length > 0 else 1
        else:
            total_uv_length = sum((nodes[edge[0]].uv - nodes[edge[1]].uv).length for edge in edges)
            scale = total_uv_length / len(edges) if edges else 0

        for _ in range(self.iteration):
            movements = {node: Vector((0, 0)) for node in nodes if node not in endpoints}

            for edge in edges:
                node1, node2 = nodes[edge[0]], nodes[edge[1]]
                target_length = (node1.vert.co - node2.vert.co).length * scale if method == "GEOMETRY" else scale

                uv_edge = node2.uv - node1.uv
                current_length = uv_edge.length

                if current_length > 0:
                    movement = (target_length - current_length) / 4 # の割合だけ動かす
                    direction = uv_edge.normalized()

                    if node1 not in endpoints:
                        movements[node1] -= direction * movement
                    if node2 not in endpoints:
                        movements[node2] += direction * movement

            # スムージング
            smooth_positions = {node: node.uv.copy() for node in nodes if node not in endpoints}
            for node in nodes:
                if node not in endpoints and node.neighbors:
                    avg_position = sum((n.uv for n in node.neighbors), Vector((0, 0))) / len(node.neighbors)
                    smooth_positions[node] = node.uv.lerp(avg_position, self.smooth_factor)

            max_movement = 0
            for node in nodes:
                if node not in endpoints:
                    combined_movement = (movements[node] + (smooth_positions[node] - node.uv)) / 2
                    node.uv += combined_movement
                    max_movement = max(max_movement, combined_movement.length)

            if max_movement < 0.00005:
                break

        for node in nodes:
            for neighbor in node.neighbors:
                if neighbor not in nodes:
                    relative_pos = neighbor.uv - node.uv
                    neighbor.uv = node.uv + relative_pos


classes = [MIO3UV_OT_circle, MIO3UV_OT_adjust_edge]


def register():
    for c in classes:
        bpy.utils.register_class(c)


def unregister():
    for c in classes:
        bpy.utils.unregister_class(c)
