import bpy
from ..icons import preview_collections
from ..classes.operator import Mio3UVPanel
from ..globals import get_preferences


class MIO3UV_PT_main(Mio3UVPanel):
    bl_label = "Mio3 UV"
    bl_idname = "MIO3UV_PT_main"
    bl_space_type = "IMAGE_EDITOR"
    bl_region_type = "UI"
    bl_category = "Mio3"

    def draw_header(self, context):
        icons = preview_collections["icons"]
        self.layout.label(icon_value=icons["UNWRAP2"].icon_id)

    def draw(self, context):
        icons = preview_collections["icons"]
        layout = self.layout

        row = layout.row(align=True)
        row.prop(context.space_data, "pivot_point", icon_only=True, expand=True)

        row2 = row.row(align=False)
        row2.alignment = "RIGHT"

        row3 = row.row(align=True)
        row3.operator("uv.mio3_pin", text="", icon="PINNED")
        row3.separator()
        row3.popover("MIO3UV_PT_options_popover", text="", icon="PREFERENCES")

        col_unwrap = layout.column(align=True)
        col_unwrap.scale_y = 1.1

        row = col_unwrap.row(align=True)
        row.operator("uv.mio3_unwrap", text="Unwrap", icon_value=icons["UNWRAP"].icon_id).axis = "BOTH"
        row.scale_x=0.14
        row.operator("uv.mio3_unwrap", text="X").axis = "X"
        row.operator("uv.mio3_unwrap", text="Y").axis = "Y"
        row.scale_x=1

        col_unwrap = layout.column(align=True)

        row = col_unwrap.row(align=True)
        row.operator("uv.mio3_normalize", icon_value=icons["NORMALIZE"].icon_id)
        row.operator("uv.mio3_straight", icon_value=icons["STRAIGHT"].icon_id).type = "GEOMETRY"
        row = col_unwrap.row(align=True)
        row.operator("uv.mio3_gridify", icon_value=icons["GRID"].icon_id)
        row.operator("uv.mio3_rectify", icon_value=icons["RECTIFY"].icon_id)


