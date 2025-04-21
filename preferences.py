import bpy
from bpy.types import AddonPreferences
from bpy.props import BoolProperty


class MIO3UV_preferences(AddonPreferences):
    bl_idname = __name__

    # ui_legacy: BoolProperty(
    #     name="Legacy UI Layout",
    #     default=True,
    # )
    auto_uv_sync: BoolProperty(
        name="UV Sync Auto Select",
        default=False,
    )

    def draw(self, context):
        layout = self.layout
        # layout.prop(self, "ui_legacy")
        layout.prop(self, "auto_uv_sync")


def register(name):
    MIO3UV_preferences.bl_idname = name
    bpy.utils.register_class(MIO3UV_preferences)


def unregister(name):
    MIO3UV_preferences.bl_idname = name
    bpy.utils.unregister_class(MIO3UV_preferences)
