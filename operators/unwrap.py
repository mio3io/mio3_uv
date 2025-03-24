import bpy
from bpy.props import  EnumProperty
from bpy.app.translations import pgettext_iface as tt_iface
from mathutils import Vector
from ..classes.uv import UVIslandManager
from ..classes.operator import Mio3UVOperator


class MIO3UV_OT_unwrap(Mio3UVOperator):
    bl_idname = "uv.mio3_unwrap"
    bl_label = "UV Unwrap"
    bl_description = "UV Unwrap"
    bl_options = {"REGISTER", "UNDO"}

    @classmethod
    def description(cls, context, properties):
        if properties.axis == "X":
            return tt_iface("Unwrap Horizontal(X) Only")
        elif properties.axis == "Y":
            return tt_iface("Unwrap Vertical(Y) Only")
        return tt_iface("UV Unwrap")

    def unwrap_method_items(self, context):
        items = [
            ("ANGLE_BASED", "Angle Based", "Angle based unwrapping method"),
            ("CONFORMAL", "Conformal", "Conformal mapping method"),
        ]
        if bpy.app.version >= (4, 3, 0):
            items.append(("MINIMUM_STRETCH", "Minimum Stretch", "Minimum stretch mapping method"))
        return items

    method: EnumProperty(
        name="Method",
        items=unwrap_method_items,
    )
    axis: EnumProperty(
        name="Direction",
        items=[
            ("BOTH", "Both", ""),
            ("X", "Horizontal", ""),
            ("Y", "Vertical", ""),
        ],
    )
    keep: EnumProperty(
        name="Keep",
        description="Keep Position, Scale, Angle",
        items=[
            ("ALL", "All", ""),
            ("INPLACE", "Position and Scale", ""),
            ("NONE", "None", ""),
        ],
    )

    @classmethod
    def poll(cls, context):
        return cls.is_valid_object(context.active_object)

    def execute(self, context):
        self.start_time()
        self.objects = self.get_selected_objects(context)

        for obj in self.objects:
            if not obj.data.uv_layers:
                bpy.ops.uv.unwrap(method=self.method, margin=0.001)
                return {"FINISHED"}

        use_uv_select_sync = context.tool_settings.use_uv_select_sync
        if use_uv_select_sync:
            self.sync_uv_from_mesh(context, self.objects)
            context.tool_settings.use_uv_select_sync = False
            context.scene.mio3uv.auto_uv_sync_skip = True
            island_manager = UVIslandManager(self.objects, mesh_link_uv=True)
        else:
            island_manager = UVIslandManager(self.objects)

        axis = self.axis

        original_uvs = {}
        for island in island_manager.islands:
            island.store_selection()
            if self.keep == "NONE":
                island.ajast = False
            elif self.method == "MINIMUM_STRETCH":
                island.ajast = True
            else:
                island.ajast = self.init_select_uvs(island)

            original_uvs[island] = {}
            if axis != "BOTH":
                original_uvs_island = original_uvs[island]
                uv_layer = island.uv_layer
                for face in island.faces:
                    for loop in face.loops:
                        if loop[uv_layer].select:
                            original_uvs_island[loop] = loop[uv_layer].uv.copy()

            if island.ajast:
                island.update_bounds()
                island.original_center = island.center.copy()
                island.original_width = island.width
                island.original_height = island.height

        bpy.ops.uv.unwrap(method=self.method, margin=0.001)

        for island in island_manager.islands:
            if axis != "BOTH":
                original_uvs_island = original_uvs[island]
                uv_layer = island.uv_layer
                for face in island.faces:
                    for loop in face.loops:
                        if loop in original_uvs_island:
                            current_uv = loop[uv_layer].uv
                            original_uv = original_uvs_island[loop]
                            if axis == "X":
                                loop[uv_layer].uv = Vector((current_uv.x, original_uv.y))
                            elif axis == "Y":
                                loop[uv_layer].uv = Vector((original_uv.x, current_uv.y))
            if island.ajast:
                island.update_bounds()
                offset = island.original_center - island.center
                self.transform_island(island, offset)
                if hasattr(island, "tmp_uv_list"):
                    for uv in island.tmp_uv_list:
                        uv.select = True

        if use_uv_select_sync:
            island_manager.restore_vertex_selection()
            context.tool_settings.use_uv_select_sync = True

        island_manager.update_uvmeshes()

        self.print_time()
        return {"FINISHED"}

    def transform_island(self, island, offset):
        original_size = Vector((island.original_width, island.original_height))
        current_size = Vector((island.width, island.height))
        original_center = island.center

        scale_x = original_size.x / current_size.x if current_size.x != 0 else 1
        scale_y = original_size.y / current_size.y if current_size.y != 0 else 1
        scale = (scale_x + scale_y) / 2

        for face in island.faces:
            for loop in face.loops:
                uv = loop[island.uv_layer]
                uv.uv = (uv.uv - original_center) * scale + original_center
                uv.uv += offset

    def count_uvs(self, island):
        uv_layer = island.uv_layer
        unselected_count = 0
        for face in island.faces:
            for loop in face.loops:
                if not loop[uv_layer].select:
                    unselected_count += 1
                    if unselected_count >= 2:
                        return False
        return True

    def init_select_uvs(self, island):
        island.tmp_uv_list = []

        pinned_count = sum(1 for face in island.faces for loop in face.loops if loop[island.uv_layer].pin_uv)
        if pinned_count >= 2:
            return False

        deselect_count = island.all_uv_count - island.selection_uv_count
        if deselect_count >= 2:
            return False

        uv_layer = island.uv_layer
        selected_nodes = {}
        for face in island.faces:
            for loop in face.loops:
                uv = loop[uv_layer]
                if uv.select:
                    key = (uv.uv.x, uv.uv.y, loop.vert.index)
                    if key not in selected_nodes:
                        selected_nodes[key] = []
                    selected_nodes[key].append(uv)

        sorted_keys = sorted(selected_nodes.keys())
        nodes_to_process = []
        if sorted_keys:
            nodes_to_process.append(selected_nodes[sorted_keys[0]])
            if len(sorted_keys) > 1:
                nodes_to_process.append(selected_nodes[sorted_keys[-1]])

        additional_deselect_needed = 2 - deselect_count
        for uvs in nodes_to_process:
            for uv in uvs:
                if self.keep == "ALL":
                    uv.select = False
                island.tmp_uv_list.append(uv)
            additional_deselect_needed -= 1
            if additional_deselect_needed == 0:
                break
        return additional_deselect_needed == 0

    def draw(self, context):
        layout = self.layout
        layout.use_property_decorate = False
        layout.use_property_split = True
        layout.prop(self, "method")
        layout.prop(self, "keep", text="Keep")
        layout.use_property_split = False
        row = layout.row()
        row.prop(self, "axis", expand=True)

classes = [MIO3UV_OT_unwrap]


def register():
    for c in classes:
        bpy.utils.register_class(c)


def unregister():
    for c in classes:
        bpy.utils.unregister_class(c)
