import bpy
import math
from mathutils import Vector, Matrix
from bpy.props import BoolProperty, FloatProperty
from bmesh.types import BMFace, BMLayerItem
from ..classes import Mio3UVOperator, UVIslandManager
from ..utils.uv_follow import uv_follow, build_uv_loop_index, collect_shared_uv_loops


class UV_OT_mio3_grid(Mio3UVOperator):
    bl_idname = "uv.mio3_gridify"
    bl_label = "Gridify"
    bl_description = "Align UVs of a quadrangle in a grid"
    bl_options = {"REGISTER", "UNDO"}

    ratio_influence: FloatProperty(
        name="Geometry Ratio",
        description="1 matches the aspect ratio of the geometry",
        default=0.5,
        min=0.0,
        max=1.0,
        step=10
    )
    shape_blend: FloatProperty(
        name="Evenness",
        description="0 keeps average edge-length scaling, 1 makes spacing even",
        default=0,
        min=0.0,
        max=1.0,
        step=10
    )
    normalize: BoolProperty(name="Normalize", default=False)
    keep_aspect: BoolProperty(name="Keep Aspect Ratio", default=False)

    def execute(self, context):
        self.start_time()
        tool_settings = context.tool_settings
        use_uv_select_sync = tool_settings.use_uv_select_sync
        objects = self.get_selected_objects(context)

        island_manager = UVIslandManager(objects, sync=use_uv_select_sync, extend=False)
        if not island_manager.islands:
            self.report({"WARNING"}, "No UV islands found")
            return {"CANCELLED"}

        uv_loop_index_cache = {}
        for island in island_manager.islands:
            bm = island.bm
            uv_layer = island.uv_layer
            obj = island.obj

            f_act = self.get_base_face(uv_layer, island.faces)
            if not f_act:
                continue

            if obj not in uv_loop_index_cache:
                uv_loop_index_cache[obj] = build_uv_loop_index(bm, uv_layer)

            shared_uvs = collect_shared_uv_loops(uv_layer, island.faces, uv_loop_index_cache[obj])
            self.align_rect(uv_layer, f_act, island.faces)
            uv_follow(self.shape_blend, island, f_act, shared_uvs)

        island_manager.update_uvmeshes()

        if self.normalize:
            bpy.ops.uv.mio3_normalize(keep_aspect=self.keep_aspect)

        self.end_time()
        return {"FINISHED"}

    def get_base_face(self, uv_layer: BMLayerItem, selected_faces: list[BMFace]) -> BMFace | None:
        THRESHOLD = 1e-4
        best_face = None
        best_score = float("inf")
        all_rect = True

        for face in selected_faces:
            if len(face.loops) != 4:
                continue
            max_angle_diff = 0
            for i in range(4):
                v1 = face.loops[i][uv_layer].uv - face.loops[(i - 1) % 4][uv_layer].uv
                v2 = face.loops[(i + 1) % 4][uv_layer].uv - face.loops[i][uv_layer].uv
                angle_diff = abs(math.atan2(v1.x * v2.y - v1.y * v2.x, v1.dot(v2)) - math.pi / 2)
                if angle_diff > max_angle_diff:
                    max_angle_diff = angle_diff
            if max_angle_diff >= THRESHOLD:
                all_rect = False
            if max_angle_diff < best_score:
                best_score = max_angle_diff
                best_face = face

        if all_rect:
            return None

        return best_face

    def compute_aspect(self, active_face: BMFace, selected_faces):
        selected_set = set(f for f in selected_faces if len(f.loops) == 4)
        edge_dir = {}
        for i, loop in enumerate(active_face.loops):
            edge_dir[loop.edge] = i % 2

        visited = {active_face}
        queue = [active_face]
        while queue:
            face = queue.pop(0)
            for loop in face.loops:
                edge = loop.edge
                if not edge.is_manifold or edge.seam:
                    continue
                other_face = loop.link_loop_radial_next.face
                if other_face in visited or other_face not in selected_set:
                    continue
                visited.add(other_face)
                queue.append(other_face)
                shared_dir = edge_dir[edge]
                shared_verts = set(edge.verts)
                for other_loop in other_face.loops:
                    other_edge = other_loop.edge
                    if other_edge in edge_dir:
                        continue
                    if shared_verts & set(other_edge.verts):
                        edge_dir[other_edge] = 1 - shared_dir
                    else:
                        edge_dir[other_edge] = shared_dir

        dir0 = [e.calc_length() for e, d in edge_dir.items() if d == 0]
        dir1 = [e.calc_length() for e, d in edge_dir.items() if d == 1]
        avg0 = sum(dir0) / len(dir0) if dir0 else 1.0
        avg1 = sum(dir1) / len(dir1) if dir1 else 1.0
        return avg0 / avg1 if avg1 > 1e-10 else 1.0

    def align_rect(self, uv_layer: BMLayerItem, active_face: BMFace, selected_faces):
        uv_coords = [loop[uv_layer].uv.copy() for loop in active_face.loops]
        min_uv = Vector((min(uv.x for uv in uv_coords), min(uv.y for uv in uv_coords)))
        max_uv = Vector((max(uv.x for uv in uv_coords), max(uv.y for uv in uv_coords)))
        center_uv = (min_uv + max_uv) / 2

        edge_uv = uv_coords[1] - uv_coords[0]
        current_angle = math.atan2(edge_uv.y, edge_uv.x)
        target_angle = round(current_angle / (math.pi / 2)) * (math.pi / 2)
        angle_diff = target_angle - current_angle
        sin_a = math.sin(angle_diff)
        cos_a = math.cos(angle_diff)

        rot_matrix = Matrix(((cos_a, -sin_a), (sin_a, cos_a)))
        rotated_uvs = [rot_matrix @ (uv - center_uv) + center_uv for uv in uv_coords]

        sorted_by_y = sorted(zip(rotated_uvs, active_face.loops), key=lambda pair: (pair[0].y, pair[0].x))
        bottom_pairs = sorted(sorted_by_y[:2], key=lambda pair: pair[0].x)
        top_pairs = sorted(sorted_by_y[2:], key=lambda pair: pair[0].x)
        corner_pairs = [bottom_pairs[0], bottom_pairs[1], top_pairs[1], top_pairs[0]]
        ordered_uvs = [uv for uv, _loop in corner_pairs]

        w = max(((ordered_uvs[1] - ordered_uvs[0]).length + (ordered_uvs[2] - ordered_uvs[3]).length) / 2, 1e-8)
        h = max(((ordered_uvs[2] - ordered_uvs[1]).length + (ordered_uvs[3] - ordered_uvs[0]).length) / 2, 1e-8)

        if self.ratio_influence > 0:
            geo_aspect = self.compute_aspect(active_face, selected_faces)
            # dir0 = loops[0].edge direction
            dir0_vec = rotated_uvs[1] - rotated_uvs[0]
            if abs(dir0_vec.x) < abs(dir0_vec.y):
                geo_aspect = 1.0 / geo_aspect if geo_aspect > 1e-10 else 1.0
            uv_aspect = w / h
            target_aspect = math.exp(
                math.log(uv_aspect) * (1 - self.ratio_influence)
                + math.log(max(geo_aspect, 1e-10)) * self.ratio_influence
            )
            scale = math.sqrt(target_aspect / uv_aspect)
            w *= scale
            h /= scale

        hw, hh = w / 2, h / 2
        new_uvs = [
            Vector((center_uv.x - hw, center_uv.y - hh)),
            Vector((center_uv.x + hw, center_uv.y - hh)),
            Vector((center_uv.x + hw, center_uv.y + hh)),
            Vector((center_uv.x - hw, center_uv.y + hh)),
        ]

        for (_, loop), new_uv in zip(corner_pairs, new_uvs):
            loop[uv_layer].uv = new_uv

    def draw(self, context):
        layout = self.layout
        layout.use_property_decorate = False
        layout.use_property_split = True
        layout.prop(self, "ratio_influence")
        layout.prop(self, "shape_blend")
        layout.prop(self, "normalize")

        row = layout.row()
        row.enabled = self.normalize
        row.prop(self, "keep_aspect")


def register():
    bpy.utils.register_class(UV_OT_mio3_grid)


def unregister():
    bpy.utils.unregister_class(UV_OT_mio3_grid)
