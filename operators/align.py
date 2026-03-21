import bpy
from mathutils import Vector
from bpy.props import BoolProperty, EnumProperty
from ..classes import UVIslandManager, UVNodeManager, Mio3UVOperator


class MIO3UV_OT_align(Mio3UVOperator):
    bl_idname = "uv.mio3_align"
    bl_label = "Align UVs"
    bl_description = "Align UVs of vertices, edge loops and islands"
    bl_options = {"REGISTER", "UNDO"}

    method: EnumProperty(
        items=[
            ("ALIGN", "Align", "Align UVs to the target position"),
            ("MOVE", "Move", "Move UVs to the target position while keeping their relative spacing"),
        ],
        name="Method",
    )
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
            ("MAX_Y_MIN_X", "Top Left", ""),
            ("MAX_Y_MAX_X", "Top Right", ""),
            ("MIN_Y_MIN_X", "Bottom Left", ""),
            ("MIN_Y_MAX_X", "Bottom Right", ""),
        ],
        name="Align Axis",
        default="MAX_Y",
        options={"HIDDEN"},
    )
    edge_mode: BoolProperty(name="Edge Mode", description="Process each edge loops", default=False)
    island: BoolProperty(name="Island Mode", default=False)
    align_to: EnumProperty(
        name="Align To",
        items=[
            ("BBOX", "Bounding Box", ""),
            ("UV_AREA", "UV Area", ""),
            ("CURSOR", "2D Cursor", ""),
        ],
        default="BBOX",
    )

    def draw(self, context):
        layout = self.layout
        layout.use_property_decorate = False
        layout.use_property_split = True
        col = layout.column()
        col.row().prop(self, "method", expand=True)
        col.enabled = self.island and not self.edge_mode
        layout.prop(self, "edge_mode")
        layout.prop(self, "island")
        layout.prop(self, "align_to", expand=True)

    def invoke(self, context, event):
        objects = self.get_selected_objects(context)
        if not objects:
            self.report({"WARNING"}, "Object is not selected")
            return {"CANCELLED"}

        face_selected = self.check_selected_face_objects(objects)
        self.island = True if context.scene.mio3uv.island_mode else face_selected

        if context.scene.mio3uv.edge_mode:
            self.edge_mode = True
        elif context.tool_settings.use_uv_select_sync:
            self.edge_mode = context.tool_settings.mesh_select_mode[1] == True and not self.island
        else:
            self.edge_mode = context.tool_settings.uv_select_mode == "EDGE" and not self.island
        return self.execute(context)

    def execute(self, context):
        self.start_time()
        objects = self.get_selected_objects(context)
        align_to = self.align_to
        align_types = self.expand_align_types(self.type)
        use_uv_select_sync = context.tool_settings.use_uv_select_sync
        self.use_udim = context.scene.mio3uv.udim
        self.avg_center = Vector((0.5, 0.5))

        if self.type == "ALIGN_S":
            try:
                bpy.ops.uv.align(axis="ALIGN_S")
            except:
                return {"CANCELLED"}
            return {"FINISHED"}

        if self.island and not self.edge_mode:
            island_manager = UVIslandManager(objects, sync=use_uv_select_sync)
            uv_center = island_manager.get_bbox_center()
            self.avg_center = uv_center
            if not island_manager.islands:
                return {"CANCELLED"}
            for align_type in align_types:
                islands = island_manager.islands
                if islands:
                    if self.method == "MOVE":
                        self.move_islands(context, islands, align_type, align_to)
                    else:
                        self.align_islands(context, islands, align_type, align_to)

            island_manager.update_uvmeshes(True)
        else:
            node_manager = UVNodeManager(objects, sync=use_uv_select_sync)
            uv_center = node_manager.get_bbox_center()
            self.avg_center = uv_center
            if not node_manager.groups:
                return {"CANCELLED"}
            for align_type in align_types:
                self.align_uv_nodes(context, node_manager, align_type, align_to)
            node_manager.update_uvmeshes()

        self.print_time()
        return {"FINISHED"}

    def expand_align_types(self, align_type):
        corner_map = {
            "MAX_Y_MIN_X": ["MAX_Y", "MIN_X"],
            "MAX_Y_MAX_X": ["MAX_Y", "MAX_X"],
            "MIN_Y_MIN_X": ["MIN_Y", "MIN_X"],
            "MIN_Y_MAX_X": ["MIN_Y", "MAX_X"],
        }
        return corner_map.get(align_type, [align_type])

    def group_current_value(self, group, alignment_type, axis):
        coords = [node.uv.x if axis == 0 else node.uv.y for node in group.nodes]
        if alignment_type in ["MAX_X", "MAX_Y"]:
            return max(coords)
        if alignment_type in ["MIN_X", "MIN_Y"]:
            return min(coords)
        return (min(coords) + max(coords)) / 2

    def align_uv_nodes(self, context, node_manager, alignment_type, align_to):
        if self.edge_mode and self.island:
            self.align_groups(context, node_manager.groups, alignment_type, align_to)
        elif self.edge_mode:
            for group in node_manager.groups:
                self.align_nodes(context, group.nodes, alignment_type, align_to)
        else:
            all_nodes = [node for group in node_manager.groups for node in group.nodes]
            self.align_nodes(context, all_nodes, alignment_type, align_to)

        for group in node_manager.groups:
            group.update_uvs()

        for group in node_manager.groups:
            for node in group.nodes:
                node.select = True

    def align_groups(self, context, groups, alignment_type, align_to):
        if not groups:
            return

        if alignment_type in ["MAX_X", "MIN_X", "ALIGN_X", "MAX_Y", "MIN_Y", "ALIGN_Y"]:
            axis = 0 if alignment_type in ["MAX_X", "MIN_X", "ALIGN_X"] else 1
            target = self.get_target_value(context, groups, alignment_type, align_to)
            for group in groups:
                current = self.group_current_value(group, alignment_type, axis)
                offset = target - current
                for node in group.nodes:
                    if axis == 0:
                        node.uv.x += offset
                    else:
                        node.uv.y += offset
        elif alignment_type == "CENTER":
            self.align_groups(context, groups, "ALIGN_X", align_to)
            self.align_groups(context, groups, "ALIGN_Y", align_to)

    def align_nodes(self, context, nodes, alignment_type, align_to):
        uv_coords = [node.uv for node in nodes]

        if alignment_type in ["MAX_X", "MIN_X", "ALIGN_X", "MAX_Y", "MIN_Y", "ALIGN_Y"]:
            axis = 0 if alignment_type in ["MAX_X", "MIN_X", "ALIGN_X"] else 1
            pos = self.get_target_value(context, uv_coords, alignment_type, align_to)
            for node in nodes:
                if axis == 0:
                    node.uv.x = pos
                else:
                    node.uv.y = pos
        elif alignment_type == "CENTER":
            center_x = self.get_target_value(context, uv_coords, "ALIGN_X", align_to)
            center_y = self.get_target_value(context, uv_coords, "ALIGN_Y", align_to)
            for node in nodes:
                node.uv.x = center_x
                node.uv.y = center_y

    def align_islands(self, context, islands, align_type, align_to):
        if align_type in ["MAX_Y", "MIN_Y", "MIN_X", "MAX_X"]:
            target = self.get_target_value(context, islands, align_type, align_to)
            axis = 0 if align_type in ["MAX_X", "MIN_X", "ALIGN_X"] else 1

            for island in islands:
                uv = island.max_uv if align_type in ["MAX_X", "MAX_Y"] else island.min_uv
                current = uv.x if axis == 0 else uv.y
                offset = target - current
                island.move(Vector((offset, 0)) if axis == 0 else Vector((0, offset)))

        elif align_type == "ALIGN_S":
            avg_center = sum((island.center for island in islands), Vector()) / len(islands)
            for island in islands:
                island.move(Vector((avg_center.x - island.center.x, 0)))

        elif align_type in ["ALIGN_X", "ALIGN_Y", "CENTER"]:
            center = Vector(
                (
                    self.get_target_value(context, islands, "ALIGN_X", align_to),
                    self.get_target_value(context, islands, "ALIGN_Y", align_to),
                )
            )

            for island in islands:
                island_center = (island.min_uv + island.max_uv) / 2
                if align_type == "ALIGN_X" or align_type == "CENTER":
                    island.move(Vector((center.x - island_center.x, 0)))
                if align_type == "ALIGN_Y" or align_type == "CENTER":
                    island.move(Vector((0, center.y - island_center.y)))

    def move_islands(self, context, islands, align_type, align_to):
        min_x = min(island.min_uv.x for island in islands)
        max_x = max(island.max_uv.x for island in islands)
        min_y = min(island.min_uv.y for island in islands)
        max_y = max(island.max_uv.y for island in islands)

        offset_x, offset_y = 0.0, 0.0
        if align_type == "MAX_X":
            target = self.get_target_value(context, islands, align_type, align_to)
            offset_x = target - max_x
        elif align_type == "MIN_X":
            target = self.get_target_value(context, islands, align_type, align_to)
            offset_x = target - min_x
        elif align_type == "MAX_Y":
            target = self.get_target_value(context, islands, align_type, align_to)
            offset_y = target - max_y
        elif align_type == "MIN_Y":
            target = self.get_target_value(context, islands, align_type, align_to)
            offset_y = target - min_y
        elif align_type == "ALIGN_X":
            target = self.get_target_value(context, islands, align_type, align_to)
            current = (min_x + max_x) / 2
            offset_x = target - current
        elif align_type == "ALIGN_Y":
            target = self.get_target_value(context, islands, align_type, align_to)
            current = (min_y + max_y) / 2
            offset_y = target - current
        elif align_type == "CENTER":
            target_x = self.get_target_value(context, islands, "ALIGN_X", align_to)
            target_y = self.get_target_value(context, islands, "ALIGN_Y", align_to)
            current_x = (min_x + max_x) / 2
            current_y = (min_y + max_y) / 2
            offset_x = target_x - current_x
            offset_y = target_y - current_y

        if offset_x == 0.0 and offset_y == 0.0:
            return

        offset = Vector((offset_x, offset_y))
        for island in islands:
            island.move(offset)

    def get_target_value(self, context, elements, alignment_type, align_to):
        axis = 0 if alignment_type in ["MAX_X", "MIN_X", "ALIGN_X"] else 1
        if align_to == "BBOX" and alignment_type in ["ALIGN_X", "ALIGN_Y"]:
            min_type = "MIN_X" if axis == 0 else "MIN_Y"
            max_type = "MAX_X" if axis == 0 else "MAX_Y"
            min_values = self.collect_values(elements, axis, min_type)
            max_values = self.collect_values(elements, axis, max_type)
            if not min_values or not max_values:
                return 0.0
            return (min(min_values) + max(max_values)) / 2

        if align_to == "UV_AREA":
            if alignment_type in ["MAX_X", "MAX_Y"]:
                local = 1.0
            elif alignment_type in ["MIN_X", "MIN_Y"]:
                local = 0.0
            else:
                local = 0.5

            base_co = Vector((local, local))
            udim_co = self.get_udim_co(self.use_udim, base_co, self.avg_center)
            return udim_co.x if axis == 0 else udim_co.y

        if align_to == "CURSOR":
            cursor = context.space_data.cursor_location
            return cursor.x if axis == 0 else cursor.y

        values = self.collect_values(elements, axis, alignment_type)
        if not values:
            return 0.0
        if alignment_type in ["MAX_X", "MAX_Y"]:
            return max(values)
        if alignment_type in ["MIN_X", "MIN_Y"]:
            return min(values)
        return sum(values) / len(values)

    def collect_values(self, elements, axis, alignment_type):
        values = []

        for element in elements:
            if hasattr(element, "x") and hasattr(element, "y"):
                values.append(element.x if axis == 0 else element.y)
            elif hasattr(element, "uv"):
                values.append(element.uv.x if axis == 0 else element.uv.y)
            elif hasattr(element, "nodes"):
                coords = [node.uv.x if axis == 0 else node.uv.y for node in element.nodes]
                if alignment_type in ["MAX_X", "MAX_Y"]:
                    values.append(max(coords))
                elif alignment_type in ["MIN_X", "MIN_Y"]:
                    values.append(min(coords))
                else:
                    values.append((min(coords) + max(coords)) / 2)
            elif hasattr(element, "min_uv") and hasattr(element, "max_uv"):
                if axis == 0:
                    min_v = element.min_uv.x
                    max_v = element.max_uv.x
                else:
                    min_v = element.min_uv.y
                    max_v = element.max_uv.y

                if alignment_type in ["MAX_X", "MAX_Y"]:
                    values.append(max_v)
                elif alignment_type in ["MIN_X", "MIN_Y"]:
                    values.append(min_v)
                else:
                    values.append((min_v + max_v) / 2)

        return values

    @staticmethod
    def get_udim_co(use_udim, co, element):
        center = element.center if hasattr(element, "center") else element
        if use_udim:
            return Vector((int(center.x) + co.x, int(center.y) + co.y))
        else:
            return co

def register():
    bpy.utils.register_class(MIO3UV_OT_align)


def unregister():
    bpy.utils.unregister_class(MIO3UV_OT_align)
