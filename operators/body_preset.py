import bpy
import numpy as np
from bpy.props import EnumProperty
from mathutils import Vector
from ..classes.uv import UVIslandManager
from ..classes.operator import Mio3UVOperator


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
        self.objects = self.get_selected_objects(context)
        use_uv_select_sync = context.tool_settings.use_uv_select_sync
        if use_uv_select_sync:
            self.sync_uv_from_mesh(context, self.objects)
        # original_pivot = context.space_data.pivot_point

        island_manager = UVIslandManager(self.objects)
        if not island_manager.islands:
            return {"CANCELLED"}

        all_centers = np.array([island.center_3d for island in island_manager.islands])
        avg_center = Vector(np.mean(all_centers, axis=0))

        bound_box = [Vector(point) @ context.active_object.matrix_world for point in context.active_object.bound_box]
        min_co = Vector(np.min(bound_box, axis=0))
        max_co = Vector(np.max(bound_box, axis=0))

        if self.type == "AUTO":
            parts_type = self.get_humanoid_parts(avg_center, max_co, min_co)
            if parts_type == "HEAD":
                parts_type = "HAIR_F"
        else:
            parts_type = self.type

        if parts_type == "BODY":
            self.find_groups(context, island_manager, max_co, min_co)
            island_manager.update_uvmeshes()
        else:
            if parts_type in {"HAND_R", "HAND_L"}:
                bpy.ops.uv.align_rotation(method="GEOMETRY", axis="X")
                bpy.ops.uv.align_rotation(method="AUTO")
            elif parts_type in {"FOOT_R", "FOOT_L"}:
                bpy.ops.uv.align_rotation(method="GEOMETRY", axis="Y")
                bpy.ops.uv.align_rotation(method="AUTO")
            elif parts_type in {"HAIR_F", "HAIR_B"}:
                bpy.ops.uv.align_rotation(method="GEOMETRY", axis="Z")
            else:
                bpy.ops.uv.align_rotation(method="GEOMETRY", axis="Z")

            if parts_type in {"HAND_R", "FOOT_R", "FOOT_L"}:
                self.rotate_islands(island_manager)

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

            island_manager.update_uvmeshes()

        self.print_time()
        self.report({"INFO"}, "Match as {}".format(parts_type))
        return {"FINISHED"}

    def get_humanoid_parts(self, avg_center, max_co, min_co):
        dimensions = max_co - min_co
        rel_x = (avg_center.x - min_co.x) / dimensions.x
        rel_z = (avg_center.z - min_co.z) / dimensions.z
        center_x = (min_co.x + max_co.x) / 2
        x = avg_center.x
        #  Legs Bottom 45%
        if rel_z < 0.45 and x < center_x:
            return "FOOT_R"
        if rel_z < 0.45 and x > center_x:
            return "FOOT_L"
        # Arms
        if rel_x < 0.35:  # L 35%
            return "HAND_R"
        elif rel_x > 0.65:  # R 35%
            return "HAND_L"
        # body
        if rel_z > 0.80:  # Top 20%
            return "HEAD"
        else:
            return "BODY"

    def find_groups(self, context, island_manager, max_co, min_co):
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
            parts_type = self.get_humanoid_parts(island.center_3d, max_co, min_co)
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

        all_min = np.min([bounds[1] for bounds in island_bounds], axis=0)
        all_max = np.max([bounds[2] for bounds in island_bounds], axis=0)

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

    def rotate_islands(self, island_manager):
        for island in island_manager.islands:
            uv_layer = island.uv_layer
            pivot = Vector(((island.min_uv.x + island.max_uv.x) / 2, (island.min_uv.y + island.max_uv.y) / 2))
            for face in island.faces:
                for loop in face.loops:
                    uv = loop[uv_layer].uv
                    dx = uv.x - pivot.x
                    dy = uv.y - pivot.y
                    uv.x = pivot.x - dx
                    uv.y = pivot.y - dy

            island.update_bounds()

    def draw(self, context):
        layout = self.layout
        row = layout.row()
        row.label(text="Align")
        row.prop(self, "align_uv", expand=True)


classes = [MIO3UV_OT_body_preset]


def register():
    for c in classes:
        bpy.utils.register_class(c)


def unregister():
    for c in classes:
        bpy.utils.unregister_class(c)
