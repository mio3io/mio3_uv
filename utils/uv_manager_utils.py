import math
from mathutils import Matrix, Vector


AXIS_INDEX_MAP = {
    "X": 0,
    "Y": 1,
    "Z": 2,
}

SECONDARY_AXIS_MAP = {
    "X": "Z",
    "Y": "Z",
    "Z": "Y",
}


def rotate_island(island, angle):
    if angle == 0.0:
        return False

    mid_u = (island.min_uv.x + island.max_uv.x) / 2.0
    mid_v = (island.min_uv.y + island.max_uv.y) / 2.0
    cos_angle = math.cos(angle)
    sin_angle = math.sin(angle)

    delta_u = mid_u - cos_angle * mid_u + sin_angle * mid_v
    delta_v = mid_v - sin_angle * mid_u - cos_angle * mid_v

    for face in island.faces:
        for loop in face.loops:
            uv = loop[island.uv_layer].uv
            new_u = cos_angle * uv.x - sin_angle * uv.y + delta_u
            new_v = sin_angle * uv.x + cos_angle * uv.y + delta_v
            loop[island.uv_layer].uv = Vector((new_u, new_v))


def find_rotation_auto(uv_layer, faces):
    sum_u = 0.0
    sum_v = 0.0

    for face in faces:
        prev_uv = face.loops[-1][uv_layer].uv
        for loop in face.loops:
            uv = loop[uv_layer].uv
            delta_u = uv.x - prev_uv.x
            delta_v = uv.y - prev_uv.y
            edge_angle = math.atan2(delta_v, delta_u)
            edge_angle *= 4.0
            sum_u += math.cos(edge_angle)
            sum_v += math.sin(edge_angle)
            prev_uv = uv

    return -math.atan2(sum_v, sum_u) / 4.0


def find_rotation_geometry(uv_layer, faces, axis, space="LOCAL", matrix_world=None):
    sum_u_co = Vector((0.0, 0.0, 0.0))
    sum_v_co = Vector((0.0, 0.0, 0.0))

    if space == "LOCAL":
        for face in faces:
            for fan in range(2, len(face.loops)):
                delta_uv0 = face.loops[fan - 1][uv_layer].uv - face.loops[0][uv_layer].uv
                delta_uv1 = face.loops[fan][uv_layer].uv - face.loops[0][uv_layer].uv

                mat = Matrix((delta_uv0, delta_uv1))
                mat.invert_safe()

                base_co = face.loops[0].vert.co
                delta_co0 = face.loops[fan - 1].vert.co - base_co
                delta_co1 = face.loops[fan].vert.co - base_co
                w = delta_co0.cross(delta_co1).length
                sum_u_co += (delta_co0 * mat[0][0] + delta_co1 * mat[0][1]) * w
                sum_v_co += (delta_co0 * mat[1][0] + delta_co1 * mat[1][1]) * w
    elif space == "WORLD":
        if matrix_world is None:
            raise ValueError("matrix_world is required when space is WORLD")

        for face in faces:
            for fan in range(2, len(face.loops)):
                delta_uv0 = face.loops[fan - 1][uv_layer].uv - face.loops[0][uv_layer].uv
                delta_uv1 = face.loops[fan][uv_layer].uv - face.loops[0][uv_layer].uv

                mat = Matrix((delta_uv0, delta_uv1))
                mat.invert_safe()

                base_co = matrix_world @ face.loops[0].vert.co
                delta_co0 = (matrix_world @ face.loops[fan - 1].vert.co) - base_co
                delta_co1 = (matrix_world @ face.loops[fan].vert.co) - base_co
                w = delta_co0.cross(delta_co1).length
                sum_u_co += (delta_co0 * mat[0][0] + delta_co1 * mat[0][1]) * w
                sum_v_co += (delta_co0 * mat[1][0] + delta_co1 * mat[1][1]) * w
    else:
        raise ValueError("Unsupported geometry space: {}".format(space))

    if axis not in AXIS_INDEX_MAP:
        raise ValueError("Unsupported geometry axis: {}".format(axis))

    axis_index = AXIS_INDEX_MAP[axis]
    primary_u = sum_u_co[axis_index]
    primary_v = sum_v_co[axis_index]

    if math.isclose(primary_u, 0.0, abs_tol=1e-8) and math.isclose(primary_v, 0.0, abs_tol=1e-8):
        secondary_axis = SECONDARY_AXIS_MAP.get(axis)
        if secondary_axis is not None:
            secondary_index = AXIS_INDEX_MAP[secondary_axis]
            return math.atan2(sum_u_co[secondary_index], sum_v_co[secondary_index])

    return math.atan2(primary_u, primary_v)