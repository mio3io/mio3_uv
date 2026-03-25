import bpy
from ..icons import icons
from ..classes.operator import Mio3UVPanel
from ..globals import get_preferences


class MIO3UV_PT_main(Mio3UVPanel):
    bl_label = "Mio3 UV"
    bl_idname = "MIO3UV_PT_main"
    bl_space_type = "IMAGE_EDITOR"
    bl_region_type = "UI"
    bl_category = "Mio3"

    def draw_header(self, context):
        self.layout.label(icon_value=icons.unwrap)

    def draw(self, context):
        layout = self.layout
        col = layout.column()

        row = col.row(align=True)
        row.prop(context.space_data, "pivot_point", icon_only=True, expand=True)

        row2 = row.row(align=False)
        row2.alignment = "RIGHT"

        row3 = row.row(align=True)
        row3.operator("uv.snap_cursor", text="", icon="CURSOR").target="SELECTED"
        # row3.operator("ed.undo", text="", icon="LOOP_BACK")
        row3.separator(factor=0.5)
        row3.operator("uv.mio3_pin", text="", icon="PINNED").clear = False
        row3.operator("uv.mio3_pin", text="", icon="UNPINNED").clear = True
        row3.separator(factor=0.5)
        row3.popover("MIO3UV_PT_options_popover", text="", icon="PREFERENCES")

        col_unwrap = col.column(align=True)
        col_unwrap.scale_y = 1.1

        row = col_unwrap.row(align=True)
        row.operator("uv.mio3_unwrap", text="Unwrap", icon_value=icons.unwrap).axis = "BOTH"
        row.scale_x=0.14
        row.operator("uv.mio3_unwrap", text="X").axis = "X"
        row.operator("uv.mio3_unwrap", text="Y").axis = "Y"
        row.scale_x=1
        row.separator(factor=0.2)
        row.operator("uv.mio3_unwrap_mirrored", text="", icon="MOD_MIRROR")

        col_unwrap = col.column(align=True)

        row = col_unwrap.row(align=True)
        row.operator("uv.mio3_normalize", icon_value=icons.normalize)
        row.operator("uv.mio3_straight", icon_value=icons.straight).type = "GEOMETRY"
        row = col_unwrap.row(align=True)
        row.operator("uv.mio3_gridify", icon_value=icons.grid)
        row.operator("uv.mio3_rectify", icon_value=icons.rectify)


