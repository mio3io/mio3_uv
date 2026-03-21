import bpy
import bmesh
from bisect import bisect_left, bisect_right
from mathutils import Vector
from bpy.props import FloatProperty, EnumProperty
from ..classes import Mio3UVOperator, UVNodeManager
from ..utils import get_tile_co


class MIO3UV_OT_symmetry_snap(Mio3UVOperator):
    bl_idname = "uv.mio3_symmetry_snap"
    bl_label = "Snap"
    bl_description = "Symmetrize based on UV space"
    bl_options = {"REGISTER", "UNDO"}

    center: EnumProperty(
        name="Center",
        items=[
            ("GLOBAL", "Center", "Use UV space center"),
            ("CURSOR", "Cursor", "Use 2D cursor position"),
            ("SELECT", "Selection", "Selection"),
        ],
        default="CURSOR",
    )
    ref_direction: EnumProperty(
        items=[
            ("POSITIVE_Y_NEGATIVE_X", "↘", ""),
            ("POSITIVE_Y", "↓", ""),
            ("POSITIVE_Y_POSITIVE_X", "↙", ""),
            ("NEGATIVE_X", "→", ""),
            ("CENTER", "", ""),
            ("POSITIVE_X", "←", ""),
            ("NEGATIVE_Y_NEGATIVE_X", "↗", ""),
            ("NEGATIVE_Y", "↑", ""),
            ("NEGATIVE_Y_POSITIVE_X", "↖", ""),
        ],
        name="Reference Direction",
        default="POSITIVE_X",
    )

    threshold: FloatProperty(
        name="Threshold",
        default=0.05,
        min=0.0001,
        max=0.1,
        step=0.1,
        precision=4,
    )
    threshold_center: FloatProperty(
        name="Threshold Center",
        default=0.0005,
        min=0.0001,
        max=0.001,
        step=0.1,
        precision=4,
    )

    def invoke(self, context, event):
        self.objects = self.get_selected_objects(context)
        if not self.objects:
            self.report({"WARNING"}, "No objects selected")
            return {"CANCELLED"}
        return self.execute(context)

    def execute(self, context):
        self.start_time()
        self.objects = self.get_selected_objects(context)
        use_uv_select_sync = context.tool_settings.use_uv_select_sync

        node_manager = UVNodeManager(self.objects, sync=use_uv_select_sync, node_key_mode="VERT_AND_UV")
        for group in node_manager.groups:
            uv_layer = group.uv_layer
            center_loops = [loop for node in group.nodes for loop in node.loops]
            center = self.get_symmetry_center(context, uv_layer, center_loops)
            if "NEGATIVE_X" in self.ref_direction:
                self.symmetrize_axis(uv_layer, group.nodes, center, "X", "NEGATIVE")
            elif "POSITIVE_X" in self.ref_direction:
                self.symmetrize_axis(uv_layer, group.nodes, center, "X", "POSITIVE")

            if "POSITIVE_Y" in self.ref_direction:
                self.symmetrize_axis(uv_layer, group.nodes, center, "Y", "POSITIVE")
            elif "NEGATIVE_Y" in self.ref_direction:
                self.symmetrize_axis(uv_layer, group.nodes, center, "Y", "NEGATIVE")

        node_manager.update_uvmeshes()

        self.print_time()
        return {"FINISHED"}

    def symmetrize_axis(self, uv_layer, selected_nodes, center, axis_uv, direction):
        axis_index = 0 if axis_uv == "X" else 1
        other_index = 1 - axis_index
        center_value = center[axis_index]
        threshold = self.threshold
        threshold_sq = threshold * threshold

        features = self.build_node_features(selected_nodes)
        negative_nodes = []
        positive_nodes = []

        for node in selected_nodes:
            uv = node.uv
            axis_value = uv[axis_index]

            if abs(axis_value - center_value) <= self.threshold_center:
                new_uv = uv.copy()
                new_uv[axis_index] = center_value
                node.uv = new_uv
                node.update_uv(uv_layer)
            elif axis_value < center_value:
                negative_nodes.append(node)
            else:
                positive_nodes.append(node)

        if direction == "POSITIVE":
            source_nodes, target_nodes = positive_nodes, negative_nodes
        else:
            source_nodes, target_nodes = negative_nodes, positive_nodes

        if not source_nodes or not target_nodes:
            return

        source_data = []
        for node in source_nodes:
            uv = node.uv.copy()
            source_data.append((node, uv, uv[axis_index], uv[other_index], features[id(node)]))

        source_index, fallback_index = self.build_source_index(source_data)

        candidate_pairs = []
        for node in target_nodes:
            uv = node.uv.copy()
            mirrored_axis = 2 * center_value - uv[axis_index]
            target_other = uv[other_index]
            target_feature = features[id(node)]
            bucket = source_index.get(target_feature[0], fallback_index)
            coordinates, candidates = bucket
            left = bisect_left(coordinates, target_other - threshold)
            right = bisect_right(coordinates, target_other + threshold)

            for index in range(left, right):
                source_node, source_uv, source_axis, source_other, _ = candidates[index]
                axis_delta = abs(source_axis - mirrored_axis)
                if axis_delta > threshold:
                    continue

                other_delta = abs(source_other - target_other)
                dist_sq = axis_delta * axis_delta + other_delta * other_delta
                if dist_sq > threshold_sq:
                    continue

                score = self.score_loop_pair(axis_delta, other_delta, target_feature, features[id(source_node)])
                if score <= 5.5:
                    candidate_pairs.append((score, dist_sq, node, source_node, source_uv))

        candidate_pairs.sort(key=lambda item: (item[0], item[1]))

        matched_targets = set()
        matched_sources = set()
        for _, _, target_node, source_node, source_uv in candidate_pairs:
            target_node_id = id(target_node)
            source_node_id = id(source_node)
            if target_node_id in matched_targets or source_node_id in matched_sources:
                continue

            if axis_uv == "X":
                new_uv = Vector((2 * center.x - source_uv.x, source_uv.y))
            else:
                new_uv = Vector((source_uv.x, 2 * center.y - source_uv.y))
            target_node.uv = new_uv
            target_node.update_uv(uv_layer)
            matched_targets.add(target_node_id)
            matched_sources.add(source_node_id)

    def build_node_features(self, nodes):
        features = {}

        for node in nodes:
            loop = min(node.loops, key=lambda item: (item.face.index, item.index))
            face = loop.face
            vert = loop.vert

            edge_lengths = sorted((loop.edge.calc_length(), loop.link_loop_prev.edge.calc_length()))
            max_edge_length = edge_lengths[-1]
            if max_edge_length <= 1e-8:
                edge_signature = (0.0, 0.0)
            else:
                edge_signature = tuple(length / max_edge_length for length in edge_lengths)

            features[id(node)] = (len(face.verts), len(vert.link_edges), edge_signature)

        return features

    def build_source_index(self, source_data):
        grouped = {}
        fallback = []
        for item in source_data:
            key = item[4][0]
            grouped.setdefault(key, []).append(item)
            fallback.append(item)

        source_index = {key: self.sort_source_bucket(items) for key, items in grouped.items()}
        return source_index, self.sort_source_bucket(fallback)

    @staticmethod
    def sort_source_bucket(items):
        items.sort(key=lambda item: item[3])
        return [item[3] for item in items], items

    def score_loop_pair(self, axis_delta, other_delta, target_feature, source_feature):
        threshold = max(self.threshold, 1e-8)
        score = axis_delta / threshold
        score += (other_delta / threshold) * 1.25
        score += abs(source_feature[1] - target_feature[1]) * 1.0
        source_signature = source_feature[2]
        target_signature = target_feature[2]
        signature_distance = abs(len(source_signature) - len(target_signature))
        for index in range(min(len(source_signature), len(target_signature))):
            signature_distance += abs(source_signature[index] - target_signature[index])
        score += signature_distance * 1.5
        return score

    def get_symmetry_center(self, context, uv_layer, loops):
        if self.center == "SELECT":
            original = context.space_data.cursor_location.copy()
            bpy.ops.uv.snap_cursor(target="SELECTED")
            selection_loc = context.space_data.cursor_location.copy()
            bpy.ops.uv.cursor_set(location=original)
            return selection_loc
        elif self.center == "CURSOR":
            return context.space_data.cursor_location.copy()
        else:
            if context.scene.mio3uv.udim:
                return get_tile_co(Vector((0.5, 0.5)), uv_layer, loops)
            else:
                return Vector((0.5, 0.5))

    def draw(self, context):
        layout = self.layout
        row = layout.row()
        row.prop(self, "center", expand=True)

        split = layout.split(factor=0.45)
        split.alignment = "RIGHT"
        split.label(text="Reference Direction")
        grid = split.grid_flow(align=True, row_major=True, columns=3)
        grid.prop(self, "ref_direction", expand=True)

        split = layout.split(factor=0.45)
        split.alignment = "RIGHT"
        split.label(text="Threshold")
        split.prop(self, "threshold", text="")


def register():
    bpy.utils.register_class(MIO3UV_OT_symmetry_snap)


def unregister():
    bpy.utils.unregister_class(MIO3UV_OT_symmetry_snap)
