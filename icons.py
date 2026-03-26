import os
import bpy
from bpy.utils import previews


ICON_DIR = os.path.join(os.path.dirname(__file__), "icons")

icon_names = [
    "unwrap",
    "rectify",
    "grid",
    "straight",
    "highlight",
    "merge",
    "align_x_center",
    "align_y_center",
    "align_seam_y",
    "align_x",
    "align_y",
    "align_center",
    "align_top",
    "align_bottom",
    "align_left",
    "align_right",
    "align_top_left",
    "align_top_right",
    "align_bottom_left",
    "align_bottom_right",
    "z",
    "normalize",
    "flip_y",
    "flip_x",
    "x_n",
    "x_p",
    "similar",
    "unfoldify",
    "symmetrize",
    "n90",
    "p90",
    "p180",
    "orient",
    "stack",
    "dist_x",
    "dist_y",
    "seam",
    "relax",
    "copy",
    "paste",
    "hand_l",
    "hand_r",
    "foot_l",
    "foot_r",
    "body",
    "button",
    "mirror_uv",
    "color_grid",
    "size",
    "edges_x",
    "edges_y",
    "snap",
    "axis_x",
    "axis_y",
    "symm_n_x",
    "symm_p_x",
    "symm_n_y",
    "symm_p_y",
    "boundary",
    "shuffle",
    "circle",
    "offset",
    "stitch",
    "stretch",
    "cube",
    "auto",
    "padding",
    "camera",
]


class IconSet:
    def __init__(self):
        self._icons = None
        for name in icon_names:
            setattr(self, name, 0)

    def load(self):
        self._icons = previews.new()
        for name in icon_names:
            icon_path = os.path.join(ICON_DIR, "{}.png".format(name))
            if os.path.exists(icon_path):
                self._icons.load(name, icon_path, "IMAGE")
                setattr(self, name, self._icons[name].icon_id)

    def unload(self):
        if self._icons:
            previews.remove(self._icons)
            self._icons = None
            


icons = IconSet()


def register():
    icons.load()


def unregister():
    icons.unload()
