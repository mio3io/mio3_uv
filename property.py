import bpy
from .operators import view_padding
from bpy.types import PropertyGroup
from bpy.props import BoolProperty, FloatProperty, IntProperty, EnumProperty, PointerProperty
from .icons import preview_collections


def callback_update_padding(self, context):
    view_padding.MIO3UV_OT_view_padding.redraw(context)


class MIO3_UVProperties(PropertyGroup):

    edge_mode: BoolProperty(name="Edge Mode", description="Edge Mode", default=False)
    island_mode: BoolProperty(name="Island Mode", description="Island Mode", default=False)

    align_mode: EnumProperty(
        name="Mode",
        items=[
            ("AUTO", "Auto", "Auto"),
            ("ISLAND", "Island", "Island"),
            ("GROUP", "Group", "Group"),
        ],
        default="AUTO",
    )

    def symmetry_center_items(self, context):
        icons = preview_collections["icons"]
        return [
            ("X", "X", "", icons["AXIS_X"].icon_id, 0),
            ("Y", "Y", "", icons["AXIS_Y"].icon_id, 1),
        ]

    udim: BoolProperty(name="UDIM", default=False)

    symmetry_center: EnumProperty(
        name="Center",
        items=[
            ("GLOBAL", "Center", "Center"),
            ("CURSOR", "Cursor", "Cursor"),
            ("SELECT", "Selection", "Selection"),
        ],
        default="GLOBAL",
    )

    symmetry_uv_axis: EnumProperty(
        name="Axis",
        description="Axis of symmetry in UV space",
        items=symmetry_center_items,
        default=0,
    )
    symmetry_3d_axis: EnumProperty(
        name="Axis",
        description="Axis of symmetry in 3D space",
        items=[
            ("AUTO", "Auto", "Sync UV Axis"),
            ("X", "X", "X axis in 3D space"),
            ("Y", "Y", "Y axis in 3D space"),
            ("Z", "Z", "Z axis in 3D space"),
        ],
        default="AUTO",
    )
    grid_link: BoolProperty(name="Grid Link", default=True)


class MIO3UV_ObjectProps(PropertyGroup):
    realtime: BoolProperty(name="Realtime", description="Warning: This option may poor performance", default=False)
    image_size: EnumProperty(
        name="Size",
        description="Choose an image size",
        items=[
            ("512", "512", "512x512 (4px)"),
            ("1024", "1024", "1024x1024 (8px)"),
            ("2048", "2048", "2048x2048 (16px)"),
            ("4096", "4096", "4096x4096 (32px)"),
            ("8192", "8192", "8192x8192 (64px)"),
        ],
        default="2048",
        update=callback_update_padding,
    )
    padding_px: IntProperty(name="Padding (px)", default=16, update=callback_update_padding)


class MIO3UV_ImageProps(PropertyGroup):
    def callback_update_use_exposure(self, context):
        if context.edit_image is not None:
            context.edit_image.use_view_as_render = self.use_exposure
            context.scene.view_settings.exposure = self.exposure if self.use_exposure else 0

    def callback_update_exposure(self, context):
        context.scene.view_settings.exposure = self.exposure

    use_exposure: BoolProperty(name="Exposure", default=False, update=callback_update_use_exposure)
    exposure: FloatProperty(name="Exposure Level", default=-5, min=-7, max=5, step=10, update=callback_update_exposure)


classes = [MIO3_UVProperties, MIO3UV_ObjectProps, MIO3UV_ImageProps]


def register():
    for c in classes:
        bpy.utils.register_class(c)
    bpy.types.Scene.mio3uv = PointerProperty(type=MIO3_UVProperties)
    bpy.types.Object.mio3uv = PointerProperty(type=MIO3UV_ObjectProps)
    bpy.types.Image.mio3uv = PointerProperty(type=MIO3UV_ImageProps)


def unregister():
    del bpy.types.Image.mio3uv
    del bpy.types.Object.mio3uv
    del bpy.types.Scene.mio3uv
    for c in classes:
        bpy.utils.unregister_class(c)
