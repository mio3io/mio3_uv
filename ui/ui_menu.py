import bpy
from bpy.types import Menu
from bpy.app.translations import pgettext_iface as tt_iface
from ..icons import preview_collections


class MIO3UV_MT_unwrap(Menu):
    bl_idname = "MIO3UV_MT_unwrap"
    bl_label = "Unwrap Menu"

    def draw(self, context):
        icons = preview_collections["icons"]

        layout = self.layout
        layout.operator(
            "uv.mio3_unwrap",
            text=tt_iface("Unwrap Horizontal(U) Only"),
            icon_value=icons["EDGE_X"].icon_id,
        ).axis = "X"
        layout.operator(
            "uv.mio3_unwrap",
            text=tt_iface("Unwrap Vertical(V) Only"),
            icon_value=icons["EDGE_Y"].icon_id,
        ).axis = "Y"




classes = [
    MIO3UV_MT_unwrap,
]


def register():
    for c in classes:
        bpy.utils.register_class(c)


def unregister():
    for c in classes:
        bpy.utils.unregister_class(c)
