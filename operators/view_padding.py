import bpy
import bmesh
import gpu
from mathutils import Vector
from gpu_extras.batch import batch_for_shader
from ..classes.operator import Mio3UVOperator
from bpy.types import SpaceImageEditor

mio3uv_view_padding_msgbus = object()


def callback(cls, context):
    MIO3UV_OT_view_padding.handle_remove(context)
    bpy.msgbus.clear_by_owner(mio3uv_view_padding_msgbus)


def reload_view(context):
    for window in context.window_manager.windows:
        for area in window.screen.areas:
            if area.type == "IMAGE_EDITOR":
                area.tag_redraw()


class MIO3UV_OT_view_padding(Mio3UVOperator):
    bl_idname = "uv.mio3_guide_padding"
    bl_label = "Preview Padding"
    bl_description = "Preview the padding lines"
    bl_options = {"REGISTER", "UNDO"}

    _handle = None
    _shader = None
    _region = None
    _color = (0.1, 0.5, 1.0, 1)
    _vertices = []

    _padding = None

    def execute(self, context):
        if not MIO3UV_OT_view_padding.is_running():
            self.handle_add(context)
        else:
            MIO3UV_OT_view_padding.handle_remove(context)
        return {"FINISHED"}

    @classmethod
    def draw_2d(cls, context):
        obj = context.active_object
        if obj.mio3uv.realtime:
            cls.update_mesh(context)
        viewport_vertices = [cls._region.view2d.view_to_region(v[0], v[1], clip=False) for v in cls._vertices]
        batch = batch_for_shader(cls._shader, "LINES", {"pos": viewport_vertices})

        cls._shader.bind()
        cls._shader.uniform_float("color", cls._color)
        batch.draw(cls._shader)

    @classmethod
    def is_running(cls):
        return cls._handle is not None

    @classmethod
    def handle_add(cls, context):
        cls._handle = SpaceImageEditor.draw_handler_add(cls.draw_2d, (context,), "WINDOW", "POST_PIXEL")
        cls._shader = gpu.shader.from_builtin("UNIFORM_COLOR")

        area = next(a for a in context.screen.areas if a.type == "IMAGE_EDITOR")
        cls._region = next(r for r in area.regions if r.type == "WINDOW")

        cls.redraw(context)

        bpy.msgbus.subscribe_rna(
            key=(bpy.types.Object, "mode"),
            owner=mio3uv_view_padding_msgbus,
            args=(cls, context),
            notify=callback,
        )

    @classmethod
    def handle_remove(cls, context):
        if cls.is_running():
            SpaceImageEditor.draw_handler_remove(cls._handle, "WINDOW")
            cls._handle = None
            cls._shader = None
            cls._region = None
            cls._vertices = []
            cls._padding = None
            bpy.msgbus.clear_by_owner(mio3uv_view_padding_msgbus)
            reload_view(context)

    @classmethod
    def redraw(cls, context):
        cls.update_state(context)
        cls.update_mesh(context)
        reload_view(context)

    @classmethod
    def update_state(cls, context):
        obj = context.active_object
        mio3uv = obj.mio3uv
        padding_pixels = int(mio3uv.padding_px)
        if mio3uv.image_size == "AUTO":
            image_size = None
            for area in context.screen.areas:
                if area.type == "IMAGE_EDITOR":
                    space = area.spaces.active
                    if space.image:
                        image_size = space.image.size[0]
            if not image_size:
                image_size = 2048
        else:
            image_size = int(mio3uv.image_size)
        cls._padding = padding_pixels / image_size

    @classmethod
    def update_mesh(cls, context):
        cls._vertices = []

        if not cls.is_running():
            return

        selected_objects = [obj for obj in context.selected_objects if obj.type == "MESH" and obj.mode == "EDIT"]

        for obj in selected_objects:
            padding_distance = cls._padding

            bm = bmesh.from_edit_mesh(obj.data)
            uv_layer = bm.loops.layers.uv.verify()

            vertex_to_padded = {}
            original_vertices = set()

            for face in bm.faces:
                for loop in face.loops:
                    uv = loop[uv_layer].uv
                    uv_next = loop.link_loop_next[uv_layer].uv
                    uv_tuple = uv.to_tuple(5)
                    uv_next_tuple = uv_next.to_tuple(5)
                    original_vertices.add(uv_tuple)

                    if loop.edge.is_boundary or loop.edge.seam:
                        edge_vector = uv_next - uv
                        normal = Vector((edge_vector.y, -edge_vector.x)).normalized()
                        padding_v1 = uv + normal * padding_distance
                        padding_v2 = uv_next + normal * padding_distance
                        cls._vertices.extend([padding_v1, padding_v2])

                        vertex_to_padded.setdefault(uv_tuple, []).append(padding_v1)
                        vertex_to_padded.setdefault(uv_next_tuple, []).append(padding_v2)

            for original_v in original_vertices:
                if original_v in vertex_to_padded:
                    padded_positions = vertex_to_padded[original_v]
                    for i in range(len(padded_positions)):
                        for j in range(i + 1, len(padded_positions)):
                            cls._vertices.extend([padded_positions[i], padded_positions[j]])

            bm.free()

    @classmethod
    def unregister(cls):
        cls.handle_remove(bpy.context)


class MIO3UV_OT_view_padding_refresh(Mio3UVOperator):
    bl_idname = "uv.mio3_guide_padding_refresh"
    bl_label = "Refresh Preview Padding"
    bl_description = "Refresh Preview Padding"
    bl_options = {"REGISTER", "UNDO", "INTERNAL"}

    def execute(self, context):
        if MIO3UV_OT_view_padding.is_running():
            MIO3UV_OT_view_padding.redraw(context)
        return {"FINISHED"}


@bpy.app.handlers.persistent
def load_handler(dummy):
    MIO3UV_OT_view_padding.handle_remove(bpy.context)


classes = [
    MIO3UV_OT_view_padding,
    MIO3UV_OT_view_padding_refresh,
]


def register():
    for c in classes:
        bpy.utils.register_class(c)
    bpy.app.handlers.load_post.append(load_handler)


def unregister():
    bpy.app.handlers.load_post.remove(load_handler)
    for c in classes:
        bpy.utils.unregister_class(c)
