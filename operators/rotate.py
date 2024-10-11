import bpy
import time
import math
from bpy.props import FloatProperty
from ..classes.operator import Mio3UVOperator

class MIO3UV_OT_rotate(Mio3UVOperator):
    bl_idname = "uv.mio3_rotate"
    bl_label = "Rotate"
    bl_description = "Rotate"
    bl_options = {"REGISTER", "UNDO"}

    angle: FloatProperty(
        name="Angle",
        default=math.radians(90),
        min=-math.pi,
        max=math.pi,
        subtype="ANGLE",
        step=1000,
    )

    def execute(self, context):
        bpy.ops.transform.rotate(
            value=self.angle,
            orient_type="VIEW",
            orient_matrix=((1, 0, 0), (0, 1, 0), (0, 0, 1)),
            orient_matrix_type="VIEW",
        )
        return {"FINISHED"}


classes = [MIO3UV_OT_rotate]


def register():
    for c in classes:
        bpy.utils.register_class(c)


def unregister():
    for c in classes:
        bpy.utils.unregister_class(c)
