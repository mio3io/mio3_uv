import bpy
import bmesh
import gpu
from mathutils import Vector
from gpu_extras.batch import batch_for_shader
from ..classes.operator import Mio3UVOperator
from bpy.types import SpaceImageEditor

msgbus_owner = object()


def reload_view(context):
    for window in context.window_manager.windows:
        for area in window.screen.areas:
            if area.type == "IMAGE_EDITOR":
                area.tag_redraw()


class UV_OT_mio3_guide_padding(Mio3UVOperator):
    bl_idname = "uv.mio3_guide_padding"
    bl_label = "Preview Padding"
    bl_description = "Preview the padding lines"
    bl_options = {"REGISTER", "UNDO"}

    _handle = None

    _color = (0.1, 0.5, 1.0, 1)
    _vertices = []
    _padding = 16 / 1024

    @classmethod
    def is_running(cls):
        return cls._handle is not None

    @classmethod
    def remove_handler(cls):
        if cls.is_running():
            SpaceImageEditor.draw_handler_remove(cls._handle, "WINDOW")
            cls._handle = None
        bpy.msgbus.clear_by_owner(msgbus_owner)
        reload_view(bpy.context)

    def invoke(self, context, event):
        cls = self.__class__
        is_running = cls.is_running()
        cls.remove_handler()
        if is_running:
            return {"FINISHED"}

        cls._handle = SpaceImageEditor.draw_handler_add(self.draw_2d, ((self, context)), "WINDOW", "POST_PIXEL")

        def callback():
            cls.remove_handler()

        bpy.msgbus.subscribe_rna(key=(bpy.types.Object, "mode"), owner=msgbus_owner, args=(), notify=callback)

        self.update_mesh(context)
        reload_view(context)
        context.window_manager.modal_handler_add(self)
        return {"RUNNING_MODAL"}

    def modal(self, context, event):
        cls = self.__class__
        if not cls.is_running():
            return {"FINISHED"}
        if event.type == "LEFTMOUSE" and event.value == "RELEASE":
            self.update_mesh(context)
        return {"PASS_THROUGH"}

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
        selected_objects = [obj for obj in context.selected_objects if obj.type == "MESH" and obj.mode == "EDIT"]

        for obj in selected_objects:
            obj.data.update()
            bm = bmesh.from_edit_mesh(obj.data)
            uv_layer = bm.loops.layers.uv.verify()
            padding = cls._padding

            vertex_to_padded = {}
            original_uvs = set()

            for face in bm.faces:
                for loop in face.loops:
                    uv = loop[uv_layer].uv
                    uv_next = loop.link_loop_next[uv_layer].uv

                    uv_tuple = uv.to_tuple(5)
                    uv_next_tuple = uv_next.to_tuple(5)
                    original_uvs.update([uv_tuple, uv_next_tuple])

                    if loop.edge.is_boundary or loop.edge.seam:
                        edge_vec = uv_next - uv
                        normal = Vector((edge_vec.y, -edge_vec.x)).normalized()

                        pad_uv1 = uv + normal * padding
                        pad_uv2 = uv_next + normal * padding

                        cls._vertices.extend([pad_uv1, pad_uv2])

                        vertex_to_padded.setdefault(uv_tuple, []).append(pad_uv1)
                        vertex_to_padded.setdefault(uv_next_tuple, []).append(pad_uv2)

            for uv_key, padded_list in vertex_to_padded.items():
                for i in range(len(padded_list)):
                    for j in range(i + 1, len(padded_list)):
                        cls._vertices.extend([padded_list[i], padded_list[j]])

            bm.free()

    @staticmethod
    def draw_2d(self, context):
        viewport_vertices = [context.region.view2d.view_to_region(v[0], v[1], clip=False) for v in self._vertices]
        shader = gpu.shader.from_builtin("UNIFORM_COLOR")
        batch = batch_for_shader(shader, "LINES", {"pos": viewport_vertices})
        shader.bind()
        shader.uniform_float("color", self._color)
        batch.draw(shader)

    @classmethod
    def unregister(cls):
        cls.remove_handler()


@bpy.app.handlers.persistent
def load_handler(dummy):
    # print("load_handler")
    # print(dummy)
    UV_OT_mio3_guide_padding.remove_handler()


def register():
    bpy.utils.register_class(UV_OT_mio3_guide_padding)
    bpy.app.handlers.load_post.append(load_handler)


def unregister():
    bpy.app.handlers.load_post.remove(load_handler)
    bpy.utils.unregister_class(UV_OT_mio3_guide_padding)
