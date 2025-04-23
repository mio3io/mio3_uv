import bpy
import bmesh
import math
from mathutils import Vector
from bpy.props import BoolProperty, EnumProperty, FloatProperty
from ..classes.uv import UVIslandManager, UVNodeManager
from ..classes.operator import Mio3UVOperator


class MIO3UV_OT_align(Mio3UVOperator):
    bl_idname = "uv.mio3_align"
    bl_label = "Align UVs"
    bl_description = "Align UVs of vertices, edge loops and islands"
    bl_options = {"REGISTER", "UNDO"}

    type: EnumProperty(
        items=[
            ("MAX_Y", "Top", ""),
            ("MIN_Y", "Bottom", ""),
            ("MIN_X", "Left", ""),
            ("MAX_X", "Right", ""),
            ("ALIGN_S", "Straighten", ""),
            ("ALIGN_X", "Center Y", ""),
            ("ALIGN_Y", "Center X", ""),
            ("CENTER", "Center", ""),
        ],
        name="Align Axis",
        default="MAX_Y",
        options={"HIDDEN"},
    )
    edge_mode: BoolProperty(name="Edge Mode", description="Process each edge loops", default=False)
    island: BoolProperty(name="Island Mode", default=False)

    def invoke(self, context, event):
        self.objects = self.get_selected_objects(context)
        if not self.objects:
            self.report({"WARNING"}, "Object is not selected")
            return {"CANCELLED"}

        use_uv_select_sync = context.tool_settings.use_uv_select_sync
        if use_uv_select_sync:
            self.sync_uv_from_mesh(context, self.objects)

        selected_face = self.check_selected_face_objects(self.objects)
        self.island = True if context.scene.mio3uv.island_mode else selected_face

        if context.scene.mio3uv.edge_mode:
            self.edge_mode = True
        elif context.tool_settings.use_uv_select_sync:
            self.edge_mode = context.tool_settings.mesh_select_mode[1] == True and not self.island
        else:
            self.edge_mode = context.tool_settings.uv_select_mode == "EDGE" and not self.island
        return self.execute(context)

    def check(self, context):
        self.objects = self.get_selected_objects(context)
        if context.tool_settings.use_uv_select_sync:
            self.sync_uv_from_mesh(context, self.objects)
        return True

    def execute(self, context):
        self.start_time()

        if self.type == "ALIGN_S":
            try:
                bpy.ops.uv.align(axis="ALIGN_S")
            except:
                return {"CANCELLED"}
            return {"FINISHED"}

        self.objects = self.get_selected_objects(context)
        use_uv_select_sync = context.tool_settings.use_uv_select_sync

        if self.island and not self.edge_mode:
            if use_uv_select_sync:
                island_manager = UVIslandManager(self.objects, mesh_keep=True, mesh_link_uv=True)
            else:
                island_manager = UVIslandManager(self.objects)
            if not island_manager.islands:
                return {"CANCELLED"}
            self.align_islands(island_manager, self.type)
            island_manager.update_uvmeshes()
        else:
            if use_uv_select_sync:
                node_manager = UVNodeManager(self.objects, mode="VERT")
            else:
                node_manager = UVNodeManager(self.objects, mode="EDGE" if self.edge_mode else "FACE")
            if not node_manager.groups:
                return {"CANCELLED"}
            self.align_uv_nodes(node_manager, self.type)
            node_manager.update_uvmeshes()

        self.print_time()
        return {"FINISHED"}

    def align_group(self, group, alignment_type):
        self.align_nodes(group.nodes, alignment_type)

    def align_uv_nodes(self, node_manager, alignment_type):
        if self.edge_mode and self.island:
            self.align_groups(node_manager.groups, alignment_type)
        elif self.edge_mode:
            for group in node_manager.groups:
                self.align_group(group, alignment_type)
        else:
            all_nodes = []
            for group in node_manager.groups:
                all_nodes.extend(group.nodes)
            self.align_nodes(all_nodes, alignment_type)

        for group in node_manager.groups:
            group.update_uvs()

        for group in node_manager.groups:
            for node in group.nodes:
                node.select = True

    def align_groups(self, groups, alignment_type):
        def align(groups, key, get_pos):
            target = get_pos(groups)
            for group in groups:
                offset = target - get_pos([group])
                for node in group.nodes:
                    node.uv[key] += offset

        if alignment_type == "MAX_X":
            align(groups, 0, lambda g: max(max(node.uv.x for node in group.nodes) for group in g))
        elif alignment_type == "MIN_X":
            align(groups, 0, lambda g: min(min(node.uv.x for node in group.nodes) for group in g))
        elif alignment_type == "MAX_Y":
            align(groups, 1, lambda g: max(max(node.uv.y for node in group.nodes) for group in g))
        elif alignment_type == "MIN_Y":
            align(groups, 1, lambda g: min(min(node.uv.y for node in group.nodes) for group in g))
        elif alignment_type in ["ALIGN_X", "ALIGN_Y", "CENTER"]:
            key = 0 if alignment_type.endswith("X") else 1
            overall_min = min(min(node.uv[key] for node in group.nodes) for group in groups)
            overall_max = max(max(node.uv[key] for node in group.nodes) for group in groups)
            original_center = (overall_min + overall_max) / 2

            for group in groups:
                group_min = min(node.uv[key] for node in group.nodes)
                group_max = max(node.uv[key] for node in group.nodes)
                group_center = (group_min + group_max) / 2
                offset = original_center - group_center
                for node in group.nodes:
                    node.uv[key] += offset

            if alignment_type == "CENTER":
                self.align_groups(groups, "ALIGN_Y" if key == 0 else "ALIGN_X")

    def align_nodes(self, nodes, alignment_type):
        uv_coords = [node.uv for node in nodes]

        if alignment_type == "MAX_X":
            pos = max(uv.x for uv in uv_coords)
            for node in nodes:
                node.uv.x = pos
        elif alignment_type == "MIN_X":
            pos = min(uv.x for uv in uv_coords)
            for node in nodes:
                node.uv.x = pos
        elif alignment_type == "MAX_Y":
            pos = max(uv.y for uv in uv_coords)
            for node in nodes:
                node.uv.y = pos
        elif alignment_type == "MIN_Y":
            pos = min(uv.y for uv in uv_coords)
            for node in nodes:
                node.uv.y = pos
        elif alignment_type == "ALIGN_X":
            avg_x = sum(uv.x for uv in uv_coords) / len(uv_coords)
            for node in nodes:
                node.uv.x = avg_x
        elif alignment_type == "ALIGN_Y":
            avg_y = sum(uv.y for uv in uv_coords) / len(uv_coords)
            for node in nodes:
                node.uv.y = avg_y
        elif alignment_type == "CENTER":
            center_x = sum(uv.x for uv in uv_coords) / len(uv_coords)
            center_y = sum(uv.y for uv in uv_coords) / len(uv_coords)
            for node in nodes:
                node.uv.x = center_x
                node.uv.y = center_y

    def align_islands(self, island_manager, align_type):
        islands = island_manager.islands
        if not islands:
            return

        if align_type in ["MAX_Y", "MIN_Y", "MIN_X", "MAX_X"]:
            if align_type == "MAX_Y":
                target = max(island.max_uv.y for island in islands)
                for island in islands:
                    island.move(Vector((0, target - island.max_uv.y)))
            elif align_type == "MIN_Y":
                target = min(island.min_uv.y for island in islands)
                for island in islands:
                    island.move(Vector((0, target - island.min_uv.y)))
            elif align_type == "MIN_X":
                target = min(island.min_uv.x for island in islands)
                for island in islands:
                    island.move(Vector((target - island.min_uv.x, 0)))
            elif align_type == "MAX_X":
                target = max(island.max_uv.x for island in islands)
                for island in islands:
                    island.move(Vector((target - island.max_uv.x, 0)))

        elif align_type == "ALIGN_S":
            avg_center = sum((island.center for island in islands), Vector()) / len(islands)
            for island in islands:
                island.move(Vector((avg_center.x - island.center.x, 0)))

        elif align_type in ["ALIGN_X", "ALIGN_Y", "CENTER"]:
            all_min = Vector(min(island.min_uv for island in islands))
            all_max = Vector(max(island.max_uv for island in islands))
            center = (all_min + all_max) / 2

            for island in islands:
                island_center = (island.min_uv + island.max_uv) / 2
                if align_type == "ALIGN_X" or align_type == "CENTER":
                    island.move(Vector((center.x - island_center.x, 0)))
                if align_type == "ALIGN_Y" or align_type == "CENTER":
                    island.move(Vector((0, center.y - island_center.y)))