class MIO3UV_PT_align(Mio3UVPanel):
    bl_label = "Align"
    bl_idname = "MIO3UV_PT_align"
    bl_space_type = "IMAGE_EDITOR"
    bl_region_type = "UI"
    bl_category = "Mio3"

    def draw(self, context):
        # pref = get_preferences()
        icons = preview_collections["icons"]
        # props_scene = context.scene.mio3uv
        layout = self.layout


        split = layout.split(factor=0.5)
        col_left = split.column()
        col_left.scale_y = 1.1
        grid = col_left.grid_flow(row_major=True, columns=3, even_columns=True, even_rows=True, align=True)
        grid.label(text="")
        grid.operator("uv.mio3_align", text="", icon_value=icons["ALIGN_T"].icon_id).type = "MAX_Y"
        grid.label(text="")
        grid.operator("uv.mio3_align", text="", icon_value=icons["ALIGN_L"].icon_id).type = "MIN_X"
        dummy = grid.row(align=True)
        dummy.scale_x = 3
        dummy.operator("uv.mio3_align", text="", icon_value=icons["ALIGN_CENTER"].icon_id).type = "CENTER"
        grid.operator("uv.mio3_align", text="", icon_value=icons["ALIGN_R"].icon_id).type = "MAX_X"
        grid.label(text="")
        grid.operator("uv.mio3_align", text="", icon_value=icons["ALIGN_B"].icon_id).type = "MIN_Y"

        # Right
        col_right = split.column(align=True)
        col_right.scale_y = 1.14

        row = col_right.row(align=True)
        row.scale_x = 3
        row.operator("uv.mio3_align", text="", icon_value=icons["ALIGN_Y_CENTER"].icon_id).type = "ALIGN_Y"
        row.operator("uv.mio3_align", text="", icon_value=icons["ALIGN_X_CENTER"].icon_id).type = "ALIGN_X"
        row = col_right.row(align=True)
        row.scale_x = 3
        row.operator("uv.mio3_align_edges", text="", icon_value=icons["EDGE_X"].icon_id).axis = "X"
        row.operator("uv.mio3_align_edges", text="", icon_value=icons["EDGE_Y"].icon_id).axis = "Y"
        row = col_right.row(align=True)
        row.scale_x = 3
        row.operator("uv.mio3_mirror", text="", icon_value=icons["FLIP_Y"].icon_id).axis="Y"
        row.operator("uv.mio3_mirror", text="", icon_value=icons["FLIP_X"].icon_id).axis="X"


        col_rotate = layout.column(align=True)
        col_rotate.scale_y = 1.1

        row = col_rotate.row(align=True)
        row.operator("uv.mio3_rotate", text="90", icon_value=icons["P90"].icon_id).angle = -1.5708
        row.operator("uv.mio3_rotate", text="180", icon_value=icons["P180"].icon_id).angle = 3.14159
        row.operator("uv.mio3_rotate", text="90", icon_value=icons["N90"].icon_id).angle = 1.5708

        row = col_rotate.row(align=True)
        op = row.operator("uv.align_rotation", text="Orient World", icon_value=icons["Z"].icon_id)
        op.method = "GEOMETRY"
        op.axis = "Z"

        row = col_rotate.row(align=True)
        row.operator("uv.mio3_orient", icon_value=icons["ROTATE"].icon_id)
        row.operator("uv.mio3_align_seam", icon_value=icons["ALIGN_SEAM_Y"].icon_id)

        row = col_rotate.row(align=True)
        row.operator("uv.mio3_stretch", icon_value=icons["STRATCH"].icon_id)
        row.operator("uv.mio3_distribute", icon_value=icons["DIST_X"].icon_id)

        row = layout.row(align=True)
        row.label(text="Fixed Mode")
        row.scale_x = 0.7
        row.prop(context.scene.mio3uv, "edge_mode", text="Edge", toggle=True)
        row.scale_x = 1.1
        row.prop(context.scene.mio3uv, "island_mode", text="Island", toggle=True)


class MIO3UV_PT_arrange(Mio3UVPanel):
    bl_label = "Arrange"
    bl_idname = "MIO3UV_PT_arrange"
    bl_space_type = "IMAGE_EDITOR"
    bl_region_type = "UI"
    bl_category = "Mio3"

    def draw(self, context):
        icons = preview_collections["icons"]
        layout = self.layout

        # Vertex
        # layout.label(text="Vertex", icon_value=icons["VERT"].icon_id)

        col_vert = layout.column(align=True)
        col_vert.scale_y = 1.2
        row = col_vert.row(align=True)
        row.operator("uv.mio3_relax", icon_value=icons["RELAX"].icon_id)
        row.operator("uv.mio3_merge", icon_value=icons["VERT"].icon_id)

        row = col_vert.row(align=True)
        row.operator("uv.mio3_circle", icon_value=icons["CIRCLE"].icon_id)
        row.operator("uv.mio3_offset", icon_value=icons["OFFSET"].icon_id)

        # Island
        row = layout.row()
        row.label(text="Island", icon_value=icons["ISLAND"].icon_id)
        row.menu("MIO3UV_MT_arrange", text="", icon="DOWNARROW_HLT")

        col_iisland = layout.column(align=True)
        col_iisland.scale_y = 1.2

        row = col_iisland.row(align=True)
        row.operator("uv.mio3_stack", icon_value=icons["STACK"].icon_id)
        row.operator("uv.mio3_sort", icon_value=icons["ALIGN_X"].icon_id)
        row = col_iisland.row(align=True)
        row.operator("uv.copy", text="Copy", icon_value=icons["COPY"].icon_id)
        row.operator("uv.mio3_paste", icon_value=icons["PASTE"].icon_id).mode = "PASTE"
        row = col_iisland.row(align=True)
        row.operator("uv.mio3_stitch", icon_value=icons["STITCH"].icon_id)
        row.operator("uv.mio3_shuffle_island", icon_value=icons["SHUFFLE"].icon_id)
        row = col_iisland.row(align=True)
        row.operator("uv.average_islands_scale", text="Average Island Scales", icon_value=icons["CUBE"].icon_id)
        col = layout.column(align=True)
        row = col.row(align=True)
        row.operator("uv.mio3_body_preset", icon_value=icons["BODY"].icon_id).type = "AUTO"
        row.popover("MIO3UV_PT_auto_body_parts_popover", text="", icon="DOWNARROW_HLT")


