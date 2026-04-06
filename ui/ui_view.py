import bpy
from bpy.types import Panel
from ..operators.view_padding import UV_OT_mio3_guide_padding
from ..icons import icons
from ..globals import PADDING_AUTO


class UV_PT_mio3_Utility(Panel):
    bl_label = "Utility"
    bl_idname = "UV_PT_mio3_Utility"
    bl_space_type = "IMAGE_EDITOR"
    bl_region_type = "UI"
    bl_category = "Mio3"
    bl_options = {"DEFAULT_CLOSED"}

    @classmethod
    def poll(cls, context):
        return context.active_object is not None

    def draw(self, context):
        layout = self.layout
        col = layout.column()
        props_scene = context.scene.mio3uv

        split = col.split(factor=0.5)
        split.label(text="Size")
        split.prop(props_scene, "checker_map_size", text="")

        row = col.row(align=True)
        row.operator("mio3uv.checker_map", icon_value=icons.color_grid)
        row.operator("mio3uv.checker_map_clear", text="", icon="CANCEL")

        col.operator(
            "mio3uv.checker_map_cleanup", text="Cleanup All Checker Maps", icon="TRASH"
        )


class UV_PT_mio3_UVMesh(Panel):
    bl_label = "UV Mesh Nodes"
    bl_idname = "UV_PT_mio3_UVMesh"
    bl_space_type = "IMAGE_EDITOR"
    bl_region_type = "UI"
    bl_category = "Mio3"
    bl_parent_id = "UV_PT_mio3_Utility"
    bl_options = {"DEFAULT_CLOSED"}

    def draw(self, context):
        layout = self.layout
        layout.use_property_split = True
        layout.use_property_decorate = False
        props_object = context.active_object.mio3uv

        modifier = context.active_object.modifiers.get("Mio3UVMeshModifier")

        if modifier:
            col = layout.column(align=False)
            row = col.row(align=True)
            row.operator(
                "mesh.mio3_uvmesh_control",
                text="Mesh",
                icon_value=icons.cube,
                depress=False if props_object.uvmesh_factor > 0 else True,
            ).mode = "MESH"
            row.operator(
                "mesh.mio3_uvmesh_control",
                text="UV",
                icon_value=icons.unfoldify,
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


class UV_PT_mio3_SubGuidePadding(Panel):
    bl_label = "Padding"
    bl_idname = "UV_PT_mio3_SubGuidePadding"
    bl_space_type = "IMAGE_EDITOR"
    bl_region_type = "UI"
    bl_category = "Mio3"
    bl_parent_id = "UV_PT_mio3_Utility"
    bl_options = {"DEFAULT_CLOSED"}

    def draw(self, context):
        layout = self.layout
        col = layout.column()
        props_object = context.active_object.mio3uv

        row = col.row()
        row.prop(props_object, "image_size", text="Size")

        row = col.row(align=True)
        row.operator(
            "uv.mio3_guide_padding",
            icon_value=icons.padding,
            depress=True if UV_OT_mio3_guide_padding.is_running() else False,
        )
        row = col.row()
        row.label(text="Padding")
        row.alignment = "RIGHT"
        row.scale_x = 5
        row.prop(props_object, "padding_px", text="")
        row.scale_x = 1
        if props_object.padding_px == "AUTO":
            row.label(text=str(PADDING_AUTO.get(props_object.image_size, 16)) + "px", translate=False)
        else:
            row.label(text="px", translate=False)


classes = [UV_PT_mio3_Utility, UV_PT_mio3_UVMesh, UV_PT_mio3_SubGuidePadding]


def register():
    for c in classes:
        bpy.utils.register_class(c)


def unregister():
    for c in classes:
        bpy.utils.unregister_class(c)
