import bpy
from bpy.app.translations import pgettext_iface as tt_iface
from ..icons import preview_collections
from ..classes.operator import Mio3UVPanel


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

        if context.edit_image is not None:
            mio3uv_image = context.edit_image.mio3uv
            row2.prop(mio3uv_image, "use_exposure", text="", icon="NODE_TEXTURE", toggle=True)
        row3 = row.row(align=True)
        row3.operator("uv.pin", text="", icon="PINNED").clear = False
        row3.operator("uv.pin", text="", icon="UNPINNED").clear = True

        col_unwrap = layout.column(align=True)
        col_unwrap.scale_y = 1.1

        row = col_unwrap.row(align=True)
        row.operator("uv.mio3_unwrap", text="Unwrap", icon_value=icons["UNWRAP"].icon_id)
        op = row.operator("uv.mio3_straight", text=tt_iface("Straight"), icon_value=icons["STRAIGHT"].icon_id)
        op.distribute = "GEOMETRY"
        row = col_unwrap.row(align=True)
        row.operator("uv.mio3_gridify", text=tt_iface("Gridify"), icon_value=icons["GRID"].icon_id)
        row.operator("uv.mio3_rectify", text=tt_iface("Rectify"), icon_value=icons["RECTIFY"].icon_id)


class MIO3UV_PT_align(Mio3UVPanel):
    bl_label = "Align"
    bl_idname = "MIO3UV_PT_align"
    bl_space_type = "IMAGE_EDITOR"
    bl_region_type = "UI"
    bl_category = "Mio3"

    def draw(self, context):
        icons = preview_collections["icons"]
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
        row.operator("uv.mio3_align", text="", icon_value=icons["ALIGN_X_CENTER"].icon_id).type = "ALIGN_X"
        row.operator("uv.mio3_align", text="", icon_value=icons["ALIGN_Y_CENTER"].icon_id).type = "ALIGN_Y"
        row = col_right.row(align=True)
        row.scale_x = 3
        row.operator("uv.mio3_align_edges", text="", icon_value=icons["EDGE_Y"].icon_id).axis = "Y"
        row.operator("uv.mio3_align_edges", text="", icon_value=icons["EDGE_X"].icon_id).axis = "X"

        row = col_right.row(align=True)
        row.scale_x = 3
        row.operator_context = "EXEC_REGION_WIN"
        row.operator("transform.mirror", text="", icon_value=icons["FLIP_X"].icon_id).constraint_axis = (
            True,
            False,
            False,
        )
        row.operator("transform.mirror", text="", icon_value=icons["FLIP_Y"].icon_id).constraint_axis = (
            False,
            True,
            False,
        )
        row.operator_context = "INVOKE_DEFAULT"

        col_rotate = layout.column(align=True)
        col_rotate.scale_y = 1.1

        row = col_rotate.row(align=True)
        row.operator("uv.mio3_rotate", text=tt_iface("90"), icon_value=icons["P90"].icon_id).angle = -1.5708
        row.operator("uv.mio3_rotate", text=tt_iface("180"), icon_value=icons["P180"].icon_id).angle = 3.14159
        row.operator("uv.mio3_rotate", text=tt_iface("90"), icon_value=icons["N90"].icon_id).angle = 1.5708

        row = col_rotate.row(align=True)
        row.operator("uv.align_rotation", text=tt_iface("Align Axis"), icon_value=icons["ROTATE"].icon_id).method = (
            "AUTO"
        )
        op = row.operator("uv.align_rotation", text=tt_iface("Orient World"), icon_value=icons["Z"].icon_id)
        op.method = "GEOMETRY"
        op.axis = "Z"

        row = col_rotate.row(align=True)
        row.operator("uv.mio3_orient_edge", text=tt_iface("Orient Edge"), icon_value=icons["ALIGN_EDGE"].icon_id)
        row.operator("uv.mio3_normalize", text=tt_iface("Normalize"), icon_value=icons["NORMALIZE"].icon_id)

        row = col_rotate.row(align=True)
        row.operator("uv.mio3_align_seam", text=tt_iface("Align Seam"), icon_value=icons["ALIGN_SEAM_Y"].icon_id)

        row = layout.row(align=True)
        row.label(text=tt_iface("Fixed Mode"))
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

        layout.label(text="Vertex", icon_value=icons["VERT"].icon_id)

        col_vert = layout.column(align=True)
        col_vert.scale_y = 1.2
        row = col_vert.row(align=True)
        row.operator("uv.mio3_relax", text=tt_iface("Relax"), icon_value=icons["RELAX"].icon_id)
        row.operator("uv.mio3_adjust_edge", text=tt_iface("Adjust Length"), icon_value=icons["LENGTH"].icon_id)

        row = col_vert.row(align=True)
        row.operator("uv.mio3_circle", text=tt_iface("Circle"), icon_value=icons["CIRCLE"].icon_id)
        row.operator("uv.mio3_offset", text=tt_iface("Offset"), icon_value=icons["OFFSET"].icon_id)

        layout.label(text="Island", icon_value=icons["ISLAND"].icon_id)

        col_iisland = layout.column(align=True)
        col_iisland.scale_y = 1.2

        row = col_iisland.row(align=True)
        row.operator("uv.mio3_stack", text=tt_iface("Stack"), icon_value=icons["STACK"].icon_id)
        row.operator("uv.mio3_sort", text=tt_iface("Sort"), icon_value=icons["ALIGN_X"].icon_id)

        row = col_iisland.row(align=True)
        row.operator("uv.copy", text=tt_iface("Copy"), icon_value=icons["COPY"].icon_id)
        row.operator("uv.mio3_paste", text=tt_iface("Paste"), icon_value=icons["PASTE"].icon_id).mode = "PASTE"

        row = col_iisland.row(align=True)
        row.operator("uv.mio3_stitch", text=tt_iface("Stitch"), icon_value=icons["STITCH"].icon_id)
        row.operator("uv.mio3_shuffle_island", text=tt_iface("Shuffle"), icon_value=icons["SHUFFLE"].icon_id)

        row = col_iisland.row(align=True)
        row.operator("uv.mio3_paste", text=tt_iface("Unify Shapes"), icon_value=icons["SHAPE"].icon_id).mode = "AUTO"
        row = col_iisland.row(align=True)
        row.operator("uv.average_islands_scale", text=tt_iface("Average Island Scales"), icon_value=icons["CUBE"].icon_id)


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
        row.operator("uv.mio3_symmetrize", text=tt_iface("Symmetrize"), icon_value=icons["SYMMETRIZE"].icon_id)
        row.operator("uv.mio3_symmetry_snap", text=tt_iface("Snap"), icon_value=icons["SNAP"].icon_id)
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
        row.operator("uv.mio3_select_mirror3d", text=tt_iface("Mirror"), icon_value=icons["MIRROR_UV"].icon_id)

        row = col.row(align=True)
        row.operator("uv.mio3_select_similar", text=tt_iface("Similar"), icon_value=icons["SIMILAR"].icon_id)
        row.operator("uv.mio3_select_boundary", text=tt_iface("Boundary"), icon_value=icons["BOUND"].icon_id)
        row = col.row(align=True)

        row.operator(
            "uv.mio3_select_edge_direction", text=tt_iface("Vertical"), icon_value=icons["EDGE_Y"].icon_id
        ).axis = "Y"
        row.operator(
            "uv.mio3_select_edge_direction", text=tt_iface("Horizontal"), icon_value=icons["EDGE_X"].icon_id
        ).axis = "X"

        row = layout.row(align=True)
        row.label(text=tt_iface("Odd UVs"))
        row.operator("uv.mio3_select_zero", text=tt_iface("No region"))
        row.operator("uv.mio3_select_flipped_faces", text=tt_iface("Flipped"))


