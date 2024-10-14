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

from .operators import rotate
from .operators import orient
from .operators import select

from .operators import align
from .operators import align_seam
from .operators import edge_loop
from .operators import relax
from .operators import offset
from .operators import stitch

from .operators import sort
from .operators import place
from .operators import stack
from .operators import shuffle

from .operators import symmetrize
from .operators import unfoldify
from .operators import body_preset

from .operators import view_padding
from .operators import view_colorgid

from .ui import ui_main
from .ui import ui_view


bl_info = {
    "name": "Mio3 UV",
    "author": "mio",
    "version": (1, 1, 0),
    "blender": (3, 6, 0),
    "location": "UV Image Editor > Sidebar > Mio3",
    "description": "UV Edit support",
    "category": "UV",
}


modules = [
    icons,
    unwrap,
    unwrap_project,
    straight,
    rectify,
    gridify,
    seam,
    normalize,
    rotate,
    orient,
    select,
    align,
    align_seam,
    edge_loop,
    relax,
    offset,
    stitch,
    sort,
    place,
    stack,
    shuffle,
    symmetrize,
    unfoldify,
    body_preset,
    view_padding,
    view_colorgid,
    ui_main,
    ui_view,
    property,
]


def register():
    translation.register(__name__)
    for module in modules:
        module.register()


def unregister():
    for module in reversed(modules):
        module.unregister()
    translation.unregister(__name__)


if __name__ == "__main__":
    register()
