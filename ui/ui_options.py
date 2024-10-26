import bpy
from bpy.types import Panel


class MIO3UV_PT_options(Panel):
    bl_label = "Options"
    bl_idname = "MIO3UV_PT_options"
    bl_space_type = "IMAGE_EDITOR"
    bl_region_type = "UI"
    bl_category = "Mio3"
    bl_options = {"DEFAULT_CLOSED"}

    @classmethod
    def poll(cls, context):
        return context.active_object is not None

    def draw(self, context):
        layout = self.layout
        layout.prop(context.scene.mio3uv, "udim")


classes = [MIO3UV_PT_options]


def register():
    for c in classes:
        bpy.utils.register_class(c)


def unregister():
    for c in classes:
        bpy.utils.unregister_class(c)
