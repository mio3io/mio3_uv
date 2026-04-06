import bpy
from bpy.types import AddonPreferences
from bpy.props import BoolProperty, FloatVectorProperty, EnumProperty


class MIO3UV_preferences(AddonPreferences):
    bl_idname = __package__

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
    ui_help: BoolProperty(name="Help Messages", default=True, options=set())
    ui_guide: BoolProperty(name="Show 3D Space Guide", default=True, options=set())
    ui_guide_col: FloatVectorProperty(
        name="3D Space Guide Color",
        subtype="COLOR_GAMMA",
        size=4,
        default=(0.0, 0.7, 1.0, 1.0),
        min=0.0,
        max=1.0,
        options=set(),
    )
    ui_padding_col: FloatVectorProperty(
        name="Padding Guide Color",
        subtype="COLOR_GAMMA",
        size=4,
        default=(0.1, 0.5, 1.0, 1.0),
        min=0.0,
        max=1.0,
        options=set(),
    )

    def draw(self, context):
        layout = self.layout
        layout.use_property_split = True
        layout.use_property_decorate = False
        col = layout.column()
        col.prop(self, "default_symmetry_priority")
        col.prop(self, "auto_uv_sync")
        col.prop(self, "ui_help")
        col.prop(self, "ui_guide")
        col.prop(self, "ui_guide_col")
        col.prop(self, "ui_padding_col")


def register():
    bpy.utils.register_class(MIO3UV_preferences)


def unregister():
    bpy.utils.unregister_class(MIO3UV_preferences)
