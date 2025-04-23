from . import preferences
from . import icons
from . import property
from . import translation

from .operators import unwrap
from .operators import unwrap_project
from .operators import straight
from .operators import rectify
from .operators import gridify
from .operators import seam
from .operators import normalize
from .operators import pin

from .operators import rotate
from .operators import mirror
from .operators import orient
from .operators import select

from .operators import align
from .operators import align_seam
from .operators import circle
from .operators import stretch
from .operators import relax
from .operators import offset
from .operators import stitch
from .operators import merge

from .operators import sort
from .operators import distribute
from .operators import stack
from .operators import shuffle

from .operators import symmetrize
from .operators import unfoldify
from .operators import body_preset

from .operators import view_padding
from .operators import view_checker_map
from .operators import mesh_uvmesh

from .ui import ui_main
from .ui import ui_view
from .ui import ui_menu


bl_info = {
    "name": "Mio3 UV",
    "author": "mio",
    "version": (1, 5, 0),
    "blender": (4, 2, 0),
    "location": "UV Image Editor > Sidebar > Mio3",
    "description": "UV Edit Assistant Tools",
    "category": "UV",
}


modules = [
    preferences,
    translation,
    icons,
    unwrap,
    unwrap_project,
    straight,
    rectify,
    gridify,
    seam,
    normalize,
    pin,
    rotate,
    mirror,
    orient,
    select,
    align,
    align_seam,
    circle,
    stretch,
    relax,
    offset,
    stitch,
    merge,
    sort,
    distribute,
    stack,
    shuffle,
    symmetrize,
    unfoldify,
    body_preset,
    view_padding,
    view_checker_map,
    mesh_uvmesh,
    ui_main,
    ui_view,
    ui_menu,
    property,
]


def register():
    for module in modules:
        module.register()


def unregister():
    for module in reversed(modules):
        module.unregister()
