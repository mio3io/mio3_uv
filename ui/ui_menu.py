import bpy
from bpy.types import Menu, Panel
from ..icons import preview_collections
from bpy.app.translations import pgettext_iface as tt_iface
from ..globals import get_preferences


class MIO3UV_PT_auto_body_parts_popover(Panel):
    bl_label = "Auto Body Parts"
    bl_space_type = "IMAGE_EDITOR"
    bl_region_type = "WINDOW"
    def draw(self, context):
        icons = preview_collections["icons"]
        layout = self.layout

        col = layout.column(align=True)
        row = col.row(align=True)
        row.operator("uv.mio3_body_preset", text="Front Hair").type = "HAIR_F"
        row.operator("uv.mio3_body_preset", text="Back Hair").type = "HAIR_B"
        row = col.row(align=True)
        row.operator("uv.mio3_body_preset", text="Hand R", icon_value=icons["HAND_R"].icon_id).type = "HAND_R"
        row.operator("uv.mio3_body_preset", text="Hand L", icon_value=icons["HAND_L"].icon_id).type = "HAND_L"
        row = col.row(align=True)
        row.operator("uv.mio3_body_preset", text="Foot R", icon_value=icons["FOOT_R"].icon_id).type = "FOOT_R"
        row.operator("uv.mio3_body_preset", text="Foot L", icon_value=icons["FOOT_L"].icon_id).type = "FOOT_L"
        row = col.row(align=True)
        row.operator("uv.mio3_body_preset", text="Button").type = "BUTTON"


class MIO3UV_MT_arrange(Menu):
    bl_idname = "MIO3UV_MT_arrange"
    bl_label = "Arrange Menu"

    def draw(self, context):
        icons = preview_collections["icons"]
        layout = self.layout
        layout.operator("uv.mio3_paste", text="Unify UV Shapes", icon_value=icons["SHAPE"].icon_id).mode = "AUTO"
        layout.separator()
        layout.operator("uv.mio3_sort_grid", icon_value=icons["GRID_SORT"].icon_id)
        layout.operator("uv.mio3_unfoldify", icon_value=icons["UNFOLDIFY"].icon_id)


class MIO3UV_PT_options_popover(Panel):
    bl_label = "Options"
    bl_space_type = "IMAGE_EDITOR"
    bl_region_type = "WINDOW"
    def draw(self, context):
        pref = get_preferences()
        layout = self.layout
        props_s = context.scene.mio3uv
        # props_o = context.active_object.mio3uv
        # row = layout.row(align=True)
        # row.prop(props_o, "texture_size_x", text="")
        # row.prop(props_o, "texture_size_link", text="", icon="LINKED", toggle=True)
        # row.prop(props_o, "texture_size_y", text="")

        col = layout.column(align=True)
        col.prop(pref, "auto_uv_sync")
        col.prop(context.scene.mio3uv, "udim")
        # col.prop(pref, "ui_legacy")

        props_image = context.edit_image.mio3uv if context.edit_image is not None else context.scene.mio3uv
        split = layout.split(factor=0.4)
        split.enabled = context.edit_image is not None
        split.prop(props_image, "use_exposure")
        exposure_row = split.column()
        exposure_row.active = props_image.use_exposure
        exposure_row.prop(props_s, "exposure", text="")


classes = [
    MIO3UV_MT_arrange,
    MIO3UV_PT_auto_body_parts_popover,
    MIO3UV_PT_options_popover,
]


def register():
    for c in classes:
        bpy.utils.register_class(c)


def unregister():
    for c in classes:
        bpy.utils.unregister_class(c)