class MIO3UV_PT_symmetry(Mio3UVPanel):
    bl_label = "Symmetrize"
    bl_idname = "MIO3UV_PT_symmetry"
    bl_space_type = "IMAGE_EDITOR"
    bl_region_type = "UI"
    bl_category = "Mio3"

    def draw(self, context):
        icons = preview_collections["icons"]
        layout = self.layout
        row = layout.row(align=True)
        row.scale_y = 1
        row.prop(context.scene.mio3uv, "symmetry_center", expand=True)
        row = layout.row(align=True)
        row.scale_y = 1.2
        row.operator("uv.mio3_symmetrize", icon_value=icons["SYMMETRIZE"].icon_id)
        row.operator("uv.mio3_symmetry_snap", icon_value=icons["SNAP"].icon_id)
        row_option = layout.row()
        row_option.scale_y = 1.1
        row = row_option.row(align=True)
        row.scale_x = 2
        row.prop(context.scene.mio3uv, "symmetry_uv_axis", expand=True)
        row = row_option.row(align=True)
        row.scale_x = 0.1
        row.label(text="3D")
        row.scale_x = 2
        row.prop(context.scene.mio3uv, "symmetry_3d_axis", text="")


class MIO3UV_PT_select(Mio3UVPanel):
    bl_label = "Select"
    bl_idname = "MIO3UV_PT_select"
    bl_space_type = "IMAGE_EDITOR"
    bl_region_type = "UI"
    bl_category = "Mio3"

    def draw(self, context):
        icons = preview_collections["icons"]
        layout = self.layout

        col = layout.column(align=True)
        col.scale_y = 1.1

        row = col.row(align=True)
        row.operator("uv.mio3_select_half", text="-X", icon_value=icons["X_N"].icon_id).direction = "NEGATIVE_X"
        row.operator("uv.mio3_select_half", text="+X", icon_value=icons["X_P"].icon_id).direction = "POSITIVE_X"
        row.scale_x = 1.3
        row.operator("uv.mio3_select_mirror3d", icon_value=icons["MIRROR_UV"].icon_id)

        row = col.row(align=True)
        row.operator("uv.mio3_select_similar", icon_value=icons["SIMILAR"].icon_id)
        row.operator("uv.mio3_select_boundary", icon_value=icons["BOUND"].icon_id)
        row = col.row(align=True)

        row.operator("uv.mio3_select_edge_direction", text="Horizontal", icon_value=icons["EDGE_X"].icon_id).axis = "X"
        row.operator("uv.mio3_select_edge_direction", text="Vertical", icon_value=icons["EDGE_Y"].icon_id).axis = "Y"

        row = layout.row(align=True)
        row.label(text="Odd UVs")
        row.operator("uv.mio3_select_zero")
        row.operator("uv.mio3_select_flipped_faces")


classes = [
    MIO3UV_PT_main,
    MIO3UV_PT_align,
    MIO3UV_PT_arrange,
    MIO3UV_PT_symmetry,
    MIO3UV_PT_select,
]


def register():
    for c in classes:
        bpy.utils.register_class(c)


def unregister():
    for c in classes:
        bpy.utils.unregister_class(c)
