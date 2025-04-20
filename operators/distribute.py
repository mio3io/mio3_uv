import bpy
from mathutils import Vector
from bpy.props import BoolProperty, FloatProperty, IntProperty, EnumProperty
from ..classes.uv import UVIslandManager, UVNodeManager
from ..classes.operator import Mio3UVOperator
from ..utils import straight_uv_nodes


class MIO3UV_OT_distribute(Mio3UVOperator):
    bl_idname = "uv.mio3_distribute"
    bl_label = "Distribute"
    bl_description = "Island Mode: Distribute islands evenly spaced\nUV Group: evenly spaced or based on geometry"
    bl_options = {"REGISTER", "UNDO"}

    island: BoolProperty(name="Island Mode", default=False)
    method: EnumProperty(
        name="Method",
        items=[("DISTRIBUTE", "Distribute", ""), ("FREE", "Free", "")],
    )
    axis: EnumProperty(
        name="Axis",
        items=[("AUTO", "Auto", ""), ("X", "X", ""), ("Y", "Y", "")],
    )
    reference: EnumProperty(
        name="Reference",
        items=[("BBOX", "Boundary", ""), ("CENTER", "Center", "")],
    )

    spacing: FloatProperty(
        name="Margin",
        default=0.01,
        min=0.0,
        step=0.1,
        precision=3,
    )
    align_uvs: EnumProperty(
        name="Align",
        items=[
            ("GEOMETRY", "Geometry", ""),
            ("EVEN", "Even", ""),
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
    straight: BoolProperty(name="Straight", default=True)

    def invoke(self, context, event):
        self.objects = self.get_selected_objects(context)
        if not self.objects:
            self.report({"WARNING"}, "Object is not selected")
            return {"CANCELLED"}

        use_uv_select_sync = context.tool_settings.use_uv_select_sync
        if use_uv_select_sync:
            self.sync_uv_from_mesh(context, self.objects)
        selected_face = self.check_selected_face_objects(self.objects)

        self.island = True if context.scene.mio3uv.island_mode else selected_face

        return self.execute(context)

    def check(self, context):
        self.objects = self.get_selected_objects(context)
        if context.tool_settings.use_uv_select_sync:
            self.sync_uv_from_mesh(context, self.objects)
        return True

    def execute(self, context):
        self.start_time()
        self.objects = self.get_selected_objects(context)

        use_uv_select_sync = context.tool_settings.use_uv_select_sync
        if use_uv_select_sync:
            self.sync_uv_from_mesh(context, self.objects)

        if self.island:
            island_manager = UVIslandManager(self.objects)
            if not island_manager.islands:
                return {"CANCELLED"}
            self.align_islands(island_manager)
            island_manager.update_uvmeshes()
        else:
            if use_uv_select_sync:
                node_manager = UVNodeManager(self.objects, mode="VERT")
            else:
                node_manager = UVNodeManager(self.objects, mode="EDGE")

            count = sum(len(group.nodes) for group in node_manager.groups)
            if count > 1000:
                self.report({"WARNING"}, "Too many vertices")
                return {"CANCELLED"}

            for group in node_manager.groups:
                if self.straight:
                    straight_uv_nodes(group, mode=self.align_uvs, keep_length=False, center=False)
                else:
                    self.adjust_edges(group)
                group.update_uvs()
            node_manager.update_uvmeshes()

        self.print_time()
        return {"FINISHED"}

    def align_islands(self, island_manager):
        islands = island_manager.islands
        if not islands:
            return

        axis = self.axis if self.axis != "AUTO" else island_manager.get_axis_uv()

        if axis == "X":
            island_manager.islands.sort(key=lambda island: island.center[0], reverse=False)
        else:
            island_manager.islands.sort(key=lambda island: island.center[1], reverse=True)

        if self.method == "DISTRIBUTE":
            total_islands = len(islands)
            if total_islands < 3:
                return

            first_island = islands[0]
            last_island = islands[-1]
            
            if self.reference == "BBOX":
                if axis == "X":
                    total_space = last_island.max_uv.x - first_island.min_uv.x
                    islands_width = sum(island.width for island in islands[1:-1])
                    space = (total_space - islands_width - first_island.width - last_island.width) / (total_islands - 1)
                    
                    current_pos = first_island.max_uv.x + space
                    for island in islands[1:-1]:
                        offset = Vector((current_pos - island.min_uv.x, 0))
                        island.move(offset)
                        current_pos += island.width + space
                else:
                    total_space = first_island.max_uv.y - last_island.min_uv.y
                    islands_height = sum(island.height for island in islands[1:-1])
                    space = (total_space - islands_height - first_island.height - last_island.height) / (total_islands - 1)
                    
                    current_pos = first_island.min_uv.y - space
                    for island in islands[1:-1]:
                        offset = Vector((0, current_pos - island.max_uv.y))
                        island.move(offset)
                        current_pos -= island.height + space
            else:
                start_center = first_island.center[0 if axis == "X" else 1]
                end_center = last_island.center[0 if axis == "X" else 1]
                total_space = abs(end_center - start_center)
                equal_space = total_space / (total_islands - 1)
                
                for i, island in enumerate(islands[1:-1], 1):
                    target_center = start_center + (equal_space * i * (1 if axis == "X" else -1))
                    current_center = island.center[0 if axis == "X" else 1]
                    offset_value = target_center - current_center
                    offset = Vector((offset_value, 0)) if axis == "X" else Vector((0, offset_value))
                    island.move(offset)
        else:
            if self.reference == "BBOX":
                if axis == "X":
                    current_pos = min(island.min_uv.x for island in islands)
                    for island in islands:
                        offset = Vector((current_pos - island.min_uv.x, 0))
                        current_pos += island.width + self.spacing
                        island.move(offset)
                else:
                    current_pos = max(island.max_uv.y for island in islands)
                    for island in islands:
                        offset = Vector((0, current_pos - island.max_uv.y))
                        current_pos -= island.height + self.spacing
                        island.move(offset)
            else:
                get_center = lambda island: island.center[0 if axis == "X" else 1]
                current_pos = min(get_center(island) for island in islands) if axis == "X" else max(get_center(island) for island in islands)
                for island in islands:
                    current_center = get_center(island)
                    offset_value = current_pos - current_center
                    offset = Vector((offset_value, 0)) if axis == "X" else Vector((0, offset_value))
                    island.move(offset)
                    current_pos += self.spacing * (1 if axis == "X" else -1)

    def adjust_edges(self, group):
        align_uvs = self.align_uvs
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

        if align_uvs == "GEOMETRY":
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
                target_length = (node1.vert.co - node2.vert.co).length * scale if align_uvs == "GEOMETRY" else scale

                uv_edge = node2.uv - node1.uv
                current_length = uv_edge.length

                if current_length > 0:
                    movement = (target_length - current_length) / 4  # の割合だけ動かす
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

    def draw(self, context):
        layout = self.layout
        layout.use_property_split = True
        layout.use_property_decorate = False

        if self.island:
            row = layout.row()
            row.prop(self, "method", expand=True)
            row = layout.row()
            row.prop(self, "spacing", text="Spacing")
            row.enabled = self.method == "FREE"
            row = layout.row()
            row.prop(self, "axis", expand=True)
            row = layout.row()
            row.prop(self, "reference", expand=True)
        else:
            layout.prop(self, "align_uvs")
            layout.prop(self, "smooth_factor")
            layout.prop(self, "iteration")
            layout.prop(self, "straight")

        layout.prop(self, "island")


classes = [MIO3UV_OT_distribute]


def register():
    for c in classes:
        bpy.utils.register_class(c)


def unregister():
    for c in classes:
        bpy.utils.unregister_class(c)
