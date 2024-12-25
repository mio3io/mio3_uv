import bpy
from bpy.props import FloatProperty
from ..classes.operator import Mio3UVOperator


class MIO3UV_OT_merge(Mio3UVOperator):
    bl_idname = "uv.mio3_merge"
    bl_label = "Merge"
    bl_description = "Selected UV vertices that are within a radius of each other are welded together"
    bl_options = {"REGISTER", "UNDO"}

    threshold: FloatProperty(
        name="Threshold",
        default=0.0001,
        min=0.0,
        step=0.01,
        precision=4
    )

    def execute(self, context):
        self.start_time()
        self.objects = self.get_selected_objects(context)

        bpy.ops.uv.remove_doubles(threshold=self.threshold)

        self.print_time()
        return {"FINISHED"}


classes = [MIO3UV_OT_merge]


def register():
    for c in classes:
        bpy.utils.register_class(c)


def unregister():
    for c in classes:
        bpy.utils.unregister_class(c)
