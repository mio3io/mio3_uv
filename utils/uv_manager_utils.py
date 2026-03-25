import math
from mathutils import Matrix, Vector


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


def find_rotation_geometry(uv_layer, faces, axis):
    sum_u_co = Vector((0.0, 0.0, 0.0))
    sum_v_co = Vector((0.0, 0.0, 0.0))
    for face in faces:
        for fan in range(2, len(face.loops)):
            delta_uv0 = face.loops[fan - 1][uv_layer].uv - face.loops[0][uv_layer].uv
            delta_uv1 = face.loops[fan][uv_layer].uv - face.loops[0][uv_layer].uv

            mat = Matrix((delta_uv0, delta_uv1))
            mat.invert_safe()

            delta_co0 = face.loops[fan - 1].vert.co - face.loops[0].vert.co
            delta_co1 = face.loops[fan].vert.co - face.loops[0].vert.co
            w = delta_co0.cross(delta_co1).length
            sum_u_co += (delta_co0 * mat[0][0] + delta_co1 * mat[0][1]) * w
            sum_v_co += (delta_co0 * mat[1][0] + delta_co1 * mat[1][1]) * w

    if axis == "X":
        axis_index = 0
    elif axis == "Y":
        axis_index = 1
    elif axis == "Z":
        axis_index = 2
    else:
        raise ValueError("Unsupported geometry axis: {}".format(axis))

    return math.atan2(sum_u_co[axis_index], sum_v_co[axis_index])
