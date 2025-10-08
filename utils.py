import bpy
import bmesh
import math
from mathutils import Vector, Matrix


def sync_uv_from_mesh(context, selected_objects):
    "メッシュからUVの選択状態を同期する"
    objects = selected_objects if selected_objects else context.objects_in_mode
    for obj in objects:
        sync_uv_from_mesh_obj(obj)


def sync_uv_from_mesh_obj(obj):
    "メッシュからUVの選択状態を同期する"
    bm = bmesh.from_edit_mesh(obj.data)
    uv_layer = bm.loops.layers.uv.verify()
    for face in bm.faces:
        for loop in face.loops:
            loop[uv_layer].select = False
            loop[uv_layer].select_edge = False
    for vert in bm.verts:
        if vert.select:
            for loop in vert.link_loops:
                loop[uv_layer].select = True
    for edge in bm.edges:
        if edge.select:
            for loop in edge.link_loops:
                loop[uv_layer].select_edge = True
    bmesh.update_edit_mesh(obj.data)


def sync_mesh_from_uv(context, selected_objects):
    "UVからメッシュの選択状態を同期する"
    objects = selected_objects if selected_objects else context.objects_in_mode
    for obj in objects:
        sync_mesh_from_uv_obj(obj)
        obj.data.update()


def sync_mesh_from_uv_obj(obj):
    "UVからメッシュの選択状態を同期する"
    bm = bmesh.from_edit_mesh(obj.data)
    uv_layer = bm.loops.layers.uv.verify()
    for vert in bm.verts:
        vert.select = False
    bm.select_flush(False)

    for vert in bm.verts:
        vert.select = any(loop[uv_layer].select for loop in vert.link_loops)
    for face in bm.faces:
        if all(loop[uv_layer].select for loop in face.loops):
            face.select = True
    bm.select_flush(True)
    bmesh.update_edit_mesh(obj.data)


def get_uv_from_mirror_offset(obj, is_vertical):
    "ミラーモディファイアのオフセット設定を取得する"
    for mod in obj.modifiers:
        if mod.type != "MIRROR" or not mod.show_viewport:
            continue
        if is_vertical and mod.use_mirror_u and mod.mirror_offset_u:
            offset_u = 0.5 + mod.mirror_offset_u * 0.5
            return Vector((offset_u, 0))
        if not is_vertical and mod.use_mirror_v and mod.mirror_offset_v:
            offset_v = 0.5 + mod.mirror_offset_v * 0.5
            return Vector((0, offset_v))
    return None


def rotate_uv_faces(faces, angle, uv_layer, center):
    sin_a = math.sin(angle)
    cos_a = math.cos(angle)
    rot_matrix = Matrix(((cos_a, -sin_a), (sin_a, cos_a)))
    for face in faces:
        for loop in face.loops:
            loop_uv = loop[uv_layer]
            local = loop_uv.uv - center
            loop_uv.uv = rot_matrix @ local + center


def get_tile_co(offset_vector, uv_layer, loops):
    min_x = min(loop[uv_layer].uv.x for loop in loops)
    min_y = min(loop[uv_layer].uv.y for loop in loops)
    tile_u = int(min_x)
    tile_v = int(min_y)
    udim_x = tile_u + offset_vector.x
    udim_y = tile_v + offset_vector.y
    return Vector((udim_x, udim_y))


def get_bounds(uv_layer, faces):
    uv_coords = [loop[uv_layer].uv for face in faces for loop in face.loops]
    min_u = min(uv.x for uv in uv_coords)
    max_u = max(uv.x for uv in uv_coords)
    min_v = min(uv.y for uv in uv_coords)
    max_v = max(uv.y for uv in uv_coords)
    return min_u, max_u, min_v, max_v


def straight_uv_nodes(node_group, mode="GEOMETRY", keep_length=False, center=False):
    ordered_nodes = node_group.get_ordered_nodes()
    if len(ordered_nodes) <= 1:
        return

    start_uv = ordered_nodes[0].uv
    end_uv = ordered_nodes[-1].uv
    direction = end_uv - start_uv
    if abs(direction.x) > abs(direction.y):
        direction.y = 0
    else:
        direction.x = 0

    original_uv_length = node_group.get_sum_length(ordered_nodes) if keep_length else 0

    if mode == "GEOMETRY":
        total_3d_distance = 0
        cumulative_3d_distances = [0]
        for i in range(1, len(ordered_nodes)):
            dist = (ordered_nodes[i].vert.co - ordered_nodes[i - 1].vert.co).length
            total_3d_distance += dist
            cumulative_3d_distances.append(total_3d_distance)

        if total_3d_distance <= 0:
            return

        new_positions = {}
        for i, node in enumerate(ordered_nodes):
            t = cumulative_3d_distances[i] / total_3d_distance
            new_position = start_uv + direction * t
            new_positions[node] = new_position
    elif mode == "EVEN":
        new_positions = {}
        for i, node in enumerate(ordered_nodes):
            t = i / (len(ordered_nodes) - 1)
            new_position = start_uv + direction * t
            new_positions[node] = new_position
    else:
        total_uv_distance = sum(
            (ordered_nodes[i + 1].uv - ordered_nodes[i].uv).length for i in range(len(ordered_nodes) - 1)
        )
        if total_uv_distance <= 0:
            return

        new_positions = {}
        cumulative_uv_distance = 0
        for i, node in enumerate(ordered_nodes):
            if i > 0:
                cumulative_uv_distance += (node.uv - ordered_nodes[i - 1].uv).length
            t = cumulative_uv_distance / total_uv_distance
            new_position = start_uv + direction * t
            new_positions[node] = new_position

    if keep_length:
        new_uv_length = sum(
            (new_positions[ordered_nodes[i + 1]] - new_positions[ordered_nodes[i]]).length
            for i in range(len(ordered_nodes) - 1)
        )
        scale_factor = original_uv_length / new_uv_length if new_uv_length > 0 else 1
        for node, new_position in new_positions.items():
            scaled_position = start_uv + (new_position - start_uv) * scale_factor
            new_positions[node] = scaled_position

    if center:
        original_center = Vector((0, 0))
        for node in ordered_nodes:
            original_center += node.uv
        original_center /= len(ordered_nodes)

        aligned_center = Vector((0, 0))
        for pos in new_positions.values():
            aligned_center += pos
        aligned_center /= len(new_positions)

        center_offset = original_center - aligned_center

        for node in new_positions:
            new_positions[node] += center_offset

    for node, new_position in new_positions.items():
        node.uv = new_position
