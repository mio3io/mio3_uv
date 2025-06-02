import bpy
import bmesh
from mathutils import Vector
from bpy.props import BoolProperty, EnumProperty
from ..classes import UVIslandManager, UVNodeManager, Mio3UVOperator


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

        selected_face = self.check_selected_face_objects(self.objects)
        self.island = True if context.scene.mio3uv.island_mode else selected_face

        if context.scene.mio3uv.edge_mode:
            self.edge_mode = True
        elif context.tool_settings.use_uv_select_sync:
            self.edge_mode = context.tool_settings.mesh_select_mode[1] == True and not self.island
        else:
            self.edge_mode = context.tool_settings.uv_select_mode == "EDGE" and not self.island
        return self.execute(context)

    def execute(self, context):
        self.start_time()
        self.objects = self.get_selected_objects(context)

        use_uv_select_sync = context.tool_settings.use_uv_select_sync
        if use_uv_select_sync:
            self.sync_uv_from_mesh(context, self.objects)

        if self.type == "ALIGN_S":
            try:
                bpy.ops.uv.align(axis="ALIGN_S")
            except:
                return {"CANCELLED"}
            return {"FINISHED"}

        if self.island and not self.edge_mode:
            island_manager = UVIslandManager(self.objects, sync=use_uv_select_sync)
            if not island_manager.islands:
                return {"CANCELLED"}
            self.align_islands(island_manager, self.type)
            island_manager.update_uvmeshes()
        else:
            node_manager = UVNodeManager(self.objects, sync=use_uv_select_sync)
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


def register():
    bpy.utils.register_class(MIO3UV_OT_align)


def unregister():
    bpy.utils.unregister_class(MIO3UV_OT_align)
