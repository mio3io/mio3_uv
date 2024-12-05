import bpy
from bpy.types import Menu, Panel
from ..icons import preview_collections


class MIO3UV_MT_unwrap(Menu):
    bl_idname = "MIO3UV_MT_unwrap"
    bl_label = "Unwrap Menu"

    def draw(self, context):
        icons = preview_collections["icons"]

        layout = self.layout
        layout.operator(
            "uv.mio3_unwrap",
            text="Unwrap Horizontal(X) Only",
            icon_value=icons["EDGE_X"].icon_id,
        ).axis = "X"
        layout.operator(
            "uv.mio3_unwrap",
            text="Unwrap Vertical(Y) Only",
            icon_value=icons["EDGE_Y"].icon_id,
        ).axis = "Y"


class MIO3UV_PT_auto_body_parts_popover(Panel):
    bl_label = "Auto Body Parts"
    bl_space_type = "VIEW_3D"
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


classes = [
    MIO3UV_MT_unwrap,
    MIO3UV_PT_auto_body_parts_popover
]


def register():
    for c in classes:
        bpy.utils.register_class(c)


def unregister():
    for c in classes:
        bpy.utils.unregister_class(c)
