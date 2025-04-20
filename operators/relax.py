import bpy
from mathutils import Vector
from bpy.props import BoolProperty, EnumProperty, IntProperty
from ..classes.uv import UVNodeManager
from ..classes.operator import Mio3UVOperator


class MIO3UV_OT_relax(Mio3UVOperator):
    bl_idname = "uv.mio3_relax"
    bl_label = "Relax"
    bl_description = "Relax UVs"
    bl_options = {"REGISTER", "UNDO"}

    method: EnumProperty(
        items=[
            ("DEFAULT", "Default", ""),
            ("MINIMIZE", "Minimize Stretch", ""),
        ],
        name="Mode",
    )
    keep_pin: BoolProperty(name="Keep Pin", default=False)
    keep_boundary: BoolProperty(name="Keep Boundary", default=False)
    relax_x: BoolProperty(name="X", default=True)
    relax_y: BoolProperty(name="Y", default=True)
    iterations: IntProperty(
        name="Iterations",
        description="Number of times to apply the relaxation",
        default=1,
        min=1,
        max=20,
    )
    _factor = 0.5

    def invoke(self, context, event):
        self.objects = self.get_selected_objects(context)
        if not self.objects:
            self.report({"WARNING"}, "Object is not selected")
            return {"CANCELLED"}
        return self.execute(context)

    def execute(self, context):
        self.start_time()
        self.objects = self.get_selected_objects(context)

        if self.method == "MINIMIZE":
            bpy.ops.uv.minimize_stretch(fill_holes=True, blend=0, iterations=self.iterations)
        else:
            use_uv_select_sync = context.tool_settings.use_uv_select_sync
            if use_uv_select_sync:
                self.sync_uv_from_mesh(context, self.objects)
                node_manager = UVNodeManager(self.objects, mode="VERT")
            else:
                node_manager = UVNodeManager(self.objects, mode="FACE")

            self.cache_data = self.prepare_cache_data(node_manager)

            for _ in range(self.iterations):
                self.smooth_selected_uv(node_manager)
            node_manager.update_uvmeshes()

        self.print_time()
        return {"FINISHED"}

    def prepare_cache_data(self, node_manager):
        for group in node_manager.groups:
            group.node_cache = []
            for node in group.nodes:
                is_boundary_node = any(loop.edge.is_boundary or loop.edge.seam for loop in node.loops)
                is_pinned = any(loop[group.uv_layer].pin_uv for loop in node.loops) if self.keep_pin else False
                group.node_cache.append((node, is_boundary_node, is_pinned))

    def smooth_selected_uv(self, node_manager):
        for group in node_manager.groups:
            new_positions = {}

            for node, is_boundary_node, is_pinned in group.node_cache:
                if len(node.neighbors) == 1: # End point
                    continue
                if is_pinned:
                    continue
                if self.keep_boundary and is_boundary_node:
                    continue

                if node.neighbors:
                    avg_pos = sum((n.uv for n in node.neighbors), Vector((0, 0))) / len(node.neighbors)
                    new_pos = node.uv.copy()
                    
                    if self.relax_x:
                        new_pos.x = node.uv.x + (avg_pos.x - node.uv.x) * self._factor
                    if self.relax_y:
                        new_pos.y = node.uv.y + (avg_pos.y - node.uv.y) * self._factor
                    
                    new_positions[node] = new_pos

            for node, new_pos in new_positions.items():
                node.uv = new_pos
                node.update_uv(group.uv_layer)

    def draw(self, context):
        layout = self.layout
        layout.use_property_split = True
        layout.use_property_decorate = False
        layout.prop(self, "method")

        row = layout.row(align=True)
        row.prop(self, "relax_x", toggle=True)
        row.prop(self, "relax_y", toggle=True)
        if self.method == "MINIMIZE":
            row.enabled = False

        row = layout.row()
        row.prop(self, "keep_pin")
        if self.method == "MINIMIZE":
            row.enabled = False

        row = layout.row()
        row.prop(self, "keep_boundary")
        if self.method == "MINIMIZE":
            row.enabled = False

        row = layout.row()
        row.prop(self, "iterations")


classes = [
    MIO3UV_OT_relax,
]


def register():
    for c in classes:
        bpy.utils.register_class(c)


def unregister():
    for c in classes:
        bpy.utils.unregister_class(c)
