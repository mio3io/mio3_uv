import bpy
from bpy.types import Panel
from bpy.app.translations import pgettext_iface as tt_iface
from ..operators.view_padding import MIO3UV_OT_view_padding
from ..icons import preview_collections


class MIO3UV_PT_View(Panel):
    bl_label = "Display"
    bl_idname = "MIO3UV_PT_View"
    bl_space_type = "IMAGE_EDITOR"
    bl_region_type = "UI"
    bl_category = "Mio3"
    bl_options = {"DEFAULT_CLOSED"}

    @classmethod
    def poll(cls, context):
        return context.active_object is not None
        # return context.area.spaces.active.mode == "UV" and context.mode == "EDIT_MESH"

    def draw(self, context):
        layout = self.layout
        icons = preview_collections["icons"]

        mio3uv = context.active_object.mio3uv

        layout.prop(context.scene.mio3uv, "udim")

        row = layout.row()
        row.prop(mio3uv, "image_size")

        col = layout.column(align=True)
        col.operator("mio3uv.color_grid", text=tt_iface("Checker Map"), icon_value=icons["COLOR_GRID"].icon_id)


class MIO3UV_PT_SubGuidePadding(Panel):
    bl_label = "Padding"
    bl_idname = "MIO3UV_PT_SubGuidePadding"
    bl_space_type = "IMAGE_EDITOR"
    bl_region_type = "UI"
    bl_category = "Mio3"
    bl_parent_id = "MIO3UV_PT_View"
    bl_options = {"DEFAULT_CLOSED"}

    def draw(self, context):
        icons = preview_collections["icons"]
        layout = self.layout
        mio3uv = context.active_object.mio3uv
        row = layout.row(align=True)
        row.operator(
            "mio3uv.guide_padding",
            text=tt_iface("Preview Padding"),
            icon_value=icons["OFFSET"].icon_id,
            depress=True if MIO3UV_OT_view_padding.is_running() else False,
        )
        row.operator(
            "mio3uv.guide_padding_refresh",
            text="",
            icon="FILE_REFRESH",
        )
        row = layout.row()
        row.label(text="Padding")
        row.alignment="RIGHT"
        row.scale_x=5
        row.prop(mio3uv, "padding_px", text="")
        row.scale_x=1
        row.label(text="px")

        row = layout.row()
        row.prop(mio3uv, "realtime")

classes = [MIO3UV_PT_View, MIO3UV_PT_SubGuidePadding]


def register():
    for c in classes:
        bpy.utils.register_class(c)


def unregister():
    for c in classes:
        bpy.utils.unregister_class(c)
