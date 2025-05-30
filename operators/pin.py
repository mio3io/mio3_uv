import bpy
import bmesh
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

        if context.tool_settings.use_uv_select_sync:
            self.sync_uv_from_mesh(context, objects)

        return self.execute(context)

    def execute(self, context):
        self.start_time()
        objects = self.get_selected_objects(context)

        for obj in objects:
            me = obj.data
            bm = bmesh.from_edit_mesh(me)
            uv_layer = bm.loops.layers.uv.verify()

            for face in bm.faces:
                if not face.select:
                    continue

                for loop in face.loops:
                    loop_uv = loop[uv_layer]
                    if loop_uv.select:
                        if self.clear:
                            loop_uv.pin_uv = False
                        else:
                            loop_uv.pin_uv = True

            bmesh.update_edit_mesh(me)

        self.print_time()

        return {"FINISHED"}


def register():
    bpy.utils.register_class(MIO3UV_OT_pin)


def unregister():
    bpy.utils.unregister_class(MIO3UV_OT_pin)
