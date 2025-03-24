import bpy
import bmesh
from mathutils import Vector


def sync_uv_from_mesh(context, selected_objects):
    objects = selected_objects if selected_objects else context.objects_in_mode
    for obj in objects:
        sync_uv_from_mesh_obj(obj)


def sync_uv_from_mesh_obj(obj):
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
    objects = selected_objects if selected_objects else context.selected_objects
    for obj in objects:
        sync_mesh_from_uv_obj(obj)
        obj.data.update()


def sync_mesh_from_uv_obj(obj):
    bm = bmesh.from_edit_mesh(obj.data)
    uv_layer = bm.loops.layers.uv.verify()

    for vert in bm.verts:
        vert.select = False
    bm.select_flush(False)

    for vert in bm.verts:
        vert.select = all(loop[uv_layer].select for loop in vert.link_loops)
    # for edge in bm.edges:
    #     if all(loop[uv_layer].select_edge for loop in edge.link_loops):
    #         edge.select = True
    for face in bm.faces:
        if all(loop[uv_layer].select for loop in face.loops):
            face.select = True
    bm.select_flush(True)
    bmesh.update_edit_mesh(obj.data)


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


# UV空間を基準にアイランドで分割
def split_uv_islands(uv_layer, selected_faces):
    islands = []

    def are_uv_connected(face1, face2):
        uv1 = set(tuple(loop[uv_layer].uv) for loop in face1.loops)
        uv2 = set(tuple(loop[uv_layer].uv) for loop in face2.loops)
        return len(uv1.intersection(uv2)) >= 2

    unassigned_faces = set(selected_faces)
    while unassigned_faces:
        start_face = unassigned_faces.pop()
        island = {start_face}
        to_check = {start_face}
        while to_check:
            current_face = to_check.pop()
            for edge in current_face.edges:
                for face in edge.link_faces:
                    if face in unassigned_faces and are_uv_connected(current_face, face):
                        island.add(face)
                        unassigned_faces.remove(face)
                        to_check.add(face)
        islands.append(list(island))
    return islands


def straight_uv_nodes(node_group, mode="GEOMETRY", keep_length=False, center=False):
    uv_nodes = list(node_group.nodes)
    uv_layer = node_group.uv_layer

    start_node = next((node for node in uv_nodes if len(node.neighbors) == 1), None)
    if start_node is None:
        start_node = min(uv_nodes)

    ordered_nodes = []
    visited = set()
    current_node = start_node
    while len(ordered_nodes) < len(uv_nodes):
        if current_node not in visited:
            ordered_nodes.append(current_node)
            visited.add(current_node)
        next_node = next((n for n in current_node.neighbors if n not in visited), None)
        if next_node is None:
            unvisited = set(uv_nodes) - visited
            if unvisited:
                current_node = min(unvisited, key=lambda n: (n.uv - current_node.uv).length)
            else:
                break
        else:
            current_node = next_node

    start_uv = ordered_nodes[0].uv
    end_uv = ordered_nodes[-1].uv
    direction = end_uv - start_uv

    if abs(direction.x) > abs(direction.y):
        direction.y = 0
    else:
        direction.x = 0

    original_uv_length = (
        sum((ordered_nodes[i + 1].uv - ordered_nodes[i].uv).length for i in range(len(ordered_nodes) - 1))
        if keep_length
        else 0
    )

    if len(ordered_nodes) <= 1:
        return

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
