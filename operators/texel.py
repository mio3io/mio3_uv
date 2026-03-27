import math
import bpy
import bmesh
from bpy.props import FloatProperty
from ..classes import UVIslandManager, Mio3UVOperator


COVERAGE_MASK_MAX_SIZE = 256
NAME_MOD_CHECKER_MAP = "Mio3CheckerMapModifier"


def get_texture_size(props, obj, use_checker=False):
    if use_checker:
        mod = obj.modifiers.get(NAME_MOD_CHECKER_MAP)
        if mod and mod.type == "NODES":
            mat = mod.get("Socket_2")
            if mat and hasattr(mat, "name") and mat.name.startswith("Mio3CheckerMapMat_"):
                size_str = mat.name[len("Mio3CheckerMapMat_") :]
                if size_str.isdigit():
                    size = int(size_str)
                    return size, size
    return int(props.texture_size_x), int(props.texture_size_y)


def calc_uv_face_area(face, uv_layer):
    if len(face.loops) < 3:
        return 0.0

    uv_coords = [loop[uv_layer].uv for loop in face.loops]
    uv_origin = uv_coords[0]
    total_area = 0.0
    for i in range(1, len(uv_coords) - 1):
        uv_a = uv_coords[i]
        uv_b = uv_coords[i + 1]
        total_area += 0.5 * abs(
            (uv_a.x - uv_origin.x) * (uv_b.y - uv_origin.y) - (uv_b.x - uv_origin.x) * (uv_a.y - uv_origin.y)
        )
    return total_area


def calc_face_world_area(face, obj):
    if obj is None or len(face.verts) < 3:
        return face.calc_area()

    world_matrix = obj.matrix_world
    origin = world_matrix @ face.verts[0].co
    total_area = 0.0

    for index in range(1, len(face.verts) - 1):
        v1 = world_matrix @ face.verts[index].co
        v2 = world_matrix @ face.verts[index + 1].co
        total_area += 0.5 * (v1 - origin).cross(v2 - origin).length

    return total_area


def calc_texel_density(face_area, uv_area, texture_size_x, texture_size_y):
    if face_area <= 0 or uv_area <= 0:
        return 0.0
    pixel_area = uv_area * texture_size_x * texture_size_y
    return math.sqrt(pixel_area / face_area)