class MIO3UV_PT_align(Mio3UVPanel):
    bl_label = "Layout"
    bl_idname = "MIO3UV_PT_align"
    bl_space_type = "IMAGE_EDITOR"
    bl_region_type = "UI"
    bl_category = "Mio3"

    def draw(self, context):
        # pref = get_preferences()
        # props_scene = context.scene.mio3uv
        layout = self.layout
        col = layout.column()

        split = col.row(align=True)
        col_left = split.column()
        # col_left.scale_y = 1.1
        grid = col_left.grid_flow(row_major=True, columns=3, even_columns=True, even_rows=True, align=True)
        grid.operator("uv.mio3_align", text="", icon_value=icons.align_top_left).type = "MAX_Y_MIN_X"
        grid.operator("uv.mio3_align", text="", icon_value=icons.align_top).type = "MAX_Y"
        grid.operator("uv.mio3_align", text="", icon_value=icons.align_top_right).type = "MAX_Y_MAX_X"
        grid.operator("uv.mio3_align", text="", icon_value=icons.align_left).type = "MIN_X"
        dummy = grid.row(align=True)
        dummy.scale_x = 3
        dummy.operator("uv.mio3_align", text="", icon_value=icons.align_center).type = "CENTER"
        grid.operator("uv.mio3_align", text="", icon_value=icons.align_right).type = "MAX_X"
        grid.operator("uv.mio3_align", text="", icon_value=icons.align_bottom_left).type = "MIN_Y_MIN_X"
        grid.operator("uv.mio3_align", text="", icon_value=icons.align_bottom).type = "MIN_Y"
        grid.operator("uv.mio3_align", text="", icon_value=icons.align_bottom_right).type = "MIN_Y_MAX_X"

        split.separator(factor=0.4)
        split.scale_x = 0.8

        # Right
        col_right = split.column(align=True)
        col_right.scale_y = 1.1

        row = col_right.row(align=True)
        row.scale_x = 2.5
        row.operator("uv.mio3_align", text="", icon_value=icons.align_y_center).type = "ALIGN_Y"
        row.operator("uv.mio3_align", text="", icon_value=icons.align_x_center).type = "ALIGN_X"
        row = col_right.row(align=True)
        row.scale_x = 2.5
        row.operator("uv.mio3_align_edges", text="", icon_value=icons.edges_x).axis = "X"
        row.operator("uv.mio3_align_edges", text="", icon_value=icons.edges_y).axis = "Y"
        row = col_right.row(align=True)
        row.scale_x = 2.5
        row.operator("uv.mio3_mirror", text="", icon_value=icons.flip_y).axis="Y"
        row.operator("uv.mio3_mirror", text="", icon_value=icons.flip_x).axis="X"

        col_rotate = col.column(align=True)
        col_rotate.scale_y = 1.05

        row = col_rotate.row(align=True)
        row.operator("uv.mio3_rotate", text="90", icon_value=icons.p90).angle = -1.5708
        row.operator("uv.mio3_rotate", text="180", icon_value=icons.p180).angle = 3.14159
        row.operator("uv.mio3_rotate", text="90", icon_value=icons.n90).angle = 1.5708

        row = col_rotate.row(align=True)
        row.operator("uv.mio3_orient", icon_value=icons.orient)
        row.operator("uv.mio3_orient_world", text="Orient World", icon_value=icons.z).axis = "Z"

        row = col_rotate.row(align=True)
        row.operator("uv.mio3_sort", icon_value=icons.align_x)
        row.operator("uv.mio3_distribute", icon_value=icons.dist_x)

        col = col.column()
        row = col.row(align=True)
        row.operator("uv.mio3_relax", icon_value=icons.relax)
        row.operator("uv.mio3_stack", icon_value=icons.stack)

        row = col.row(align=True)
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
        layout = self.layout
        col = layout.column()

        col_vert = col.column(align=True)
        col_vert.scale_y = 1.05
        row = col_vert.row(align=True)
        row.operator("uv.mio3_align_seam", icon_value=icons.align_seam_y)
        row.operator("uv.mio3_merge", icon_value=icons.merge)

        row = col_vert.row(align=True)
        row.operator("uv.mio3_circle", icon_value=icons.circle)
        row.operator("uv.mio3_offset", icon_value=icons.offset)

        col_iisland = col.column(align=True)
        col_iisland.scale_y = 1.05

        row = col_iisland.row(align=True)
        row.operator("uv.copy", text="Copy", icon_value=icons.copy)
        row.operator("uv.mio3_paste", icon_value=icons.paste).mode = "PASTE"
        row = col_iisland.row(align=True)
        row.operator("uv.mio3_stretch", icon_value=icons.stretch)
        row.operator("uv.mio3_shuffle_island", icon_value=icons.shuffle)

        row = col_iisland.row(align=True)
        row.operator("uv.mio3_stitch", icon_value=icons.stitch)
        row.operator("uv.mio3_unfoldify", icon_value=icons.unfoldify)
        
        row = col_iisland.row(align=True)
        row.operator("uv.average_islands_scale", text="Average Island Scales", icon_value=icons.cube)
        row = col.row(align=True)
        row.operator("uv.mio3_body_preset", icon_value=icons.body).type = "AUTO"
        row.popover("MIO3UV_PT_auto_body_parts_popover", text="", icon="DOWNARROW_HLT")


class MIO3UV_PT_symmetry(Mio3UVPanel):
    bl_label = "Symmetrize"
    bl_idname = "MIO3UV_PT_symmetry"
    bl_space_type = "IMAGE_EDITOR"
    bl_region_type = "UI"
    bl_category = "Mio3"

    def draw(self, context):
        layout = self.layout
        col = layout.column()
        row = col.row(align=True)
        row.scale_y = 1.15
        row.operator("uv.mio3_symmetrize", icon_value=icons.symmetrize)
        row.operator("uv.mio3_symmetry_snap", icon_value=icons.snap)
        row_option = col.row()
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
        layout = self.layout
        col = layout.column()

        col2 = col.column(align=True)
        row = col2.row(align=True)
        row.operator("uv.mio3_select_half", text="-X", icon_value=icons.x_n)
        row.operator("uv.mio3_select_half", text="+X", icon_value=icons.x_p)
        row.scale_x = 1.3
        row.operator("uv.mio3_select_mirror3d", icon_value=icons.mirror_uv)
        row = col2.row(align=True)
        row.operator("uv.mio3_select_similar", icon_value=icons.similar)
        row.operator("uv.mio3_select_boundary", icon_value=icons.boundary)
        row = col2.row(align=True)
        row.operator("uv.mio3_select_edge_direction", text="Horizontal", icon_value=icons.edges_x).axis = "X"
        row.operator("uv.mio3_select_edge_direction", text="Vertical", icon_value=icons.edges_y).axis = "Y"

        row = col.row(align=True)
        row.label(text="Odd UVs")
        row.operator("uv.mio3_select_zero")
        row.operator("uv.mio3_select_flipped_faces")


classes = [
    MIO3UV_PT_main,
    MIO3UV_PT_align,
    MIO3UV_PT_symmetry,
    MIO3UV_PT_arrange,
    MIO3UV_PT_select,
]


def register():
    for c in classes:
        bpy.utils.register_class(c)


def unregister():
    for c in classes:
        bpy.utils.unregister_class(c)
