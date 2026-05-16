import bpy
import math
from mathutils import Vector
from dataclasses import dataclass
from bpy.props import EnumProperty, FloatProperty
from bpy.app.translations import pgettext_iface as tt_iface
from ..classes import Mio3UVOperator, UVIslandManager, UVIsland
from ..utils.uv_manager_utils import find_rotation_auto, find_rotation_geometry, rotate_island


@dataclass(frozen=True)
class BodyReference:
    min_xyz: Vector
    max_xyz: Vector
    width: float
    height: float
    center_x: float
    half_width: float
    center_margin: float

    @classmethod
    def from_object(cls, obj):
        bp = [Vector(point) @ obj.matrix_world for point in obj.bound_box]
        min_xyz = Vector((min(point.x for point in bp), min(point.y for point in bp), min(point.z for point in bp)))
        max_xyz = Vector((max(point.x for point in bp), max(point.y for point in bp), max(point.z for point in bp)))
        dimensions = max_xyz - min_xyz
        width = max(dimensions.x, 1e-6)
        height = max(dimensions.z, 1e-6)
        return cls(
            min_xyz=min_xyz,
            max_xyz=max_xyz,
            width=width,
            height=height,
            center_x=(min_xyz.x + max_xyz.x) / 2,
            half_width=max(dimensions.x * 0.5, 1e-6),
            center_margin=min(0.12, max(0.06, 0.08 * (0.8 / height))),
        )


@dataclass
class PartGroup:
    position: Vector
    direction: Vector
    rotation_operations: tuple = (("GEOMETRY", "Z"),)
    flip: bool = False
    sort_axis: str = "X"
    sort_reverse: bool = True