class UV_OT_texel_density_coverage(Mio3UVOperator):
    bl_idname = "uv.mio3_texel_density_coverage"
    bl_label = "Calculate Coverage"
    bl_description = "Calculate UV coverage (occupancy) inside the 0-1 UV space"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        objects = self.get_selected_objects(context)
        props_s = context.scene.mio3uv
        props_w = context.window_manager.mio3uv
        use_udim = props_s.udim
        use_uv_select_sync = context.tool_settings.use_uv_select_sync

        mask_width, mask_height = COVERAGE_MASK_MAX_SIZE, COVERAGE_MASK_MAX_SIZE
        mask = bytearray(mask_width * mask_height)
        ones_buf = bytes([1]) * mask_width

        for face, uv_layer in self.get_coverage_faces(objects, use_uv_select_sync, props_w.texel_density_coverage_type):
            uv_coords = [(loop[uv_layer].uv.x, loop[uv_layer].uv.y) for loop in face.loops]
            if len(uv_coords) < 3:
                continue

            if use_udim:
                avg_u = sum(c[0] for c in uv_coords) / len(uv_coords)
                avg_v = sum(c[1] for c in uv_coords) / len(uv_coords)
                tile_u = int(math.floor(avg_u))
                tile_v = int(math.floor(avg_v))
                uv_coords = [(c[0] - tile_u, c[1] - tile_v) for c in uv_coords]

            clipped_coords = self.clip_polygon_to_boundary(uv_coords, 0, 0.0, True)
            clipped_coords = self.clip_polygon_to_boundary(clipped_coords, 0, 1.0, False)
            clipped_coords = self.clip_polygon_to_boundary(clipped_coords, 1, 0.0, True)
            clipped_coords = self.clip_polygon_to_boundary(clipped_coords, 1, 1.0, False)
            if len(clipped_coords) < 3:
                continue

            for triangle in self.triangulate_polygon(clipped_coords):
                self.fill_triangle_scanline(mask, mask_width, mask_height, ones_buf, triangle)

        props_w.texel_density_percent = mask.count(1) / (mask_width * mask_height) * 100.0

        return {"FINISHED"}

    @staticmethod
    def triangulate_polygon(uv_coords):
        if len(uv_coords) < 3:
            return []

        return [(uv_coords[0], uv_coords[index], uv_coords[index + 1]) for index in range(1, len(uv_coords) - 1)]

    @staticmethod
    def get_coverage_faces(objects, use_uv_select_sync, coverage_type):
        for obj in objects:
            bm = bmesh.from_edit_mesh(obj.data)
            if use_uv_select_sync and not bm.uv_select_sync_valid:
                bm.uv_select_sync_from_mesh()
            uv_layer = bm.loops.layers.uv.verify()
            if not uv_layer:
                continue

            for face in bm.faces:
                if face.hide:
                    continue

                if use_uv_select_sync:
                    if coverage_type == "SELECT":
                        if not face.uv_select:
                            continue
                else:
                    if not face.select:
                        continue
                    if coverage_type == "SELECT" and not face.uv_select:
                        continue

                yield face, uv_layer

    @staticmethod
    def fill_triangle_scanline(mask, width, height, ones_buf, tri):
        x0, y0 = tri[0][0] * width, tri[0][1] * height
        x1, y1 = tri[1][0] * width, tri[1][1] * height
        x2, y2 = tri[2][0] * width, tri[2][1] * height

        if y0 > y1:
            x0, y0, x1, y1 = x1, y1, x0, y0
        if y0 > y2:
            x0, y0, x2, y2 = x2, y2, x0, y0
        if y1 > y2:
            x1, y1, x2, y2 = x2, y2, x1, y1

        min_py = max(0, int(math.ceil(y0 - 0.5)))
        max_py = min(height - 1, int(math.floor(y2 - 0.5)))
        if min_py > max_py:
            return

        dy02 = y2 - y0
        dy01 = y1 - y0
        dy12 = y2 - y1
        dx02 = x2 - x0
        dx01 = x1 - x0
        dx12 = x2 - x1
        inv02 = 1.0 / dy02 if dy02 > 0 else 0.0
        inv01 = 1.0 / dy01 if dy01 > 0 else 0.0
        inv12 = 1.0 / dy12 if dy12 > 0 else 0.0

        for py in range(min_py, max_py + 1):
            sy = py + 0.5
            xa = x0 + (sy - y0) * inv02 * dx02 if dy02 > 0 else x0

            if sy < y1:
                xb = x0 + (sy - y0) * inv01 * dx01 if dy01 > 0 else x0
            else:
                xb = x1 + (sy - y1) * inv12 * dx12 if dy12 > 0 else x1

            if xa > xb:
                xa, xb = xb, xa

            left = max(0, int(math.ceil(xa - 0.5)))
            right = min(width - 1, int(math.floor(xb - 0.5)))

            if left <= right:
                start = py * width + left
                span = right - left + 1
                mask[start : start + span] = ones_buf[:span]

    @staticmethod
    def clip_polygon_to_boundary(uv_coords, axis_index, boundary, keep_greater):
        if not uv_coords:
            return []

        clipped_coords = []
        previous_uv = uv_coords[-1]
        previous_inside = previous_uv[axis_index] >= boundary if keep_greater else previous_uv[axis_index] <= boundary

        for current_uv in uv_coords:
            current_inside = current_uv[axis_index] >= boundary if keep_greater else current_uv[axis_index] <= boundary

            if current_inside != previous_inside:
                delta = current_uv[axis_index] - previous_uv[axis_index]
                if delta != 0:
                    factor = (boundary - previous_uv[axis_index]) / delta
                    clipped_coords.append(
                        (
                            previous_uv[0] + (current_uv[0] - previous_uv[0]) * factor,
                            previous_uv[1] + (current_uv[1] - previous_uv[1]) * factor,
                        )
                    )

            if current_inside:
                clipped_coords.append(current_uv)

            previous_uv = current_uv
            previous_inside = current_inside

        return clipped_coords


