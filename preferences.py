import bpy
from bpy.types import AddonPreferences
from bpy.props import BoolProperty


class MIO3UV_preferences(AddonPreferences):
    bl_idname = __name__

    ui_legacy: BoolProperty(
        name="Legacy UI Layout",
        default=True,
    )

    def draw(self, context):
        layout = self.layout
        layout.prop(self, "ui_legacy")


classes = [
    MIO3UV_preferences,
]


def register(name):
    MIO3UV_preferences.bl_idname = name
    bpy.utils.register_class(MIO3UV_preferences)


def unregister(name):
    MIO3UV_preferences.bl_idname = name
    bpy.utils.unregister_class(MIO3UV_preferences)
