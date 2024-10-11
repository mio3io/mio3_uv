import bpy
import time
import math
import numpy as np
from bpy.props import EnumProperty
from bpy.app.translations import pgettext_iface as tt_iface
from mathutils import Vector
from ..classes.uv import UVIslandManager
from ..classes.operator import Mio3UVOperator

class MIO3UV_OT_body_preset(Mio3UVOperator):
    bl_idname = "uv.mio3_body_preset"
    bl_label = "Align Body Parts"
    bl_description = "Select hair strands or fingers to auto-align rotation and order.\nClassify by parts if whole body is selected"
    bl_options = {"REGISTER", "UNDO"}

    type: EnumProperty(
        name="Axis",
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
        default="AUTO",
    )

    align_uv: EnumProperty(name="Align", items=[("X", "Align V", ""), ("Y", "Align H", "")], default="X")

    def execute(self, context):
        self.start_time = time.time()
        self.objects = self.get_selected_objects(context)
        use_uv_select_sync = context.tool_settings.use_uv_select_sync
        if use_uv_select_sync:
            self.sync_uv_from_mesh(context, self.objects)
        original_pivot = context.space_data.pivot_point

        island_manager = UVIslandManager(self.objects)
        if not island_manager.islands:
            return {"CANCELLED"}
        
        all_centers = np.array([island.center_3d for island in island_manager.islands])
        avg_center = Vector(np.mean(all_centers, axis=0))

        bound_box = [Vector(point) @ context.active_object.matrix_world for point in context.active_object.bound_box]
        min_co = Vector(np.min(bound_box, axis=0))
        max_co = Vector(np.max(bound_box, axis=0))

        if self.type == "AUTO":
            parts_type = self.find_humanoid_parts(avg_center, max_co, min_co)
            if parts_type == "HEAD":
                self.type = "HAIR_F"
            else:
                self.type = parts_type

        if self.type == "BODY":
            self.find_groups(context, island_manager, max_co, min_co)
            island_manager.update_uvmeshes()
        else:
            island_manager.update_uvmeshes()
            self.sort_parts(context)


        context.space_data.pivot_point = original_pivot
        self.print_time(time.time() - self.start_time)
        self.report({"INFO"}, "Match as {}".format(self.type))
        return {"FINISHED"}

    def find_humanoid_parts(self, avg_center, max_co, min_co):
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
            parts_type = self.find_humanoid_parts(island.center_3d, max_co, min_co)
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

    def sort_parts(self, context):
        if self.type in {"HAND_R", "HAND_L"}:
            bpy.ops.uv.align_rotation(method="GEOMETRY", axis="X")
            bpy.ops.uv.align_rotation(method="AUTO")
        elif self.type in {"FOOT_R", "FOOT_L"}:
            bpy.ops.uv.align_rotation(method="GEOMETRY", axis="Y")
            bpy.ops.uv.align_rotation(method="AUTO")
        elif self.type in {"HAIR_F", "HAIR_B"}:
            bpy.ops.uv.align_rotation(method="GEOMETRY", axis="Z")
        else:
            bpy.ops.uv.align_rotation(method="GEOMETRY", axis="Z")

        if self.type in {"HAND_R", "FOOT_R", "FOOT_L"}:
            context.space_data.pivot_point = "INDIVIDUAL_ORIGINS"
            bpy.ops.transform.rotate(value=math.pi, orient_matrix=((1, 0, 0), (0, 1, 0), (0, 0, 1)))

        if self.type == "BUTTON":
            bpy.ops.uv.mio3_sort(axis="Z", align_uv=self.align_uv, reverse=False)
        elif self.type == "HAND_R":
            bpy.ops.uv.mio3_sort(axis="Y", align_uv=self.align_uv, reverse=False)
        elif self.type == "HAND_L":
            bpy.ops.uv.mio3_sort(axis="Y", align_uv=self.align_uv, reverse=True)
        elif self.type == "HAIR_F":
            bpy.ops.uv.mio3_sort(axis="X", align_uv=self.align_uv, reverse=False)
        elif self.type == "HAIR_B":
            bpy.ops.uv.mio3_sort(axis="X", align_uv=self.align_uv, reverse=True)
        else:
            bpy.ops.uv.mio3_sort(axis="X", align_uv=self.align_uv, reverse=False)

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
