import bpy
from bpy.props import EnumProperty, FloatProperty
from ..classes import UVIslandManager, UVNodeManager, Mio3UVOperator


class MIO3UV_OT_align_edges(Mio3UVOperator):
    bl_idname = "uv.mio3_align_edges"
    bl_label = "Align Edge Loops"
    bl_description = "Align Edge Loops"
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
    blend_factor: FloatProperty(
        name="Mix",
        description="",
        default=1.0,
        min=0.0,
        max=1.0,
    )

    def execute(self, context):
        self.start_time()
        objects = self.get_selected_objects(context)

        use_uv_select_sync = context.tool_settings.use_uv_select_sync
        axis = self.axis

        island_manager = UVIslandManager(objects, sync=use_uv_select_sync)
        if not island_manager.islands:
            return {"CANCELLED"}

        for island in island_manager.islands:
            island.store_selection()
            island.deselect_all_uv()

        for island in island_manager.islands:
            island.restore_selection()

            uv_layer = island.uv_layer
            selected_uv_edges = set()
            for face in island.faces:
                if not face.select:
                    continue
                for loop in face.loops:
                    if loop.uv_select_edge:
                        selected_uv_edges.add(loop.edge)

            for edge in selected_uv_edges:
                if not self.is_direction(edge, axis, uv_layer):
                    for l in edge.link_loops:
                        l.uv_select_edge = False

            node_manager = UVNodeManager.from_island(island, sync=use_uv_select_sync, sub_faces=island.faces)
            if node_manager.groups:
                self.align_uv_nodes(node_manager, self.axis)

            island.restore_selection()

        island_manager.update_uvmeshes(True)

        self.print_time()
        return {"FINISHED"}

    def is_direction(self, edge, axis, uv_layer):
        min_vertical_ratio = None
        for loop in edge.link_loops:
            uv1 = loop[uv_layer].uv
            uv2 = loop.link_loop_next[uv_layer].uv
            edge_vector = uv2 - uv1
            length = edge_vector.length
            if length <= 1e-12:
                continue

            if axis == "X":
                vertical_ratio = abs(edge_vector.y) / length
            else:
                vertical_ratio = abs(edge_vector.x) / length

            if min_vertical_ratio is None or vertical_ratio < min_vertical_ratio:
                min_vertical_ratio = vertical_ratio

        if min_vertical_ratio is None:
            return False

        return min_vertical_ratio <= self.threshold

    def align_uv_nodes(self, node_manager: UVNodeManager, alignment_type):
        for group in node_manager.groups:
            original_uvs = [node.uv.copy() for node in group.nodes]

            if alignment_type == "Y":
                target_x = group.center.x
                for node, original_uv in zip(group.nodes, original_uvs):
                    node.uv.x = original_uv.x * (1 - self.blend_factor) + target_x * self.blend_factor
            else:
                target_y = group.center.y
                for node, original_uv in zip(group.nodes, original_uvs):
                    node.uv.y = original_uv.y * (1 - self.blend_factor) + target_y * self.blend_factor

            group.update_uvs()


def register():
    bpy.utils.register_class(MIO3UV_OT_align_edges)


def unregister():
    bpy.utils.unregister_class(MIO3UV_OT_align_edges)
