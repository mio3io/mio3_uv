import bpy
from mathutils import Vector
from bpy.props import BoolProperty, FloatProperty
from ..classes import UVIslandManager, UVIsland, Mio3UVOperator
from ..utils.uv_manager_utils import find_rotation_geometry, rotate_island


class IslandCategories:
    DIRECTIONS = ("FRONT", "RIGHT", "LEFT", "TOP", "BOTTOM", "BACK")

    def __init__(self):
        self.front = []
        self.right = []
        self.left = []
        self.top = []
        self.bottom = []
        self.back = []

    def get(self, direction):
        return getattr(self, direction.lower())

    def add(self, direction, island):
        self.get(direction).append(island)

    def items(self):
        for direction in self.DIRECTIONS:
            yield direction, self.get(direction)

    def values(self):
        for _, islands in self.items():
            yield islands


class MIO3UV_OT_unfoldify(Mio3UVOperator):
    CATEGORY_AXES = {
        "FRONT": (-Vector((0, 1, 0)), "y", -1),
        "BACK": (Vector((0, 1, 0)), "y", 1),
        "LEFT": (-Vector((1, 0, 0)), "x", -1),
        "RIGHT": (Vector((1, 0, 0)), "x", 1),
        "TOP": (Vector((0, 0, 1)), "z", 1),
        "BOTTOM": (-Vector((0, 0, 1)), "z", -1),
    }

    bl_idname = "uv.mio3_unfoldify"
    bl_label = "Unfoldify"
    bl_description = "Arrange islands vertically and horizontally based on their positional relationships in 3D space"
    bl_options = {"REGISTER", "UNDO"}

    align_rotation: BoolProperty(name="Orient World", default=True)
    group: BoolProperty(name="Group by Linked Faces", default=True)
    offset_island: FloatProperty(name="Spacing", default=0.02, min=0.001, max=0.1, step=0.1)
    offset_group: FloatProperty(name="Group Spacing", default=0.02, min=0.001, max=0.1, step=0.1)

    def execute(self, context):
        self.start_time()
        objects = self.get_selected_objects(context)

        use_uv_select_sync = context.tool_settings.use_uv_select_sync

        island_manager = UVIslandManager(objects, sync=use_uv_select_sync)
        if not island_manager.islands:
            return {"CANCELLED"}

        island_manager.set_orientation_mode("LOCAL")

        if self.align_rotation:
            for island in island_manager.islands:
                angle = find_rotation_geometry(island.uv_layer, island.faces, "Z", "WORLD", island.obj.matrix_world)
                rotate_island(island, angle)
                island.update_bounds()

        groups = self.collect_groups(island_manager)

        group_bounds = []
        for group in groups:
            group_bounds.append(self.arrange_islands(group))

        current_u = 0
        for _, (group, bounds) in enumerate(zip(groups, group_bounds)):
            offset = Vector((current_u - bounds["min_u"], 0 - bounds["min_v"]))
            for island in group:
                island.move(offset, True)
            current_u += bounds["width"] + self.offset_group

        island_manager.update_uvmeshes(True)

        self.print_time()
        return {"FINISHED"}

    def collect_groups(self, island_manager):
        groups = []
        islands_by_object = {}
        for island in island_manager.islands:
            islands_by_object.setdefault(id(island.obj_info), []).append(island)

        for obj_info in island_manager.collections:
            object_islands = islands_by_object.get(id(obj_info), [])
            if not object_islands:
                continue

            if not self.group:
                groups.append(object_islands)
                continue

            groups.extend(self.find_groups(obj_info.bm, object_islands))

        groups.sort(key=self.get_group_sort_key)
        return groups

    def get_group_sort_key(self, group):
        center = sum((island.center_3d_world for island in group), Vector()) / len(group)
        return tuple(center.xyz)

    def find_groups(self, bm, islands):
        island_order = {island: index for index, island in enumerate(islands)}
        face_to_island = {face: island for island in islands for face in island.faces}
        island_groups = []
        unprocessed = set(bm.faces)
        while unprocessed:
            current_group = set()
            faces_to_process = {unprocessed.pop()}
            while faces_to_process:
                face = faces_to_process.pop()
                island = face_to_island.get(face)
                if island is not None:
                    current_group.add(island)
                for edge in face.edges:
                    for linked_face in edge.link_faces:
                        if linked_face in unprocessed:
                            unprocessed.remove(linked_face)
                            faces_to_process.add(linked_face)
            if current_group:
                island_groups.append(sorted(current_group, key=island_order.get))
        return island_groups

    def arrange_islands(self, islands):
        base_island, other_islands = self.categorize_islands(islands)
        self.layout_islands(base_island, other_islands)

        min_u, max_u, min_v, _ = self.get_bounds(islands)
        return {"min_u": min_u, "min_v": min_v, "width": max_u - min_u}

    def get_bounds(self, islands):
        min_u = min(island.min_uv.x for island in islands)
        max_u = max(island.max_uv.x for island in islands)
        min_v = min(island.min_uv.y for island in islands)
        max_v = max(island.max_uv.y for island in islands)
        return min_u, max_u, min_v, max_v

    def build_island_data(self, islands):
        island_data = {}
        for island in islands:
            area = 0.0
            normal = Vector((0, 0, 0))
            for face in island.faces:
                face_area = face.calc_area()
                area += face_area
                normal += face.normal * face_area
            if area > 0:
                normal /= area
            island_data[island] = {"area": area, "normal": normal}
        return island_data

    def categorize_islands(self, islands):
        if not islands:
            return None, IslandCategories()

        island_data = self.build_island_data(islands)
        other_islands = IslandCategories()

        center = Vector((0, 0, 0))
        total_area = 0
        for island in islands:
            area = island_data[island]["area"]
            center += island.center_3d_local * area
            total_area += area
        if total_area > 0:
            center /= total_area

        for island in islands:
            position = island.center_3d_local - center
            category = self.get_island_category(island_data[island]["normal"], position)
            other_islands.add(category, island)

        base_island = self.get_base_island(other_islands, island_data)

        return base_island, other_islands

    def get_island_category(self, normal, position):
        return max(
            self.CATEGORY_AXES.items(),
            key=lambda item: normal.dot(item[1][0]) + (0.5 if getattr(position, item[1][1]) * item[1][2] > 0 else 0),
        )[0]

    def move_island_to(self, island, *, min_u=None, min_v=None, max_u=None, max_v=None):
        target_min_u = island.min_uv.x if min_u is None else min_u
        target_min_v = island.min_uv.y if min_v is None else min_v
        if max_u is not None:
            target_min_u = max_u - island.width
        if max_v is not None:
            target_min_v = max_v - island.height
        island.move(Vector((target_min_u - island.min_uv.x, target_min_v - island.min_uv.y)), True)

    def layout_centered_stack(self, islands, center_u, start_v, margin, align_top=False):
        current_v = start_v
        for island in islands:
            min_u = center_u - island.width / 2
            if align_top:
                self.move_island_to(island, min_u=min_u, max_v=current_v)
            else:
                self.move_island_to(island, min_u=min_u, min_v=current_v - island.height)
            current_v -= island.height + margin
        return current_v

    def layout_horizontal_row(self, islands, center_u, start_v, margin, align_top=False):
        total_width = sum(island.width for island in islands) + margin * (len(islands) - 1)
        current_u = center_u - total_width / 2
        for island in islands:
            if align_top:
                self.move_island_to(island, min_u=current_u, max_v=start_v)
            else:
                self.move_island_to(island, min_u=current_u, min_v=start_v)
            current_u += island.width + margin

    def layout_side_stack(self, islands, direction, base_island, margin):
        current_v = base_island.max_uv.y
        ref_u = base_island.max_uv.x if direction == "RIGHT" else base_island.min_uv.x
        for island in islands:
            if direction == "RIGHT":
                self.move_island_to(island, min_u=ref_u + margin, max_v=current_v)
            else:
                self.move_island_to(island, max_u=ref_u - margin, max_v=current_v)
            current_v -= island.height + margin

    def layout_islands(self, base_island: UVIsland, other_islands):
        margin = self.offset_island
        if not base_island:
            return

        current_v = base_island.min_uv.y - margin
        base_center_u = base_island.center.x

        if other_islands.front:
            islands_front = self.sort_islands(other_islands.front, "FRONT")
            current_v = self.layout_centered_stack(islands_front, base_center_u, current_v, margin)

        if other_islands.bottom:
            islands_bottom = self.sort_islands(other_islands.bottom, "BOTTOM")
            self.layout_horizontal_row(islands_bottom, base_center_u, current_v, margin, align_top=True)
            current_v -= max(island.height for island in islands_bottom) + margin

        if other_islands.back:
            islands_back = self.sort_islands(other_islands.back, "BACK")
            current_v = self.layout_centered_stack(islands_back, base_center_u, current_v, margin, align_top=True)

        if other_islands.top:
            islands_top = self.sort_islands(other_islands.top, "TOP")
            top_v = base_island.max_uv.y + margin
            self.layout_horizontal_row(islands_top, base_center_u, top_v, margin)

        for direction, islands in other_islands.items():
            if not islands or direction not in ["RIGHT", "LEFT"]:
                continue
            self.layout_side_stack(self.sort_islands(islands, direction), direction, base_island, margin)

    def get_base_island(self, other_islands, island_data):
        front_islands = other_islands.front
        if front_islands:
            base_island = max(front_islands, key=lambda island: island_data[island]["area"])
            front_islands.remove(base_island)
            return base_island

        all_islands = [island for islands in other_islands.values() for island in islands]
        if not all_islands:
            return None

        base_island = max(all_islands, key=lambda island: island_data[island]["area"])
        for islands in other_islands.values():
            if base_island in islands:
                islands.remove(base_island)
                break

        return base_island

    def sort_islands(self, islands, direction):
        sort_keys = {
            "TOP": lambda island: (island.center_3d_local.x, -island.center_3d_local.y),
            "BOTTOM": lambda island: (island.center_3d_local.x, -island.center_3d_local.y),
            "FRONT": lambda island: (-island.center_3d_local.z, island.center_3d_local.x),
            "BACK": lambda island: (-island.center_3d_local.z, island.center_3d_local.x),
            "LEFT": lambda island: (-island.center_3d_local.z, -island.center_3d_local.y),
            "RIGHT": lambda island: (-island.center_3d_local.z, -island.center_3d_local.y),
        }
        return sorted(islands, key=sort_keys[direction])


def register():
    bpy.utils.register_class(MIO3UV_OT_unfoldify)


def unregister():
    bpy.utils.unregister_class(MIO3UV_OT_unfoldify)
