import bpy
from bpy.types import Panel
from bpy.app.translations import pgettext_iface as tt_iface
from ..operators.view_padding import MIO3UV_OT_view_padding
from ..icons import preview_collections


class MIO3UV_PT_Utility(Panel):
    bl_label = "Utility"
    bl_idname = "MIO3UV_PT_Utility"
    bl_space_type = "IMAGE_EDITOR"
    bl_region_type = "UI"
    bl_category = "Mio3"
    bl_options = {"DEFAULT_CLOSED"}

    @classmethod
    def poll(cls, context):
        return context.active_object is not None

    def draw(self, context):
        layout = self.layout
        icons = preview_collections["icons"]
        props_scene = context.scene.mio3uv

        split = layout.split(factor=0.5)
        split.label(text="Size")
        split.prop(props_scene, "checker_map_size", text="")
        
        col = layout.column(align=True)
        row = col.row(align=True)
        row.operator("mio3uv.checker_map", icon_value=icons["COLOR_GRID"].icon_id)
        row.operator("mio3uv.checker_map_clear", text="", icon="CANCEL")

        layout.operator("mio3uv.checker_map_cleanup", text="Ceanup All Chaker Maps", icon="TRASH")


class MIO3UV_PT_UVMesh(Panel):
    bl_label = "UV Mesh Nodes"
    bl_idname = "MIO3UV_PT_UVMesh"
    bl_space_type = "IMAGE_EDITOR"
    bl_region_type = "UI"
    bl_category = "Mio3"
    bl_parent_id = "MIO3UV_PT_Utility"
    bl_options = {"DEFAULT_CLOSED"}

    def draw(self, context):
        layout = self.layout
        layout.use_property_split = True
        layout.use_property_decorate = False
        icons = preview_collections["icons"]
        props_object = context.active_object.mio3uv

        modifier = context.active_object.modifiers.get("Mio3UVMeshModifier")

        if modifier:
            col = layout.column(align=False)
            row = col.row(align=True)
            row.operator(
                "mesh.mio3_uvmesh_control",
                text=tt_iface("Mesh"),
                icon_value=icons["CUBE"].icon_id,
                depress=False if props_object.uvmesh_factor > 0 else True,
            ).mode = "MESH"
            row.operator(
                "mesh.mio3_uvmesh_control",
                text=tt_iface("UV"),
                icon_value=icons["UNFOLDIFY"].icon_id,
                depress=True if props_object.uvmesh_factor > 0 else False,
            ).mode = "UV"
            col.row().prop(props_object, "uvmesh_factor", text="Factor")
            col.row().prop(props_object, "uvmesh_size", text="Size")

            row = layout.row()
            row1 = row.row(align=True)
            row1.prop(modifier, "show_on_cage", icon_only=True)
            row1.prop(modifier, "show_in_editmode", icon_only=True)
            row1.prop(modifier, "show_viewport", icon_only=True)

            row2 = row.row(align=True)
            row2.operator("mesh.mio3_uvmesh_clear", text="Remove", icon="CANCEL")
        else:
            layout.operator("mesh.mio3_uvmesh")
            row = layout.row()
            row.alignment = "CENTER"
            row.label(text="Add Modifier")


class MIO3UV_PT_SubGuidePadding(Panel):
    bl_label = "Padding"
    bl_idname = "MIO3UV_PT_SubGuidePadding"
    bl_space_type = "IMAGE_EDITOR"
    bl_region_type = "UI"
    bl_category = "Mio3"
    bl_parent_id = "MIO3UV_PT_Utility"
    bl_options = {"DEFAULT_CLOSED"}

    def draw(self, context):
        icons = preview_collections["icons"]
        layout = self.layout
        props_object = context.active_object.mio3uv

        row = layout.row()
        row.prop(props_object, "image_size", text="Size")

        row = layout.row(align=True)
        row.operator(
            "uv.mio3_guide_padding",
            icon_value=icons["OFFSET"].icon_id,
            depress=True if MIO3UV_OT_view_padding.is_running() else False,
        )
        row.operator(
            "uv.mio3_guide_padding_refresh",
            text="",
            icon="FILE_REFRESH",
        )
        row = layout.row()
        row.label(text="Padding")
        row.alignment = "RIGHT"
        row.scale_x = 5
        row.prop(props_object, "padding_px", text="")
        row.scale_x = 1
        row.label(text="px")

        row = layout.row()
        row.prop(props_object, "realtime")


classes = [MIO3UV_PT_Utility, MIO3UV_PT_UVMesh, MIO3UV_PT_SubGuidePadding]


def register():
    for c in classes:
        bpy.utils.register_class(c)


def unregister():
    for c in classes:
        bpy.utils.unregister_class(c)
