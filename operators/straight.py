import bpy
import time
from bpy.props import BoolProperty, EnumProperty
from ..icons import preview_collections
from ..utils import straight_uv_nodes
from ..classes.uv import UVNodeManager
from ..classes.operator import Mio3UVOperator

class MIO3UV_OT_straight(Mio3UVOperator):
    bl_idname = "uv.mio3_straight"
    bl_label = "Straight"
    bl_description = "Unwrap selected edge loop to a straight line"
    bl_options = {"REGISTER", "UNDO"}

    distribute: EnumProperty(
        items=[
            ("GEOMETRY", "Geometry", ""),
            ("EVEN", "Even", ""),
            ("NONE", "None", ""),
        ],
        name="Type",
        default="GEOMETRY",
    )

    keep_length: BoolProperty(name="Preserve Length", default=True)

    def execute(self, context):
        self.start_time = time.time()
        self.objects = self.get_selected_objects(context)

        use_uv_select_sync = context.tool_settings.use_uv_select_sync

        if context.tool_settings.uv_select_mode not in ["VERTEX", "ISLAND"]:
            context.tool_settings.uv_select_mode = "VERTEX"

        if use_uv_select_sync:
            self.sync_uv_from_mesh(context, self.objects)
            bpy.ops.mesh.select_linked(delimit={'UV'})
            context.tool_settings.use_uv_select_sync = False
            node_manager = UVNodeManager(self.objects, mode="VERT")
        else:
            node_manager = UVNodeManager(self.objects)
    
        original_selected = {}
        for group in node_manager.groups:
            original_selected[group] = {}
            for face in group.bm.faces:
                for loop in face.loops:
                    original_selected[group][loop] = loop[group.uv_layer].select

        for group in node_manager.groups:
            straight_uv_nodes(group, self.distribute, self.keep_length, center=True)
            for node in group.nodes:
                node.update_uv(group.uv_layer)

        bpy.ops.uv.pin(clear=False)
        bpy.ops.uv.select_linked()
        bpy.ops.uv.unwrap(method="ANGLE_BASED", margin=0.001)
        bpy.ops.uv.pin(clear=True)

        for group in node_manager.groups:
            for loop, was_selected in original_selected[group].items():
                loop[group.uv_layer].select = was_selected
            group.update_uvs()

        node_manager.update_uvmeshes()

        if use_uv_select_sync:
            context.tool_settings.use_uv_select_sync = True

        self.print_time(time.time() - self.start_time)
        return {"FINISHED"}


classes = [
    MIO3UV_OT_straight,
]

def register():
    for c in classes:
        bpy.utils.register_class(c)

def unregister():
    for c in classes:
        bpy.utils.unregister_class(c)