import bpy
import math
from bpy.props import EnumProperty
from mathutils import Vector
from ..classes import UVIslandManager, Mio3UVOperator
from ..utils.uv_manager_utils import find_rotation_auto, find_rotation_geometry, rotate_island


class MIO3UV_OT_body_preset(Mio3UVOperator):
    bl_idname = "uv.mio3_body_preset"
    bl_label = "Auto Body Parts"
    bl_description = (
        "Select hair strands or fingers to auto-align rotation and order.\nClassify by parts if whole body is selected"
    )
    bl_options = {"REGISTER", "UNDO"}

    type: EnumProperty(
        name="Axis",
        default="AUTO",
        items=[
            ("AUTO", "Auto", ""),
            ("HAND_R", "Hand R", ""),
            ("HAND_L", "Hand L", ""),
            ("FOOT_R", "Foot R", ""),
            ("FOOT_L", "Foot L", ""),
            ("HAIR_F", "Front Hair", ""),
            ("HAIR_B", "Back Hair", ""),
            ("BUTTON", "Button", ""),
            ("BODY", "Body", ""),
        ],
    )

    align_uv: EnumProperty(name="Align", default="X", items=[("X", "Align H", ""), ("Y", "Align V", "")])

    def execute(self, context):
        self.start_time()
        objects = self.get_selected_objects(context)
        use_uv_select_sync = context.tool_settings.use_uv_select_sync

        island_manager = UVIslandManager(objects, sync=use_uv_select_sync)
        if not island_manager.islands:
            return {"CANCELLED"}

        all_centers = [island.center_3d for island in island_manager.islands]
        avg_center = self.average_vectors(all_centers)

        bound_box = [Vector(point) @ context.active_object.matrix_world for point in context.active_object.bound_box]
        min_co = Vector((min(point.x for point in bound_box), min(point.y for point in bound_box), min(point.z for point in bound_box)))
        max_co = Vector((max(point.x for point in bound_box), max(point.y for point in bound_box), max(point.z for point in bound_box)))
        body_reference = self.get_body_reference(island_manager, max_co, min_co)

        if self.type == "AUTO":
            parts_type = self.get_humanoid_parts(avg_center, max_co, min_co, body_reference)
            if parts_type == "HEAD":
                parts_type = "HAIR_F"
        else:
            parts_type = self.type

        if parts_type == "BODY":
            self.find_groups(context, island_manager, max_co, min_co, body_reference)
            island_manager.update_uvmeshes()
        else:
            if parts_type in {"HAND_R", "HAND_L"}:
                self.rotation_islands(island_manager, (("GEOMETRY", "X"), ("AUTO", None)))
            elif parts_type in {"FOOT_R", "FOOT_L"}:
                self.rotation_islands(island_manager, (("GEOMETRY", "Y"), ("AUTO", None)))
            elif parts_type in {"HAIR_F", "HAIR_B"}:
                self.rotation_islands(island_manager, (("GEOMETRY", "Z"),))
            else:
                self.rotation_islands(island_manager, (("GEOMETRY", "Z"),))

            if parts_type in {"HAND_R", "FOOT_R", "FOOT_L"}:
                for island in island_manager.islands:
                    rotate_island(island, math.pi)

            if parts_type == "BUTTON":
                self.sort_axis(island_manager, "Z", reverse=False)
            elif parts_type == "HAIR_F":
                self.sort_axis(island_manager, "X", reverse=False)
            elif parts_type == "HAIR_B":
                self.sort_axis(island_manager, "X", reverse=True)
            elif parts_type == "HAND_R":
                self.sort_axis(island_manager, "Y", reverse=False)
            elif parts_type == "HAND_L":
                self.sort_axis(island_manager, "Y", reverse=True)
            else:
                self.sort_axis(island_manager, "X", reverse=True)

            self.align_islands(island_manager)

            island_manager.update_uvmeshes(True)

        self.print_time()
        self.report({"INFO"}, "Match as {}".format(parts_type))
        return {"FINISHED"}

    def get_body_reference(self, island_manager, max_co, min_co):
        dimensions = max_co - min_co
        center_x = (min_co.x + max_co.x) / 2
        half_width = max(dimensions.x * 0.5, 1e-6)
        center_margin = min(0.12, max(0.06, 0.08 * (0.8 / max(dimensions.z, 1e-6))))

        return {
            "center_x": center_x,
            "half_width": half_width,
            "center_margin": center_margin,
        }

    def get_humanoid_parts(self, avg_center, max_co, min_co, body_reference=None):
        humanoid_scale = max_co - min_co
        width = max(humanoid_scale.x, 1e-6)
        height = max(humanoid_scale.z, 1e-6)
        rel_z = (avg_center.z - min_co.z) / height
        center_x = body_reference["center_x"] if body_reference else (min_co.x + max_co.x) / 2
        half_width = body_reference["half_width"] if body_reference else max(width * 0.5, 1e-6)
        center_margin = body_reference["center_margin"] if body_reference else 0.08
        relative_center_x = (avg_center.x - center_x) / half_width

        #  Legs Bottom 45%
        if rel_z < 0.45:
            leg_center_margin = center_margin * min(1.0, max(0.0, (rel_z - 0.28) / 0.17))
            if abs(relative_center_x) <= leg_center_margin:
                return "BODY"
            return "FOOT_R" if relative_center_x < 0 else "FOOT_L"
        # Arms
        if relative_center_x < -0.35:
            return "HAND_R"
        elif relative_center_x > 0.35:
            return "HAND_L"
        # body
        if rel_z > 0.80:  # Top 20%
            return "HEAD"
        else:
            return "BODY"

    def find_groups(self, context, island_manager, max_co, min_co, body_reference):
        anchor_positions = {
            "BODY": {"position": Vector((0.5, 0.5)), "direction": Vector((1, 0))},
            "HAND_R": {"position": Vector((0.3, 0.7)), "direction": Vector((-1, 0))},
            "HAND_L": {"position": Vector((0.7, 0.7)), "direction": Vector((1, 0))},
            "FOOT_R": {"position": Vector((0.3, 0.2)), "direction": Vector((-1, 0))},
            "FOOT_L": {"position": Vector((0.7, 0.2)), "direction": Vector((1, 0))},
            "HEAD": {"position": Vector((0.5, 0.9)), "direction": Vector((1, 0))},
        }

        parts_groups = {parts: [] for parts in anchor_positions.keys()}
        for island in island_manager.islands:
            parts_type = self.get_humanoid_parts(island.center_3d, max_co, min_co, body_reference)
            parts_groups[parts_type].append(island)

        for parts_type, islands in parts_groups.items():
            if islands:
                anchor = anchor_positions[parts_type]
                start_position = anchor["position"]
                direction = anchor["direction"]

                islands.sort(key=lambda island: island.width * island.height, reverse=True)

                current_position = start_position.copy()
                for island in islands:
                    offset = current_position - island.center
                    island.move(offset)
                    current_position += direction * (island.width)

    def sort_axis(self, island_manager, axis, reverse=False):
        axis_orders = {
            "X": ["+X", "+Y", "-Z"],
            "Y": ["+Y", "+X", "-Z"],
            "Z": ["-Z", "+X", "+Y"],
        }
        sort_order = axis_orders[axis]

        def sort_func(island):
            return tuple(
                island.center_3d["XYZ".index(axis[-1])] * (-1 if axis.startswith("-") else 1) for axis in sort_order
            )

        island_manager.islands.sort(key=sort_func, reverse=reverse)

    def align_islands(self, island_manager):
        island_bounds = []
        for island in island_manager.islands:
            island_bounds.append((island, island.min_uv, island.max_uv))

        all_min = Vector((min(bounds[1].x for bounds in island_bounds), min(bounds[1].y for bounds in island_bounds)))
        all_max = Vector((max(bounds[2].x for bounds in island_bounds), max(bounds[2].y for bounds in island_bounds)))

        if self.align_uv == "X":
            offset = Vector((all_min[0], all_max[1]))
        else:
            offset = Vector((all_min[0] + island_bounds[0][0].width, all_max[1]))

        for island, min_uv, max_uv in island_bounds:
            if self.align_uv == "X":
                island_offset = Vector((offset.x - min_uv[0], offset.y - max_uv[1]))
                island.move(island_offset)
                offset.x += island.width + 0.01
            else:
                island_offset = Vector((offset.x - max_uv[0], offset.y - max_uv[1]))
                island.move(island_offset)
                offset.y -= island.height + 0.01

    def rotation_islands(self, island_manager, operations):
        for island in island_manager.islands:
            for method, axis in operations:
                angle = self.find_island_rotation_angle(island, method=method, axis=axis)
                rotate_island(island, angle)

    def find_island_rotation_angle(self, island, method="AUTO", axis=None):
        if method == "AUTO":
            return find_rotation_auto(island)
        if method == "GEOMETRY":
            if axis is None:
                axis = "Z"
            return find_rotation_geometry(island, axis)
        raise ValueError("Unsupported rotation method: {}".format(method))

    @staticmethod
    def average_vectors(vectors):
        total = vectors[0].copy()
        for vector in vectors[1:]:
            total += vector
        return total / len(vectors)


    def draw(self, context):
        layout = self.layout
        row = layout.row()
        row.label(text="Align")
        row.prop(self, "align_uv", expand=True)


def register():
    bpy.utils.register_class(MIO3UV_OT_body_preset)


def unregister():
    bpy.utils.unregister_class(MIO3UV_OT_body_preset)