class MIO3UV_OT_align_edges(Mio3UVOperator):
    bl_idname = "uv.mio3_align_edges"
    bl_label = "Align Edge Loops"
    bl_description = "Align Edge Loops"
    bl_options = {"REGISTER", "UNDO"}

    axis: EnumProperty(
        name="Direction",
        items=[
            ("Y", "Vertical", ""),
            ("X", "Horizontal", ""),
        ],
        default="X",
    )
    threshold: FloatProperty(name="Threshold", default=0.3, min=0.01, max=0.8, step=1)
    blend_factor: FloatProperty(
        name="Blend Factor",
        description="",
        default=1.0,
        min=0.0,
        max=1.0,
    )

    def execute(self, context):
        self.start_time()

        self.objects = self.get_selected_objects(context)

        self.use_uv_select_sync = context.tool_settings.use_uv_select_sync
        if self.use_uv_select_sync:
            self.sync_uv_from_mesh(context, self.objects)
            context.tool_settings.use_uv_select_sync = False
            context.scene.mio3uv.auto_uv_sync_skip = True

        self.objests_state = {}

        for obj in self.objects:
            bm = bmesh.from_edit_mesh(obj.data)
            uv_layer = bm.loops.layers.uv.verify()
            self.objests_state[obj] = {
                "bm": bm,
                "uv_layer": uv_layer,
                "selected_verts": ({vert: vert.select for vert in bm.verts} if self.use_uv_select_sync else None),
                "selected_loops": {loop: loop[uv_layer].select_edge for face in bm.faces for loop in face.loops},
            }

        bpy.ops.mesh.select_linked(delimit={"UV"})

        for obj in self.objects:
            bm = self.objests_state[obj]["bm"]
            uv_layer = self.objests_state[obj]["uv_layer"]
            self.process_uv_selection(bm, uv_layer, self.axis)
            node_manager = UVNodeManager.from_object(obj, bm=bm, uv_layer=uv_layer, mode="EDGE")
            self.align_uv_nodes(node_manager, self.axis)
            self.restore_selection(self.objests_state[obj])
            bmesh.update_edit_mesh(obj.data)

        if self.use_uv_select_sync:
            context.tool_settings.use_uv_select_sync = True

        self.print_time()
        return {"FINISHED"}

    def restore_selection(self, objests_state):
        bm = objests_state["bm"]
        uv_layer = objests_state["uv_layer"]
        if self.use_uv_select_sync:
            for vert, select in objests_state["selected_verts"].items():
                vert.select = select
            bm.select_flush(False)
        for loop, state in objests_state["selected_loops"].items():
            loop[uv_layer].select_edge = state

    def process_uv_selection(self, bm, uv_layer, axis):
        selected_uv_edges = set()
        for face in bm.faces:
            if not face.select:
                continue
            for loop in face.loops:
                if loop[uv_layer].select_edge:
                    edge = loop.edge
                    selected_uv_edges.add((edge, loop))

        for edge, loop in selected_uv_edges:
            if not self.is_uv_edge_aligned(edge, loop, axis, uv_layer):
                for l in edge.link_loops:
                    l[uv_layer].select_edge = False

    def is_uv_edge_aligned(self, edge, loop, axis, uv_layer):
        uv1 = loop[uv_layer].uv
        uv2 = loop.link_loop_next[uv_layer].uv
        edge_vector = uv2 - uv1
        angle = math.atan2(edge_vector.y, edge_vector.x)
        if axis == "X":
            return abs(math.sin(angle)) < self.threshold
        else:
            return abs(math.cos(angle)) < self.threshold

    def align_uv_nodes(self, node_manager, alignment_type="X"):
        for group in node_manager.groups:
            nodes = group.nodes
            original_uvs = [node.uv.copy() for node in nodes]
            uv_coords = [node.uv for node in nodes]

            if alignment_type == "Y":
                avg_x = sum(uv.x for uv in uv_coords) / len(uv_coords)
                for node, original_uv in zip(nodes, original_uvs):
                    aligned_x = avg_x
                    node.uv.x = original_uv.x * (1 - self.blend_factor) + aligned_x * self.blend_factor
            else:
                avg_y = sum(uv.y for uv in uv_coords) / len(uv_coords)
                for node, original_uv in zip(nodes, original_uvs):
                    aligned_y = avg_y
                    node.uv.y = original_uv.y * (1 - self.blend_factor) + aligned_y * self.blend_factor

            group.update_uvs()


classes = [
    MIO3UV_OT_align,
    MIO3UV_OT_align_edges,
]


def register():
    for c in classes:
        bpy.utils.register_class(c)


def unregister():
    for c in classes:
        bpy.utils.unregister_class(c)
