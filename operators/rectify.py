import bpy
from mathutils import Vector
from bpy.props import BoolProperty, EnumProperty
from ..utils.utils import straight_uv_nodes
from ..classes import Mio3UVOperator, UVIslandManager, UVNodeManager, UVIsland


class MIO3UV_OT_rectify(Mio3UVOperator):
    bl_idname = "uv.mio3_rectify"
    bl_label = "Rectify"
    bl_description = "Unwrap boundary to rectangle using four corners or a range as reference"
    bl_options = {"REGISTER", "UNDO"}

    bbox_type: EnumProperty(
        name="Scale",
        items=[("AVERAGE", "Average", ""), ("BBOX", "Max", "")],
    )
    distribute: EnumProperty(
        name="Align UVs",
        items=[("GEOMETRY", "Geometry", ""), ("EVEN", "Even", ""), ("NONE", "None", "")],
    )
    method: EnumProperty(
        name="Unwrap Method",
        items=[
            ("ANGLE_BASED", "Angle Based", "Angle based unwrapping method"),
            ("CONFORMAL", "Conformal", "Conformal mapping method"),
            ("MINIMUM_STRETCH", "Minimum Stretch", "Minimum stretch mapping method"),
        ],
    )
    unwrap: BoolProperty(name="Unwrap", default=True)
    stretch: BoolProperty(name="Stretch", default=False)
    pin: BoolProperty(name="Pinned", default=True)

    def draw(self, context):
        layout = self.layout
        layout.use_property_split = False
        layout.use_property_decorate = False
        split = layout.split(factor=0.4)
        split.label(text="Scale")
        sub = split.row()
        sub.prop(self, "bbox_type", expand=True)

        split = layout.split(factor=0.4)
        split.label(text="Align UVs")
        split.prop(self, "distribute", text="")
        split = layout.split(factor=0.4)
        split.prop(self, "unwrap")
        sub = split.row()

        sub.prop(self, "method", text="")
        sub.enabled = self.unwrap

        layout.use_property_split = True
        layout.prop(self, "stretch")
        layout.prop(self, "pin")

    def execute(self, context):
        self.start_time()
        objects = self.get_selected_objects(context)

        use_uv_select_sync = context.tool_settings.use_uv_select_sync
        mesh_select_mode = context.tool_settings.mesh_select_mode[:]
        uv_select_mode = context.tool_settings.uv_select_mode

        island_manager = UVIslandManager(objects, sync=use_uv_select_sync)

        if use_uv_select_sync:
            context.tool_settings.mesh_select_mode = (True, False, False)
        else:
            context.tool_settings.uv_select_mode = "VERTEX"

        if not island_manager.islands:
            return {"CANCELLED"}

        valid_islands: list[tuple[UVIsland, dict]] = []
        for island in island_manager.islands:
            uv_layer = island.uv_layer
            island.store_selection()

            selected_uvs = {}
            for face in island.faces:
                for loop in face.loops:
                    if loop.uv_select_vert:
                        uv = loop[uv_layer].uv
                        uvkey = (round(uv.x, 6), round(uv.y, 6))
                        selected_uvs.setdefault(uvkey, []).append(loop)

            if len(selected_uvs) >= 4:
                valid_islands.append((island, selected_uvs))

            island.uv_select_set_all(False)

        for island, selected_uvs in valid_islands:
            island.restore_selection()
            uv_layer = island.uv_layer

            bbox_vectors = [Vector(uvkey) for uvkey in selected_uvs.keys()]
            bbox_uvs = self.get_bbox_uvs(bbox_vectors)

            # コーナーUVを検出
            corners = []
            for bbox_point in bbox_uvs:
                corner_candidates = []
                for uvkey, loops in selected_uvs.items():
                    diff_x = abs(uvkey[0] - bbox_point[0])
                    diff_y = abs(uvkey[1] - bbox_point[1])
                    total_diff = diff_x + diff_y
                    corner_candidates.append((uvkey, loops, total_diff))
                if corner_candidates:
                    closest_uv, loops, _ = min(corner_candidates, key=lambda x: x[2])
                    corners.append((loops, closest_uv))

            for (loops, _), bbox_uv in zip(corners, bbox_uvs):
                for loop in loops:
                    loop[uv_layer].uv = bbox_uv
                    if self.pin:
                        loop[uv_layer].pin_uv = True

            island.uv_select_set_all(False)

            boundary_loops = set()
            for (curr_loops, _), (next_loops, _) in zip(corners, corners[1:] + [corners[0]]):
                self.select_uv(curr_loops, True)
                self.select_uv(next_loops, True)

                try:
                    bpy.ops.uv.shortest_path_select()
                except:
                    pass

                node_manager = UVNodeManager.from_island(island, sync=use_uv_select_sync, sub_faces=island.faces)
                if len(node_manager.groups):
                    group = node_manager.groups[0]
                    straight_uv_nodes(group, self.distribute)
                    for node in group.nodes:
                        for loop in node.loops:
                            loop.uv_select_vert = False
                            loop[uv_layer].pin_uv = True
                            boundary_loops.add(loop)
                    group.update_uvs()
                else:
                    self.select_uv(curr_loops, False)
                    self.select_uv(next_loops, False)

            if self.bbox_type == "AVERAGE":
                bboox_ave = self.get_bbox_average([Vector(uvkey) for _, uvkey in corners])
                self.remap_bbox(uv_layer, bbox_uvs, bboox_ave, boundary_loops)

            # end valid_islands:

        if self.unwrap:
            for island, _ in valid_islands:
                island.uv_select_set_all(True)
                for face in island.faces:
                    face.select = True
            bpy.ops.uv.unwrap(method=self.method, margin=0.001)

        if self.stretch and self.unwrap:
            for island, _ in valid_islands:
                island.restore_selection()
            bpy.ops.uv.minimize_stretch(fill_holes=False, iterations=50)

        if not self.pin:
            for island, _ in valid_islands:
                uv_layer = island.uv_layer
                for face in island.faces:
                    for loop in face.loops:
                        loop[uv_layer].pin_uv = False

        for island, _ in valid_islands:
            island.restore_selection()

        island_manager.update_uvmeshes(True)

        if use_uv_select_sync:
            context.tool_settings.mesh_select_mode = mesh_select_mode
        else:
            context.tool_settings.uv_select_mode = uv_select_mode

        self.print_time()
        return {"FINISHED"}

    @staticmethod
    def select_uv(loops, select):
        for loop in loops:
            loop.uv_select_vert = select

    @staticmethod
    def get_bbox_uvs(uvs: list[Vector]) -> list[Vector]:
        x_coords = [uv.x for uv in uvs]
        y_coords = [uv.y for uv in uvs]
        min_uv = Vector((min(x_coords), min(y_coords)))
        max_uv = Vector((max(x_coords), max(y_coords)))
        bbox_uv = [
            Vector((min_uv.x, max_uv.y)),
            Vector((max_uv.x, max_uv.y)),
            Vector((max_uv.x, min_uv.y)),
            Vector((min_uv.x, min_uv.y)),
        ]
        return bbox_uv

    @staticmethod
    def get_bbox_average(uvs: list[Vector]) -> list[Vector]:
        center_x = sum(uv.x for uv in uvs) / len(uvs)
        center_y = sum(uv.y for uv in uvs) / len(uvs)
        avg_distance_x = sum(abs(uv.x - center_x) for uv in uvs) / len(uvs)
        avg_distance_y = sum(abs(uv.y - center_y) for uv in uvs) / len(uvs)
        j_min_u = center_x - avg_distance_x
        j_max_u = center_x + avg_distance_x
        j_min_v = center_y - avg_distance_y
        j_max_v = center_y + avg_distance_y
        average = [
            Vector((j_min_u, j_max_v)),
            Vector((j_max_u, j_max_v)),
            Vector((j_max_u, j_min_v)),
            Vector((j_min_u, j_min_v)),
        ]
        return average

    @staticmethod
    def remap_bbox(uv_layer, bbox_uvs: list[Vector], bbox_ajs: list[Vector], loops):
        old_width = bbox_uvs[1].x - bbox_uvs[0].x
        old_height = bbox_uvs[0].y - bbox_uvs[3].y
        new_width = bbox_ajs[1].x - bbox_ajs[0].x
        new_height = bbox_ajs[0].y - bbox_ajs[3].y
        if old_width == 0 or old_height == 0:
            return

        scale_x = new_width / old_width
        scale_y = new_height / old_height

        old_origin = bbox_uvs[0]
        new_origin = bbox_ajs[0]

        for loop in loops:
            uv = loop[uv_layer].uv
            scaled_uv = Vector(
                ((uv.x - old_origin.x) * scale_x + new_origin.x, (uv.y - old_origin.y) * scale_y + new_origin.y)
            )
            loop[uv_layer].uv = scaled_uv


def register():
    bpy.utils.register_class(MIO3UV_OT_rectify)


def unregister():
    bpy.utils.unregister_class(MIO3UV_OT_rectify)
