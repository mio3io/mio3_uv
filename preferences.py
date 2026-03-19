import bpy
from bpy.types import AddonPreferences
from bpy.props import BoolProperty, EnumProperty


class MIO3UV_preferences(AddonPreferences):
    bl_idname = __package__

    # ui_legacy: BoolProperty(
    #     name="Legacy UI Layout",
    #     default=True,
    # )
    auto_uv_sync: BoolProperty(name="UV Sync Auto Select", default=False, options=set())
    default_symmetry_priority: EnumProperty(
        name="Symmetry Priority",
        description="Specifies which side to use as the reference during automatic symmetry.",
        items=[
            ("NEGATIVE", "Negative", ""),
            ("POSITIVE", "Positive", ""),
        ],
        default="POSITIVE",
        options=set(),
    )

    def draw(self, context):
        layout = self.layout
        layout.use_property_split = True
        layout.use_property_decorate = False
        col = layout.column()
        col.prop(self, "default_symmetry_priority")
        col.prop(self, "auto_uv_sync")


def register():
    bpy.utils.register_class(MIO3UV_preferences)


def unregister():
    bpy.utils.unregister_class(MIO3UV_preferences)
