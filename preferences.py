import bpy
from bpy.types import AddonPreferences
from bpy.props import BoolProperty


class MIO3UV_preferences(AddonPreferences):
    bl_idname = __package__

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


def register():
    bpy.utils.register_class(MIO3UV_preferences)


def unregister():
    bpy.utils.unregister_class(MIO3UV_preferences)
