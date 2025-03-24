import bpy
from mathutils import Vector
from bpy.props import BoolProperty, EnumProperty
from ..utils import straight_uv_nodes
from ..classes.uv import UVIslandManager, UVNodeManager
from ..classes.operator import Mio3UVOperator


class MIO3UV_OT_rectify(Mio3UVOperator):
    bl_idname = "uv.mio3_rectify"
    bl_label = "Rectify"
    bl_description = "Unwrap boundary to rectangle using four corners or a range as reference"
    bl_options = {"REGISTER", "UNDO"}

    def unwrap_method_items(self, context):
        items = [
            ("ANGLE_BASED", "Angle Based", "Angle based unwrapping method"),
            ("CONFORMAL", "Conformal", "Conformal mapping method"),
        ]
        if bpy.app.version >= (4, 3, 0):
            items.append(("MINIMUM_STRETCH", "Minimum Stretch", "Minimum stretch mapping method"))
        return items

    bbox_type: EnumProperty(
        name="Scale",
        items=[("AVERAGE", "Average", ""), ("BBOX", "Max", "")],
    )
    distribute: EnumProperty(
        name="Align UVs",
        items=[("GEOMETRY", "Geometry", ""), ("EVEN", "Even", ""), ("NONE", "None", "")],
    )
    pin: BoolProperty(name="Pinned", default=True)
    unwrap: BoolProperty(name="Unwrap", default=True)
    method: EnumProperty(name="Unwrap Method", items=unwrap_method_items)
    stretch: BoolProperty(name="Stretch", default=False)

    def draw(self, context):
        layout = self.layout

        split = layout.split(factor=0.4)
        split.label(text="Scale")
        sub = split.row()
        sub.prop(self, "bbox_type", expand=True)

        split = layout.split(factor=0.4)
        split.label(text="Align UVs")
        split.prop(self, "distribute", text="")

        split = layout.split(factor=0.4)
        split.use_property_split = False
        split.prop(self, "unwrap")
        sub = split.row()

        sub.prop(self, "method", text="")
        sub.enabled = self.unwrap

        layout.use_property_split = True
        layout.use_property_decorate = False
        layout.prop(self, "stretch", expand=True)
        layout.prop(self, "pin")

    def execute(self, context):
        self.start_time()
        self.objects = self.get_selected_objects(context)
        use_uv_select_sync = context.tool_settings.use_uv_select_sync

        if context.tool_settings.uv_select_mode not in ["VERTEX", "ISLAND"]:
            context.tool_settings.uv_select_mode = "VERTEX"

        if use_uv_select_sync:
            self.sync_uv_from_mesh(context, self.objects)
            context.tool_settings.use_uv_select_sync = False
            context.scene.mio3uv.auto_uv_sync_skip = True
            island_manager = UVIslandManager(self.objects, mesh_link_uv=True)
        else:
            island_manager = UVIslandManager(self.objects)

        for island in island_manager.islands:
            island.store_selection()
            island.deselect_all_uv()
            if island.selection_uv_count < 3:
                island_manager.remove_island(island)

        for island in island_manager.islands:
            island.restore_selection()
            bm = island.bm
            uv_layer = island.uv_layer

            selected_uvs = {}
            for face in island.faces:
                for loop in face.loops:
                    if loop[uv_layer].select:
                        uv = loop[uv_layer].uv
                        key = (round(uv.x, 6), round(uv.y, 6))
                        if key not in selected_uvs:
                            selected_uvs[key] = []
                        selected_uvs[key].append(loop)

            bbox_vectors = [Vector(uv) for uv in selected_uvs.keys()]
            min_u = min(v.x for v in bbox_vectors)
            max_u = max(v.x for v in bbox_vectors)
            min_v = min(v.y for v in bbox_vectors)
            max_v = max(v.y for v in bbox_vectors)
            bbox_uv = [  # 時計回り
                Vector((min_u, max_v)),
                Vector((max_u, max_v)),
                Vector((max_u, min_v)),
                Vector((min_u, min_v)),
            ]

            # 範囲選択 コーナーUVを検出
            if len(selected_uvs) > 4:
                target_uvs = {}
                for bbox_point in bbox_uv:
                    corner_candidates = []
                    for uv, loops in selected_uvs.items():
                        diff_x = abs(uv[0] - bbox_point[0])
                        diff_y = abs(uv[1] - bbox_point[1])
                        total_diff = diff_x + diff_y
                        corner_candidates.append((uv, loops, total_diff))
                    if corner_candidates:
                        closest_uv, loops, _ = min(corner_candidates, key=lambda x: x[2])
                        target_uvs[closest_uv] = loops
            else:  # 頂点指定
                target_uvs = selected_uvs

            # 調整したサイズ
            if self.bbox_type == "AVERAGE":
                abbox_vectors = [Vector(uv) for uv in target_uvs.keys()]
                adjustbox = self.get_adjustbox(abbox_vectors)
            else:
                adjustbox = bbox_uv

            corner_mapping = []
            for old_uv, loops in target_uvs.items():
                old_vector = Vector(old_uv)
                new_uv_bbox = min(bbox_uv, key=lambda c: (c - old_vector).length)
                new_uv_adjust = adjustbox[bbox_uv.index(new_uv_bbox)]
                corner_mapping.append((old_vector, new_uv_bbox, new_uv_adjust, loops))
                for loop in loops:
                    loop[uv_layer].uv = new_uv_bbox
                    if self.pin:
                        loop[uv_layer].pin_uv = True

            island.deselect_all_uv()

            num_uvs = len(bbox_uv)
            all_loops = set()
            for i in range(num_uvs):
                uv1 = bbox_uv[i]
                uv2 = bbox_uv[(i + 1) % len(bbox_uv)]
                for _, new_uv_bbox, _, loops in corner_mapping:
                    if new_uv_bbox.to_tuple() in (uv1.to_tuple(), uv2.to_tuple()):
                        for loop in loops:
                            loop[uv_layer].select = True

                try:
                    bpy.ops.uv.shortest_path_select()
                except:
                    pass

                faces = {face for face in island.faces if face.select}
                node_manager = UVNodeManager.from_object(island.obj, bm, uv_layer, mode="FACE", selected=faces)
                if len(node_manager.groups):
                    group = node_manager.groups[0]
                    for node in group.nodes:
                        for loop in node.loops:
                            loop[uv_layer].pin_uv = True
                            all_loops.add(loop)

                    straight_uv_nodes(group, self.distribute)
                    for node in group.nodes:
                        node.update_uv(group.uv_layer)
                        for loop in node.loops:
                            loop[uv_layer].select = False

            self.adjust_aspect_ratio(island, bbox_uv, adjustbox, all_loops)

            # 隣接しているUVがshortest_path_selectで選択解除されるため
            for _, _, _, loops in corner_mapping:
                for loop in loops:
                    loop[uv_layer].pin_uv = True

            # end island_manager.islands:

        if self.unwrap:
            for island in island_manager.islands:
                island.select_all_uv()
            bpy.ops.uv.unwrap(method=self.method, margin=0.001)

        if self.stretch and self.unwrap:
            for island in island_manager.islands:
                island.restore_selection()
            # bpy.ops.uv.select_less()
            bpy.ops.uv.minimize_stretch(fill_holes=False, iterations=50)

        if not self.pin:
            for island in island_manager.islands:
                island.select_all_uv()
            bpy.ops.uv.pin(clear=True)

        for island in island_manager.islands:
            island.restore_selection()

        if use_uv_select_sync:
            island_manager.restore_vertex_selection()
            context.tool_settings.use_uv_select_sync = True

        island_manager.update_uvmeshes()

        self.print_time()
        return {"FINISHED"}

    def get_adjustbox(self, bbox_vectors):
        center_u = sum(v.x for v in bbox_vectors) / len(bbox_vectors)
        center_v = sum(v.y for v in bbox_vectors) / len(bbox_vectors)

        avg_distance_u = sum(abs(v.x - center_u) for v in bbox_vectors) / len(bbox_vectors)
        avg_distance_v = sum(abs(v.y - center_v) for v in bbox_vectors) / len(bbox_vectors)

        j_min_u = center_u - avg_distance_u
        j_max_u = center_u + avg_distance_u
        j_min_v = center_v - avg_distance_v
        j_max_v = center_v + avg_distance_v

        adjustbox = [
            Vector((j_min_u, j_max_v)),
            Vector((j_max_u, j_max_v)),
            Vector((j_max_u, j_min_v)),
            Vector((j_min_u, j_min_v)),
        ]
        return adjustbox

    def adjust_aspect_ratio(self, island, bbox_uv, adjustbox, all_loops):
        uv_layer = island.uv_layer

        bbox_width = bbox_uv[1].x - bbox_uv[0].x
        bbox_height = bbox_uv[0].y - bbox_uv[3].y
        adjust_width = adjustbox[1].x - adjustbox[0].x
        adjust_height = adjustbox[0].y - adjustbox[3].y

        if bbox_width == 0 or bbox_height == 0:
            return

        scale_x = adjust_width / bbox_width
        scale_y = adjust_height / bbox_height

        bbox_center = (bbox_uv[0] + bbox_uv[2]) / 2
        adjust_center = (adjustbox[0] + adjustbox[2]) / 2
        translation = adjust_center - bbox_center

        for loop in all_loops:
            uv = loop[uv_layer].uv
            scaled_uv = Vector(
                ((uv.x - bbox_center.x) * scale_x + bbox_center.x, (uv.y - bbox_center.y) * scale_y + bbox_center.y)
            )
            loop[uv_layer].uv = scaled_uv + translation


classes = [
    MIO3UV_OT_rectify,
]


def register():
    for c in classes:
        bpy.utils.register_class(c)


def unregister():
    for c in classes:
        bpy.utils.unregister_class(c)
