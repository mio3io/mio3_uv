import bpy
import math
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
        self.objects = self.get_selected_objects(context)

        use_uv_select_sync = context.tool_settings.use_uv_select_sync

        island_manager = UVIslandManager(self.objects, sync=use_uv_select_sync)
        if not island_manager.islands:
            return {"CANCELLED"}

        for island in island_manager.islands:
            island.store_selection()
            island.deselect_all_uv()

        for island in island_manager.islands:
            island.restore_selection()

            bm = island.bm
            uv_layer = island.uv_layer

            self.uv_selection(bm, uv_layer, island.faces, self.axis)

            node_manager = UVNodeManager.from_island(island, sync=use_uv_select_sync, sub_faces=island.faces)
            if not node_manager.groups:
                continue

            self.align_uv_nodes(node_manager, self.axis)

            island.restore_selection()

        island_manager.update_uvmeshes(True)

        self.print_time()
        return {"FINISHED"}

    def uv_selection(self, bm, uv_layer, faces, axis):
        selected_uv_edges = set()
        for face in faces:
            if not face.select:
                continue
            for loop in face.loops:
                if loop.uv_select_edge:
                    edge = loop.edge
                    selected_uv_edges.add((edge, loop))

        for edge, loop in selected_uv_edges:
            if not self.is_direction(edge, loop, axis, uv_layer):
                for l in edge.link_loops:
                    l.uv_select_edge = False

    def is_direction(self, edge, loop, axis, uv_layer):
        uv1 = loop[uv_layer].uv
        uv2 = loop.link_loop_next[uv_layer].uv
        edge_vector = uv2 - uv1
        angle = math.atan2(edge_vector.y, edge_vector.x)
        if axis == "X":
            return abs(math.sin(angle)) < self.threshold
        else:
            return abs(math.cos(angle)) < self.threshold

    def align_uv_nodes(self, node_manager, alignment_type="X"):
        for group in node_manager.groups:
            nodes = group.nodes
            original_uvs = [node.uv.copy() for node in nodes]
            uv_coords = [node.uv for node in nodes]

            if alignment_type == "Y":
                avg_x = sum(uv.x for uv in uv_coords) / len(uv_coords)
                for node, original_uv in zip(nodes, original_uvs):
                    aligned_x = avg_x
                    node.uv.x = original_uv.x * (1 - self.blend_factor) + aligned_x * self.blend_factor
            else:
                avg_y = sum(uv.y for uv in uv_coords) / len(uv_coords)
                for node, original_uv in zip(nodes, original_uvs):
                    aligned_y = avg_y
                    node.uv.y = original_uv.y * (1 - self.blend_factor) + aligned_y * self.blend_factor

            group.update_uvs()


def register():
    bpy.utils.register_class(MIO3UV_OT_align_edges)


def unregister():
    bpy.utils.unregister_class(MIO3UV_OT_align_edges)
