import bmesh
import bpy
from bpy.app.translations import pgettext_iface as tt_iface
from bpy.props import BoolProperty
from ..classes import Mio3UVOperator


class MIO3UV_OT_pin(Mio3UVOperator):
    bl_idname = "uv.mio3_pin"
    bl_label = "Pin"
    bl_description = "[Alt] {}".format(tt_iface("Clear"))
    bl_options = {"REGISTER", "UNDO"}

    clear: BoolProperty(name="Clear", default=False)

    def invoke(self, context, event):
        if event.alt:
            self.clear = True
        if event.ctrl or event.shift:
            self.clear = False
        objects = self.get_selected_objects(context)
        if not objects:
            self.report({"WARNING"}, "Object is not selected")
            return {"CANCELLED"}

        return self.execute(context)

    def execute(self, context):
        self.start_time()
        objects = self.get_selected_objects(context)
        if not objects:
            self.report({"WARNING"}, "Object is not selected")
            return {"CANCELLED"}

        use_uv_select_sync = context.scene.tool_settings.use_uv_select_sync
        pin_state = not self.clear

        for obj in objects:
            bm = bmesh.from_edit_mesh(obj.data)
            uv_layer = bm.loops.layers.uv.verify()

            if use_uv_select_sync and not bm.uv_select_sync_valid:
                bm.uv_select_sync_from_mesh()

            for face in bm.faces:
                if face.hide:
                    continue
                if not use_uv_select_sync and not face.select:
                    continue

                for loop in face.loops:
                    if loop.uv_select_vert:
                        loop[uv_layer].pin_uv = pin_state

            bmesh.update_edit_mesh(obj.data)

        self.print_time()
        return {"FINISHED"}


def register():
    bpy.utils.register_class(MIO3UV_OT_pin)


def unregister():
    bpy.utils.unregister_class(MIO3UV_OT_pin)
