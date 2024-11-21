import os
import bpy


ICON_DIR = os.path.join(os.path.dirname(__file__), "icons")

preview_collections = {}


def register():
    import bpy.utils.previews

    icons = bpy.utils.previews.new()
    icons.load("UNWRAP", os.path.join(ICON_DIR, "unwrap.png"), "IMAGE")
    icons.load("UNWRAP2", os.path.join(ICON_DIR, "unwrap2.png"), "IMAGE")
    icons.load("RECTIFY", os.path.join(ICON_DIR, "rectify.png"), "IMAGE")
    icons.load("GRID", os.path.join(ICON_DIR, "grid.png"), "IMAGE")
    icons.load("STRAIGHT", os.path.join(ICON_DIR, "straight.png"), "IMAGE")
    icons.load("HIGHLIGHT", os.path.join(ICON_DIR, "highlight.png"), "IMAGE")

    icons.load("ISLAND", os.path.join(ICON_DIR, "island.png"), "IMAGE")
    icons.load("VERT", os.path.join(ICON_DIR, "vert.png"), "IMAGE")

    icons.load("ALIGN_EDGE", os.path.join(ICON_DIR, "align_edge.png"), "IMAGE")

    icons.load("ALIGN_X_CENTER", os.path.join(ICON_DIR, "align_x_center.png"), "IMAGE")
    icons.load("ALIGN_Y_CENTER", os.path.join(ICON_DIR, "align_y_center.png"), "IMAGE")
    icons.load("ALIGN_SEAM_Y", os.path.join(ICON_DIR, "align_seam_y.png"), "IMAGE")
    icons.load("ALIGN_X", os.path.join(ICON_DIR, "align_x.png"), "IMAGE")
    icons.load("ALIGN_Y", os.path.join(ICON_DIR, "align_y.png"), "IMAGE")
    icons.load("ALIGN_CENTER", os.path.join(ICON_DIR, "align_center.png"), "IMAGE")
    icons.load("ALIGN_T", os.path.join(ICON_DIR, "align_top.png"), "IMAGE")
    icons.load("ALIGN_B", os.path.join(ICON_DIR, "align_bottom.png"), "IMAGE")
    icons.load("ALIGN_L", os.path.join(ICON_DIR, "align_left.png"), "IMAGE")
    icons.load("ALIGN_R", os.path.join(ICON_DIR, "align_right.png"), "IMAGE")
    icons.load("Z", os.path.join(ICON_DIR, "z.png"), "IMAGE")
    icons.load("NORMALIZE", os.path.join(ICON_DIR, "normalize.png"), "IMAGE")

    icons.load("FLIP_Y", os.path.join(ICON_DIR, "flip_y.png"), "IMAGE")
    icons.load("FLIP_X", os.path.join(ICON_DIR, "flip_x.png"), "IMAGE")

    icons.load("X_N", os.path.join(ICON_DIR, "x_n.png"), "IMAGE")
    icons.load("X_P", os.path.join(ICON_DIR, "x_p.png"), "IMAGE")

    icons.load("SIMILAR", os.path.join(ICON_DIR, "similar.png"), "IMAGE")
    icons.load("UNFOLDIFY", os.path.join(ICON_DIR, "unfoldify.png"), "IMAGE")
    icons.load("SYMMETRIZE", os.path.join(ICON_DIR, "symmetrize.png"), "IMAGE")

    icons.load("N90", os.path.join(ICON_DIR, "n90.png"), "IMAGE")
    icons.load("P90", os.path.join(ICON_DIR, "p90.png"), "IMAGE")
    icons.load("P180", os.path.join(ICON_DIR, "p180.png"), "IMAGE")
    icons.load("ROTATE", os.path.join(ICON_DIR, "align_rotate.png"), "IMAGE")

    icons.load("STACK", os.path.join(ICON_DIR, "stack.png"), "IMAGE")
    icons.load("DIST_X", os.path.join(ICON_DIR, "dist_x.png"), "IMAGE")
    icons.load("DIST_Y", os.path.join(ICON_DIR, "dist_y.png"), "IMAGE")

    icons.load("GRID_SORT", os.path.join(ICON_DIR, "grid_sorting.png"), "IMAGE")

    icons.load("SEAM", os.path.join(ICON_DIR, "seam.png"), "IMAGE")
    icons.load("RELAX", os.path.join(ICON_DIR, "relax.png"), "IMAGE")
    icons.load("COPY", os.path.join(ICON_DIR, "copy.png"), "IMAGE")
    icons.load("PASTE", os.path.join(ICON_DIR, "paste.png"), "IMAGE")


    icons.load("HAND_L", os.path.join(ICON_DIR, "hand_l.png"), "IMAGE")
    icons.load("HAND_R", os.path.join(ICON_DIR, "hand_r.png"), "IMAGE")
    icons.load("FOOT_L", os.path.join(ICON_DIR, "foot_l.png"), "IMAGE")
    icons.load("FOOT_R", os.path.join(ICON_DIR, "foot_r.png"), "IMAGE")
    icons.load("BODY", os.path.join(ICON_DIR, "body.png"), "IMAGE")

    icons.load("MIRROR_UV", os.path.join(ICON_DIR, "mirror_uv.png"), "IMAGE")

    icons.load("COLOR_GRID", os.path.join(ICON_DIR, "color_grid.png"), "IMAGE")

    icons.load("SIZE", os.path.join(ICON_DIR, "size.png"), "IMAGE")

    icons.load("EDGE_X", os.path.join(ICON_DIR, "edge_x.png"), "IMAGE")
    icons.load("EDGE_Y", os.path.join(ICON_DIR, "edge_y.png"), "IMAGE")

    icons.load("SNAP", os.path.join(ICON_DIR, "snap.png"), "IMAGE")
    icons.load("AXIS_X", os.path.join(ICON_DIR, "axis_x.png"), "IMAGE")
    icons.load("AXIS_Y", os.path.join(ICON_DIR, "axis_y.png"), "IMAGE")

    icons.load("SYMM_N_X", os.path.join(ICON_DIR, "symm_n_x.png"), "IMAGE")
    icons.load("SYMM_P_X", os.path.join(ICON_DIR, "symm_p_x.png"), "IMAGE")
    icons.load("SYMM_N_Y", os.path.join(ICON_DIR, "symm_n_y.png"), "IMAGE")
    icons.load("SYMM_P_Y", os.path.join(ICON_DIR, "symm_p_y.png"), "IMAGE")

    icons.load("BOUND", os.path.join(ICON_DIR, "boundary.png"), "IMAGE")
    icons.load("SHUFFLE", os.path.join(ICON_DIR, "shuffle.png"), "IMAGE")
    icons.load("SHAPE", os.path.join(ICON_DIR, "shape.png"), "IMAGE")
    icons.load("CIRCLE", os.path.join(ICON_DIR, "circle.png"), "IMAGE")
    icons.load("DIST_UVS", os.path.join(ICON_DIR, "dist_uvs.png"), "IMAGE")
    icons.load("OFFSET", os.path.join(ICON_DIR, "offset.png"), "IMAGE")
    icons.load("STITCH", os.path.join(ICON_DIR, "stitch.png"), "IMAGE")
    icons.load("STRATCH", os.path.join(ICON_DIR, "stretch.png"), "IMAGE")

    icons.load("CUBE", os.path.join(ICON_DIR, "cube.png"), "IMAGE")

    preview_collections["icons"] = icons


def unregister():
    for pcoll in preview_collections.values():
        bpy.utils.previews.remove(pcoll)
    preview_collections.clear()
