import bpy
import bmesh
import time
from bpy.props import BoolProperty, FloatProperty, EnumProperty
from mathutils import Vector
from ..utils import get_bounds, split_uv_islands
from ..icons import preview_collections
from ..classes.operator import Mio3UVOperator


class MIO3UV_OT_unfoldify(Mio3UVOperator):
    bl_idname = "uv.mio3_unfoldify"
    bl_label = "Unfoldify"
    bl_description = "Unfoldify"
    bl_options = {"REGISTER", "UNDO"}

    offset_island: FloatProperty(name="Offset Island", default=0.02, min=0.001, max=0.1, step=0.1)
    offset_unit: FloatProperty(name="Offset Unit", default=0.04, min=0, max=1, step=0.1)
    separate_units: BoolProperty(name="Separate Units", default=True)
    prioritize_active: BoolProperty(name="Active Island", default=False)
    align_rotation: BoolProperty(name="Align Rotation", default=True)

    def execute(self, context):
        self.start_time = time.time()
        self.objects = self.get_selected_objects(context)

        obj = context.active_object
        bm = bmesh.from_edit_mesh(obj.data)
        uv_layer = bm.loops.layers.uv.active

        # island_manager = UVIslandManager([context.active_object])
        # for island in island_manager.islands:
        #     print(island)

        if self.align_rotation:
            bpy.ops.uv.align_rotation(method="GEOMETRY", axis="Z")

        self.active_element = bm.select_history.active

        if self.separate_units:
            selected_faces = set(face for face in bm.faces if face.select)
            units = self.get_units(selected_faces)
            sorted_units = self.sort_units_by_uv_position(units, uv_layer)
            self.arrange_units(bm, uv_layer, sorted_units)
        else:
            all_faces = [face for face in bm.faces if face.select]
            self.arrange_uv_islands(bm, uv_layer, all_faces)

        bmesh.update_edit_mesh(obj.data)
        self.print_time(time.time() - self.start_time)
        return {"FINISHED"}

    def get_units(self, selected_faces):
        islands = []
        while selected_faces:
            island = set()
            to_check = [selected_faces.pop()]
            while to_check:
                face = to_check.pop()
                if face not in island and face.select:
                    island.add(face)
                    for edge in face.edges:
                        for linked_face in edge.link_faces:
                            if linked_face.select and linked_face not in island:
                                to_check.append(linked_face)
            selected_faces -= island
            islands.append(island)
        return islands

    def arrange_units(self, bm, uv_layer, units):
        current_u = current_v = 0.0
        for unit in units:
            min_u, max_u, min_v, max_v = self.arrange_uv_islands(bm, uv_layer, unit)
            width = max_u - min_u
            offset = Vector((current_u - min_u, -min_v))
            self.move_uv_island(uv_layer, unit, offset)
            current_u += width + self.offset_unit
            current_v = max(current_v, max_v - min_v)

    def sort_units_by_uv_position(self, units, uv_layer):
        def get_unit_uv_center(unit):
            uv_coords = [loop[uv_layer].uv for face in unit for loop in face.loops]
            avg_u = sum(uv.x for uv in uv_coords) / len(uv_coords)
            avg_v = sum(uv.y for uv in uv_coords) / len(uv_coords)
            return (avg_u, avg_v)

        return sorted(units, key=get_unit_uv_center)

    def arrange_uv_islands(self, bm, uv_layer, selected_faces):
        islands = split_uv_islands(uv_layer, selected_faces)
        front_island, other_islands = self.categorize_islands(islands)
        self.layout_islands(uv_layer, front_island, other_islands)
        all_faces = [face for island in islands for face in island]
        return get_bounds(uv_layer, all_faces)

    def categorize_islands(self, islands):
        front_island = None
        other_islands = {"FRONT": [], "RIGHT": [], "LEFT": [], "TOP": [], "BOTTOM": [], "BACK": []}

        active_island = self.find_active_island(islands) if self.prioritize_active else None
        bbox_center = self.calculate_bbox_center(islands)

        for island in islands:
            avg_normal = self.get_average_normal(island)
            island_center = self.get_island_center(island)
            normal_category = self.get_category(avg_normal)
            position_category = self.get_category(island_center - bbox_center)
            final_category = self.combine_categories(normal_category, position_category)

            if island == active_island:
                front_island = island
            else:
                other_islands[final_category].append(island)

        if not front_island:
            front_island = self.select_front_island(other_islands)

        return front_island, other_islands

    def calculate_bbox_center(self, islands):
        all_verts = [v for island in islands for face in island for v in face.verts]
        bbox_min = Vector(
            (min(v.co.x for v in all_verts), min(v.co.y for v in all_verts), min(v.co.z for v in all_verts))
        )
        bbox_max = Vector(
            (max(v.co.x for v in all_verts), max(v.co.y for v in all_verts), max(v.co.z for v in all_verts))
        )
        return (bbox_min + bbox_max) / 2

    def get_average_normal(self, faces):
        avg_normal = Vector((0, 0, 0))
        total_area = 0
        for face in faces:
            area = face.calc_area()
            avg_normal += face.normal * area
            total_area += area
        return (avg_normal / total_area).normalized() if total_area > 0 else Vector((0, 0, 0))

    def get_island_center(self, faces):
        center = Vector((0, 0, 0))
        total_area = 0
        for face in faces:
            area = face.calc_area()
            center += face.calc_center_median() * area
            total_area += area
        return center / total_area if total_area > 0 else Vector((0, 0, 0))

    def get_category(self, vector):
        abs_vector = [abs(vector.x), abs(vector.y), abs(vector.z)]
        dominant_axis = abs_vector.index(max(abs_vector))
        if dominant_axis == 0:  # X
            return "RIGHT" if vector.x > 0 else "LEFT"
        elif dominant_axis == 1:  # Y
            return "BACK" if vector.y > 0 else "FRONT"
        else:  # Z
            return "TOP" if vector.z > 0 else "BOTTOM"

    def combine_categories(self, normal_category, position_category):
        if normal_category == position_category:
            return normal_category
        opposites = {
            "FRONT": "BACK",
            "BACK": "FRONT",
            "LEFT": "RIGHT",
            "RIGHT": "LEFT",
            "TOP": "BOTTOM",
            "BOTTOM": "TOP",
        }
        return position_category if opposites[normal_category] == position_category else normal_category

    def select_front_island(self, other_islands):
        if other_islands["FRONT"]:
            front_island = max(other_islands["FRONT"], key=lambda x: sum(face.calc_area() for face in x))
            other_islands["FRONT"].remove(front_island)
        else:
            front_island = max(
                [island for category in other_islands.values() for island in category],
                key=lambda x: sum(face.calc_area() for face in x),
            )
            for category, islands in other_islands.items():
                if front_island in islands:
                    islands.remove(front_island)
                    break
        return front_island

    def find_active_island(self, islands):
        if not self.active_element:
            return None

        for island in islands:
            for face in island:
                if isinstance(self.active_element, bmesh.types.BMFace):
                    if self.active_element == face:
                        return island
                elif isinstance(self.active_element, bmesh.types.BMEdge):
                    if self.active_element in face.edges:
                        return island
                elif isinstance(self.active_element, bmesh.types.BMVert):
                    if self.active_element in face.verts:
                        return island
        return None

    def get_island_3d_position(self, island):
        total_pos = Vector((0, 0, 0))
        total_area = 0
        for face in island:
            face_center = face.calc_center_median()
            face_area = face.calc_area()
            total_pos += face_center * face_area
            total_area += face_area
        return total_pos / total_area if total_area > 0 else Vector((0, 0, 0))

    def sort_islands_by_3d_position(self, islands, direction):
        if direction == "TOP" or direction == "BOTTOM":
            # X 左から右 / Y 手前から奥
            return sorted(islands, key=lambda i: (self.get_island_3d_position(i).x, -self.get_island_3d_position(i).y))
        elif direction == "FRONT" or direction == "BACK":
            # Z 上から下 / X 左から右
            return sorted(islands, key=lambda i: (self.get_island_3d_position(i).z, -self.get_island_3d_position(i).x))
        elif direction == "LEFT" or direction == "RIGHT":
            # Z 上から下 / Y 手前から奥
            return sorted(islands, key=lambda i: (-self.get_island_3d_position(i).z, -self.get_island_3d_position(i).y))

    def layout_islands(self, uv_layer, front_island, other_islands):
        margin = self.offset_island
        front_min_u, front_max_u, front_min_v, front_max_v = get_bounds(uv_layer, front_island)
        front_center_u = (front_min_u + front_max_u) / 2

        layout_data = {
            "lowest_v": front_min_v,
            "highest_v": front_max_v,
            "leftmost_u": front_min_u,
            "rightmost_u": front_max_u,
            "front_center_u": front_center_u,
        }

        for direction, islands in other_islands.items():
            if not islands:
                continue
            sorted_islands = self.sort_islands_by_3d_position(islands, direction)
            if direction in ["RIGHT", "LEFT"]:
                self.layout_vertical(uv_layer, sorted_islands, direction, layout_data, margin)
            else:
                self.layout_horizontal(uv_layer, sorted_islands, direction, layout_data, margin)

    def layout_vertical(self, uv_layer, islands, direction, layout_data, margin):
        current_v = layout_data["highest_v"]
        for island in islands:
            min_u, max_u, min_v, max_v = get_bounds(uv_layer, island)
            width, height = max_u - min_u, max_v - min_v
            if direction == "RIGHT":
                offset = Vector((layout_data["rightmost_u"] + margin, current_v)) - Vector((min_u, max_v))
            else:
                offset = Vector((layout_data["leftmost_u"] - margin, current_v)) - Vector((max_u, max_v))
            self.move_uv_island(uv_layer, island, offset)
            current_v -= height + margin

    def layout_horizontal(self, uv_layer, islands, direction, layout_data, margin):
        group_width = sum(get_bounds(uv_layer, island)[1] - get_bounds(uv_layer, island)[0] for island in islands)
        group_width += margin * (len(islands) - 1)
        start_u = layout_data["front_center_u"] - group_width / 2

        if direction == "TOP":
            base_v = layout_data["highest_v"] + margin
        else:
            base_v = layout_data["lowest_v"] - margin

        max_height = 0
        for island in islands:
            min_u, max_u, min_v, max_v = get_bounds(uv_layer, island)
            width, height = max_u - min_u, max_v - min_v
            max_height = max(max_height, height)

        for island in islands:
            min_u, max_u, min_v, max_v = get_bounds(uv_layer, island)
            width, height = max_u - min_u, max_v - min_v

            if direction == "TOP":
                offset = Vector((start_u, base_v + (max_height - height) / 2)) - Vector((min_u, min_v))
                layout_data["highest_v"] = max(layout_data["highest_v"], base_v + max_height)
            else:
                offset = Vector((start_u, base_v - max_height + (max_height - height) / 2)) - Vector((min_u, min_v))
                layout_data["lowest_v"] = min(layout_data["lowest_v"], base_v - max_height)

            self.move_uv_island(uv_layer, island, offset)
            start_u += width + margin

    def move_uv_island(self, uv_layer, faces, offset):
        for face in faces:
            for loop in face.loops:
                loop[uv_layer].uv += offset


classes = [MIO3UV_OT_unfoldify]


def register():
    for c in classes:
        bpy.utils.register_class(c)


def unregister():
    for c in classes:
        bpy.utils.unregister_class(c)