class MIO3UV_PT_rearrange(Mio3UVPanel):
    bl_label = "Rearrange"
    bl_idname = "MIO3UV_PT_rearrange"
    bl_space_type = "IMAGE_EDITOR"
    bl_region_type = "UI"
    bl_category = "Mio3"
    bl_options = {"DEFAULT_CLOSED"}
    bl_parent_id = "MIO3UV_PT_arrange"

    def draw(self, context):
        icons = preview_collections["icons"]
        layout = self.layout

        layout.label(text="Group Rearrange", icon_value=icons["UNSTACK"].icon_id)
        col = layout.column(align=True)
        col.scale_y = 1.1

        row = col.row(align=True)
        row.operator("uv.mio3_sort_grid", text=tt_iface("Grid Sort"), icon_value=icons["GRID_SORT"].icon_id)

        row = col.row(align=True)
        row.operator("uv.mio3_unfoldify", text=tt_iface("Unfoldify"), icon_value=icons["UNFOLDIFY"].icon_id)

        layout.label(text="Body Preset", icon_value=icons["ROTATE"].icon_id)
        layout = self.layout
        row = layout.row(align=True)
        row.operator("uv.mio3_body_preset", text=tt_iface("Auto Body Parts"), icon_value=icons["BODY"].icon_id).type = (
            "AUTO"
        )

        col = layout.column(align=True)

        row = col.row(align=True)
        row.operator("uv.mio3_body_preset", text=tt_iface("Front Hair")).type = "HAIR_F"
        row.operator("uv.mio3_body_preset", text=tt_iface("Back Hair")).type = "HAIR_B"

        row = col.row(align=True)
        row.operator("uv.mio3_body_preset", text=tt_iface("Hand R"), icon_value=icons["HAND_R"].icon_id).type = "HAND_R"
        row.operator("uv.mio3_body_preset", text=tt_iface("Hand L"), icon_value=icons["HAND_L"].icon_id).type = "HAND_L"

        row = col.row(align=True)
        row.operator("uv.mio3_body_preset", text=tt_iface("Foot R"), icon_value=icons["FOOT_R"].icon_id).type = "FOOT_R"
        row.operator("uv.mio3_body_preset", text=tt_iface("Foot L"), icon_value=icons["FOOT_L"].icon_id).type = "FOOT_L"

        row = col.row(align=True)
        row.operator("uv.mio3_body_preset", text=tt_iface("Button")).type = "BUTTON"


classes = [
    MIO3UV_PT_main,
    MIO3UV_PT_align,
    MIO3UV_PT_arrange,
    MIO3UV_PT_symmetry,
    MIO3UV_PT_select,
    MIO3UV_PT_rearrange,
    # MIO3UV_PT_body_preset,
]


def register():
    for c in classes:
        bpy.utils.register_class(c)


def unregister():
    for c in classes:
        bpy.utils.unregister_class(c)