class UV_OT_texel_density_get(Mio3UVOperator):
    bl_idname = "uv.mio3_texel_density_get"
    bl_label = "Texel Density Get"
    bl_description = "Get the texel density of the selected UVs"
    bl_options = {"REGISTER", "UNDO"}

    @classmethod
    def poll(cls, context):
        return context.active_object and context.active_object.type == "MESH"

    def execute(self, context):
        props_s = context.scene.mio3uv
        props_w = context.window_manager.mio3uv
        is_edit_mode = context.active_object.mode == "EDIT"
        use_uv_select_sync = context.tool_settings.use_uv_select_sync

        if not is_edit_mode:
            bpy.ops.object.mode_set(mode="EDIT")
            island_manager = UVIslandManager([context.active_object], sync=use_uv_select_sync, mesh_all=True)
        else:
            objects = self.get_selected_objects(context)
            island_manager = UVIslandManager(objects, sync=use_uv_select_sync)

        total_face_area = 0.0
        weighted_density = 0.0

        for island in island_manager.islands:
            if is_edit_mode:
                faces = self.get_selected_faces(island)
                if not faces:
                    continue
            else:
                faces = island.faces

            face_area = sum(calc_face_world_area(face, island.obj) for face in faces)
            uv_area = sum(calc_uv_face_area(face, island.uv_layer) for face in faces)
            tex_x, tex_y = get_texture_size(props_s, island.obj, props_w.texel_use_checker)
            density = calc_texel_density(face_area, uv_area, tex_x, tex_y)
            if density <= 0:
                continue

            total_face_area += face_area
            weighted_density += density * face_area

        if not is_edit_mode:
            bpy.ops.object.mode_set(mode="OBJECT")

        if total_face_area <= 0:
            return {"CANCELLED"}

        props_s.texel_density = weighted_density / total_face_area
        return {"FINISHED"}

    def get_selected_faces(self, island):
        selected_faces = []

        for face in island.faces:
            if face.hide:
                continue
            if island.sync:
                if face.uv_select:
                    selected_faces.append(face)
            else:
                if face.select and face.uv_select:
                    selected_faces.append(face)

        return selected_faces


class UV_OT_texel_density_set(Mio3UVOperator):
    bl_idname = "uv.mio3_texel_density_set"
    bl_label = "Texel Density Set"
    bl_description = "Set the texel density of the selected UVs"
    bl_options = {"REGISTER", "UNDO"}

    @classmethod
    def poll(cls, context):
        return context.active_object and context.active_object.type == "MESH"

    td: FloatProperty(name="Texel Density", default=0, precision=4, options={"SKIP_SAVE", "HIDDEN"})

    def execute(self, context):
        props_s = context.scene.mio3uv
        use_uv_select_sync = context.tool_settings.use_uv_select_sync

        is_edit_mode = context.active_object.mode == "EDIT"

        if not is_edit_mode:
            bpy.ops.object.mode_set(mode="EDIT")
            objects = [obj for obj in context.selected_objects if obj.type == "MESH"]
            island_manager = UVIslandManager(objects, sync=use_uv_select_sync, mesh_all=True)
        else:
            objects = self.get_selected_objects(context)
            island_manager = UVIslandManager(objects, sync=use_uv_select_sync)

        props_w = context.window_manager.mio3uv
        for island in island_manager.islands:
            tex_x, tex_y = get_texture_size(props_s, island.obj, props_w.texel_use_checker)
            face_area = sum(calc_face_world_area(face, island.obj) for face in island.faces)
            uv_area = sum(calc_uv_face_area(face, island.uv_layer) for face in island.faces)
            current_density = calc_texel_density(face_area, uv_area, tex_x, tex_y)
            if current_density <= 0:
                continue

            scale_factor = self.td / current_density
            if scale_factor <= 0:
                continue

            center = island.center.copy()
            for face in island.faces:
                for loop in face.loops:
                    uv = loop[island.uv_layer].uv.copy()
                    loop[island.uv_layer].uv = center + (uv - center) * scale_factor
            island.update_bounds()

            island_manager.update_uvmeshes()

        if not is_edit_mode:
            bpy.ops.object.mode_set(mode="OBJECT")

        return {"FINISHED"}


classes = [UV_OT_texel_density_coverage, UV_OT_texel_density_get, UV_OT_texel_density_set]


def register():
    for cls in classes:
        bpy.utils.register_class(cls)


def unregister():
    for cls in classes:
        bpy.utils.unregister_class(cls)