class UV_OT_mio3_body_preset(Mio3UVOperator):
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
            ("BODY", "Body", ""),
            ("HAIR_F", "Front Hair", ""),
            ("HAIR_B", "Back Hair", ""),
            ("HAND_R", "Hand R", ""),
            ("HAND_L", "Hand L", ""),
            ("FOOT_R", "Foot R", ""),
            ("FOOT_L", "Foot L", ""),
            ("BUTTON", "Button", ""),
        ],
    )

    @classmethod
    def description(cls, context, properties):
        dicts = {
            "AUTO": "Automatically detects body parts and classifies or arranges them",
            "BUTTON": "Align the vertically positioned parts",
        }
        return tt_iface(dicts.get(properties.type, "Align the body parts in the appropriate order and orientation"))

    align_uv: EnumProperty(name="Align", default="X", items=[("X", "Align H", ""), ("Y", "Align V", "")])
    spacing: FloatProperty(name="Spacing", default=0.001, min=0.0, max=1.0, precision=3, step=0.1)

    PARTS_GROUP = {
        "BODY": PartGroup(position=Vector((0.5, 0.5)), direction=Vector((1, 0))),
        "HEAD": PartGroup(
            position=Vector((0.5, 0.9)),
            direction=Vector((1, 0)),
            rotation_operations=(("GEOMETRY", "Z"),),
            sort_axis="X",
            sort_reverse=False,
        ),
        "HAIR_F": PartGroup(
            position=Vector((0.5, 0.9)),
            direction=Vector((1, 0)),
            rotation_operations=(("GEOMETRY", "Z"),),
            sort_axis="X",
            sort_reverse=False,
        ),
        "HAIR_B": PartGroup(
            position=Vector((0.5, 0.9)),
            direction=Vector((1, 0)),
            rotation_operations=(("GEOMETRY", "Z"),),
            sort_axis="X",
            sort_reverse=True,
        ),
        "HAND_L": PartGroup(
            position=Vector((0.8, 0.7)),
            direction=Vector((1, 0)),
            rotation_operations=(("GEOMETRY", "X"), ("AUTO", None)),
            sort_axis="Y",
            sort_reverse=True,
        ),
        "HAND_R": PartGroup(
            position=Vector((0.2, 0.7)),
            direction=Vector((-1, 0)),
            rotation_operations=(("GEOMETRY", "X"), ("AUTO", None)),
            flip=True,
            sort_axis="Y",
            sort_reverse=False,
        ),
        "FOOT_L": PartGroup(
            position=Vector((0.7, 0.2)),
            direction=Vector((1, 0)),
            rotation_operations=(("GEOMETRY", "Y"), ("AUTO", None)),
            flip=True,
        ),
        "FOOT_R": PartGroup(
            position=Vector((0.3, 0.2)),
            direction=Vector((-1, 0)),
            rotation_operations=(("GEOMETRY", "Y"), ("AUTO", None)),
            flip=True,
        ),
        "BUTTON": PartGroup(
            position=Vector((0.5, 0.5)),
            direction=Vector((1, 0)),
            rotation_operations=(("GEOMETRY", "Z"),),
            sort_axis="Z",
            sort_reverse=False,
        ),
    }

    def execute(self, context):
        self.start_time()
        objects = self.get_selected_objects(context)
        use_uv_select_sync = context.tool_settings.use_uv_select_sync

        body_reference = BodyReference.from_object(context.active_object)
        island_manager = UVIslandManager(objects, sync=use_uv_select_sync)
        if not island_manager.islands:
            return {"CANCELLED"}

        avg_center_3d = self.average_vectors(island_manager)

        if self.type == "AUTO":
            parts_type = self.find_humanoid_part(avg_center_3d, body_reference)
        else:
            parts_type = self.type

        if parts_type == "BODY":
            self.auto_body_mapping(island_manager, body_reference)
        else:
            part_info = self.PARTS_GROUP[parts_type]
            self.sort_axis(island_manager, part_info.sort_axis, reverse=part_info.sort_reverse)
            self.rotation_islands(island_manager.islands, part_info)
            self.align_islands(island_manager.islands)

        island_manager.update_uvmeshes(True)
        self.end_time()
        self.report({"INFO"}, "Match as {}".format(parts_type))
        return {"FINISHED"}

    def find_humanoid_part(self, avg_center: Vector, body_reference: BodyReference) -> str:
        rel_z = (avg_center.z - body_reference.min_xyz.z) / body_reference.height
        relative_center_x = (avg_center.x - body_reference.center_x) / body_reference.half_width

        #  Legs Bottom 45%
        if rel_z < 0.45:
            leg_center_margin = body_reference.center_margin * min(1.0, max(0.0, (rel_z - 0.28) / 0.17))
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

    def auto_body_mapping(self, island_manager: UVIslandManager, body_reference: BodyReference):
        part_infos = {parts: [] for parts in self.PARTS_GROUP.keys()}
        for island in island_manager.islands:
            parts_type = self.find_humanoid_part(island.center_3d, body_reference)
            part_infos[parts_type].append(island)

        for parts_type, islands in part_infos.items():
            if islands:
                part_info = self.PARTS_GROUP[parts_type]
                start_position = part_info.position.copy()
                direction = part_info.direction

                islands.sort(key=lambda island: len(island.faces), reverse=True)

                current_position = start_position.copy()
                for island in islands:
                    offset = current_position - island.center
                    island.move(offset, True)
                    current_position += direction * (island.width)

    def sort_axis(self, island_manager: UVIslandManager, axis: str, reverse: bool = False):
        axis_orders = {
            "X": ["+X", "+Y", "-Z"],
            "Y": ["+Y", "+X", "-Z"],
            "Z": ["-Z", "+X", "+Y"],
        }
        sort_order = axis_orders[axis]

        def sort_func(island: UVIsland):
            return tuple(
                island.center_3d["XYZ".index(axis[-1])] * (-1 if axis.startswith("-") else 1) for axis in sort_order
            )

        island_manager.islands.sort(key=sort_func, reverse=reverse)

    def align_islands(self, islands: list[UVIsland]):
        min_x = min(island.min_uv.x for island in islands)
        max_x = max(island.max_uv.x for island in islands)
        max_y = max(island.max_uv.y for island in islands)

        if self.align_uv == "X":
            offset = Vector((min_x, max_y))
        else:
            offset = Vector(((min_x + max_x) * 0.5, max_y))

        for island in islands:
            if self.align_uv == "X":
                island_offset = Vector((offset.x - island.min_uv.x, offset.y - island.max_uv.y))
                island.move(island_offset, True)
                offset.x += island.width + self.spacing
            else:
                island_offset = Vector((offset.x - island.center.x, offset.y - island.max_uv.y))
                island.move(island_offset, True)
                offset.y -= island.height + self.spacing

    def rotation_islands(self, islands: list[UVIsland], part_group: PartGroup):
        for island in islands:
            world_matrix = island.obj.matrix_world
            for method, axis in part_group.rotation_operations:
                if method == "AUTO":
                    angle = find_rotation_auto(island.uv_layer, island.faces)
                if method == "GEOMETRY":
                    if axis is None:
                        axis = "Z"
                    angle = find_rotation_geometry(island.uv_layer, island.faces, axis, "WORLD", world_matrix)
                rotate_island(island, angle)

            if part_group.flip:
                rotate_island(island, math.pi)

            island.update_bounds()

    @staticmethod
    def average_vectors(island_manager: UVIslandManager) -> Vector:
        all_center_3d = [island.center_3d for island in island_manager.islands]
        total = all_center_3d[0].copy()
        for vector in all_center_3d[1:]:
            total += vector
        return total / len(all_center_3d)

    def draw(self, context):
        layout = self.layout
        layout.use_property_split = True
        layout.use_property_decorate = False
        layout.row().prop(self, "align_uv", expand=True)
        layout.prop(self, "spacing")


def register():
    bpy.utils.register_class(UV_OT_mio3_body_preset)


def unregister():
    bpy.utils.unregister_class(UV_OT_mio3_body_preset)
