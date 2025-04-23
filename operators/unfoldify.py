import bpy
import bmesh
from bpy.props import BoolProperty, FloatProperty
from mathutils import Vector
from ..classes.operator import Mio3UVOperator
from ..classes.uv import UVIslandManager


class MIO3UV_OT_unfoldify(Mio3UVOperator):
    bl_idname = "uv.mio3_unfoldify"
    bl_label = "Unfoldify"
    bl_description = "Arrange islands vertically and horizontally based on their positional relationships in 3D space"
    bl_options = {"REGISTER", "UNDO"}

    align_rotation: BoolProperty(name="Orient World", default=True)
    group: BoolProperty(name="Group by Linked Faces", default=True)
    use_active: BoolProperty(name="Based on Active", default=False)
    offset_island: FloatProperty(name="Margin", default=0.02, min=0.001, max=0.1, step=0.1)
    offset_group: FloatProperty(name="Group Margin", default=0.02, min=0.001, max=0.1, step=0.1)

    def execute(self, context):
        self.start_time()
        self.objects = self.get_selected_objects(context)

        if self.align_rotation:
            bpy.ops.uv.align_rotation(method="GEOMETRY", axis="Z")

        use_uv_select_sync = context.tool_settings.use_uv_select_sync
        if use_uv_select_sync:
            self.sync_uv_from_mesh(context, self.objects)
            island_manager = UVIslandManager(self.objects, mesh_link_uv=True)
        else:
            island_manager = UVIslandManager(self.objects, extend=True)

        island_manager.set_orientation_mode("LOCAL")

        groups = []
        for obj in self.objects:
            islands = island_manager.islands_by_object[obj]
            bm = island_manager.bmesh_dict[obj]
            if islands:
                if self.group:
                    face_groups = self.find_groups(bm)
                    island_groups = self.find_islands(islands, face_groups)
                    for group in island_groups:
                        if group:
                            groups.append(group)
                else:
                    groups.append(islands)

        groups.sort(
            key=lambda group: (
                sum(island.center_3d_world.x for island in group) / len(group),
                sum(island.center_3d_world.y for island in group) / len(group),
                sum(island.center_3d_world.z for island in group) / len(group),
            )
        )

        group_bounds = []
        for group in groups:
            min_u, max_u, min_v, max_v = self.arrange_islands(group)
            group_bounds.append(
                {
                    "min_u": min_u,
                    "min_v": min_v,
                    "width": max_u - min_u,
                }
            )

        current_u = 0
        for _, (group, bounds) in enumerate(zip(groups, group_bounds)):
            offset = Vector((current_u - bounds["min_u"], 0 - bounds["min_v"]))
            for island in group:
                island.move(offset)
            current_u += bounds["width"] + self.offset_group

        island_manager.update_uvmeshes()

        if use_uv_select_sync:
            island_manager.restore_vertex_selection()

        self.print_time()
        return {"FINISHED"}

    def find_groups(self, bm):
        face_groups = []
        unprocessed = set(bm.faces)
        while unprocessed:
            current_group = set()
            faces_to_process = {unprocessed.pop()}
            while faces_to_process:
                face = faces_to_process.pop()
                current_group.add(face)
                for edge in face.edges:
                    for linked_face in edge.link_faces:
                        if linked_face in unprocessed:
                            unprocessed.remove(linked_face)
                            faces_to_process.add(linked_face)
            face_groups.append(current_group)
        return face_groups

    def find_islands(self, islands, face_groups):
        island_groups = [[] for _ in face_groups]
        for island in islands:
            island_face = next(iter(island.faces))
            for group_index, face_group in enumerate(face_groups):
                if island_face in face_group:
                    island_groups[group_index].append(island)
                    break
        return [group for group in island_groups if group]

    def arrange_islands(self, islands):
        base_island, other_islands = self.categorize_islands(islands)
        self.layout_islands(base_island, other_islands)

        min_u = min(island.min_uv.x for island in islands)
        max_u = max(island.max_uv.x for island in islands)
        min_v = min(island.min_uv.y for island in islands)
        max_v = max(island.max_uv.y for island in islands)

        return min_u, max_u, min_v, max_v

    def categorize_islands(self, islands):
        if not islands:
            return None, {"FRONT": [], "RIGHT": [], "LEFT": [], "TOP": [], "BOTTOM": [], "BACK": []}

        base_island = None
        other_islands = {"FRONT": [], "RIGHT": [], "LEFT": [], "TOP": [], "BOTTOM": [], "BACK": []}

        if self.use_active:
            base_island = self.get_active_island(islands)

        center = Vector((0, 0, 0))
        total_area = 0
        for island in islands:
            area = sum(face.calc_area() for face in island.faces)
            center += island.center_3d_local * area
            total_area += area
        if total_area > 0:
            center /= total_area

        for island in islands:
            if island == base_island:
                continue

            normal = sum((face.normal * face.calc_area() for face in island.faces), Vector()) / sum(
                face.calc_area() for face in island.faces
            )
            position = island.center_3d_local - center

            category = self.get_island_category(normal, position)
            other_islands[category].append(island)

        if not base_island:
            base_island = self.get_base_island(other_islands)

        return base_island, other_islands

    def get_island_category(self, normal, position):
        categories = {
            "FRONT": (-Vector((0, 1, 0)), position.y < 0),
            "BACK": (Vector((0, 1, 0)), position.y > 0),
            "LEFT": (-Vector((1, 0, 0)), position.x < 0),
            "RIGHT": (Vector((1, 0, 0)), position.x > 0),
            "TOP": (Vector((0, 0, 1)), position.z > 0),
            "BOTTOM": (-Vector((0, 0, 1)), position.z < 0),
        }
        best_category = max(categories.items(), key=lambda x: normal.dot(x[1][0]) + (0.5 if x[1][1] else 0))[0]
        return best_category

    def layout_islands(self, base_island, other_islands):
        margin = self.offset_island
        if not base_island:
            return

        current_v = base_island.min_uv.y - margin
        base_center_u = (base_island.min_uv.x + base_island.max_uv.x) / 2

        if other_islands["FRONT"]:
            sorted_front = self.sort_islands(other_islands["FRONT"], "FRONT")
            for island in sorted_front:
                island_center_u = (island.min_uv.x + island.max_uv.x) / 2
                u_offset = base_center_u - island_center_u
                offset = Vector((u_offset, current_v - island.height)) - Vector((0, island.min_uv.y))
                island.move(offset)
                current_v -= (island.max_uv.y - island.min_uv.y) + margin

        if other_islands["BOTTOM"]:
            sorted_bottom = self.sort_islands(other_islands["BOTTOM"], "BOTTOM")
            total_width = sum(island.width for island in sorted_bottom) + margin * (len(sorted_bottom) - 1)
            start_u = (base_island.min_uv.x + base_island.max_uv.x) / 2 - total_width / 2

            for island in sorted_bottom:
                offset = Vector((start_u, current_v - island.height)) - Vector((island.min_uv.x, island.min_uv.y))
                island.move(offset)
                start_u += island.width + margin

            # BOTTOMの高さ分下げる
            if sorted_bottom:
                max_height = max(island.height for island in sorted_bottom)
                current_v -= max_height + margin

        if other_islands["BACK"]:
            sorted_back = self.sort_islands(other_islands["BACK"], "BACK")
            for island in sorted_back:
                island_center_u = (island.min_uv.x + island.max_uv.x) / 2
                u_offset = base_center_u - island_center_u
                offset = Vector((u_offset, current_v)) - Vector((0, island.max_uv.y))
                island.move(offset)
                current_v -= (island.max_uv.y - island.min_uv.y) + margin

        if other_islands["TOP"]:
            sorted_top = self.sort_islands(other_islands["TOP"], "TOP")
            total_width = sum(island.width for island in sorted_top) + margin * (len(sorted_top) - 1)
            start_u = (base_island.min_uv.x + base_island.max_uv.x) / 2 - total_width / 2
            top_v = base_island.max_uv.y + margin
            for island in sorted_top:
                offset = Vector((start_u, top_v)) - Vector((island.min_uv.x, island.min_uv.y))
                island.move(offset)
                start_u += island.width + margin


        for direction, islands in other_islands.items():
            if not islands or direction not in ["RIGHT", "LEFT"]:
                continue
            sorted_islands = self.sort_islands(islands, direction)
            self.layout_vertical(sorted_islands, direction, base_island, margin)


    def layout_vertical(self, islands, direction, base_island, margin):
        current_v = base_island.max_uv.y
        ref_u = base_island.max_uv.x if direction == "RIGHT" else base_island.min_uv.x
        for island in islands:
            if direction == "RIGHT":
                offset = Vector((ref_u + margin, current_v)) - Vector((island.min_uv.x, island.max_uv.y))
            else:
                offset = Vector((ref_u - margin, current_v)) - Vector((island.max_uv.x, island.max_uv.y))

            island.move(offset)
            current_v -= (island.max_uv.y - island.min_uv.y) + margin

    def get_active_island(self, islands):
        active_obj = bpy.context.active_object
        if not active_obj or not active_obj.data.total_face_sel:
            return None

        active_element = bmesh.from_edit_mesh(active_obj.data).select_history.active
        if not active_element:
            return None

        for island in islands:
            if any(
                active_element in face.verts or active_element in face.edges or active_element == face
                for face in island.faces
            ):
                return island
        return None

    def get_base_island(self, other_islands):
        front_islands = other_islands["FRONT"]
        if front_islands:
            base_island = max(front_islands, key=lambda x: sum(face.calc_area() for face in x.faces))
            front_islands.remove(base_island)
            return base_island

        all_islands = [island for islands in other_islands.values() for island in islands]
        if not all_islands:
            return None

        base_island = max(all_islands, key=lambda x: sum(face.calc_area() for face in x.faces))
        for islands in other_islands.values():
            if base_island in islands:
                islands.remove(base_island)
                break

        return base_island

    def sort_islands(self, islands, direction):
        if direction == "TOP" or direction == "BOTTOM":
            # X 左から右 / Y 手前から奥
            return sorted(islands, key=lambda i: (i.center_3d_local.x, -i.center_3d_local.y))
        elif direction == "FRONT" or direction == "BACK":
            # Z 上から下 / X 左から右
            return sorted(islands, key=lambda i: (-i.center_3d_local.z, i.center_3d_local.x))
        elif direction == "LEFT" or direction == "RIGHT":
            # Z 上から下 / Y 手前から奥
            return sorted(islands, key=lambda i: (-i.center_3d_local.z, -i.center_3d_local.y))


classes = [MIO3UV_OT_unfoldify]


def register():
    for c in classes:
        bpy.utils.register_class(c)


def unregister():
    for c in classes:
        bpy.utils.unregister_class(c)
