import bpy
import bmesh
import gpu
from mathutils import Vector
from bpy.types import SpaceImageEditor
from gpu_extras.batch import batch_for_shader
from ..classes import Mio3UVOperator
from ..globals import PADDING_AUTO

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
    _padding = 16 / 1024

    _shader = None
    _vertices = []
    _excluded_ops = {
        "UV_OT_select_linked",
        "UV_OT_select_more",
        "UV_OT_select_all",
    }

    @classmethod
    def is_running(cls):
        return cls._handle is not None

    @classmethod
    def is_relevant_uv_operator(cls, bl_idname):
        if bl_idname in cls._excluded_ops:
            return False
        return bl_idname.startswith(("TRANSFORM_OT_", "UV_OT_", "MIO3UV_"))

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

        self._shader = gpu.shader.from_builtin("UNIFORM_COLOR")
        self._press_mouse_pos = None
        self._mouse_pressed = False
        self._prev_active_op_key = None

        self.update_state(context)
        self.update_mesh(context)
        reload_view(context)
        context.window_manager.modal_handler_add(self)
        return {"RUNNING_MODAL"}

    def modal(self, context, event):
        cls = self.__class__
        if not cls.is_running():
            return {"FINISHED"}

        active_op = getattr(context, "active_operator", None)
        current_active_op_key = (active_op.bl_idname, id(active_op)) if active_op else None
        is_new_active_op = current_active_op_key is not None and current_active_op_key != self._prev_active_op_key
        is_relevant_active_op = bool(active_op and cls.is_relevant_uv_operator(active_op.bl_idname))

        if is_new_active_op and is_relevant_active_op:
            self.update_mesh(context)
            self._press_mouse_pos = None
            self._mouse_pressed = False

        if event.type == "LEFTMOUSE" and event.value == "PRESS":
            self._press_mouse_pos = (event.mouse_region_x, event.mouse_region_y)
            self._mouse_pressed = True

        if event.type == "LEFTMOUSE" and event.value == "RELEASE":
            self._mouse_pressed = False
            self._press_mouse_pos = None

        if event.type in ("ESC", "RIGHTMOUSE") and event.value == "PRESS":
            self._press_mouse_pos = None
            self._mouse_pressed = False

        if event.type == "Z" and event.ctrl and event.value == "RELEASE":
            self.update_mesh(context)

        self._prev_active_op_key = current_active_op_key
        return {"PASS_THROUGH"}

    @classmethod
    def redraw(cls, context):
        cls.update_state(context)
        cls.update_mesh(context)
        reload_view(context)

    @classmethod
    def update_mesh(cls, context):
        cls._vertices = []
        selected_objects = [obj for obj in context.selected_objects if obj.type == "MESH" and obj.mode == "EDIT"]
        padding = cls._padding

        for obj in selected_objects:
            obj.data.update()
            bm = bmesh.from_edit_mesh(obj.data)
            uv_layer = bm.loops.layers.uv.verify()
            
            vertex_to_padded = {}

            for face in bm.faces:
                for loop in face.loops:
                    curr_uv = loop[uv_layer].uv
                    next_uv = loop.link_loop_next[uv_layer].uv

                    curr_key = curr_uv.to_tuple(5)
                    next_key = next_uv.to_tuple(5)

                    if loop.edge.is_boundary or loop.edge.seam:
                        edge_vec = next_uv - curr_uv
                        normal = Vector((edge_vec.y, -edge_vec.x)).normalized()

                        pad_uv1 = curr_uv + normal * padding
                        pad_uv2 = next_uv + normal * padding

                        cls._vertices.extend([pad_uv1, pad_uv2])

                        vertex_to_padded.setdefault(curr_key, []).append(pad_uv1)
                        vertex_to_padded.setdefault(next_key, []).append(pad_uv2)

            for uv_key, padded_list in vertex_to_padded.items():
                for i in range(len(padded_list)):
                    for j in range(i + 1, len(padded_list)):
                        cls._vertices.extend([padded_list[i], padded_list[j]])

            bm.free()

    @classmethod
    def update_state(cls, context):
        obj = context.active_object
        if obj.mio3uv.padding_px == "AUTO":
            calc_padding_px = PADDING_AUTO.get(obj.mio3uv.image_size, 16)
        else:
            calc_padding_px = int(obj.mio3uv.padding_px)
        cls._padding = int(calc_padding_px) / int(obj.mio3uv.image_size)

    @staticmethod
    def draw_2d(self, context):
        viewport_vertices = [context.region.view2d.view_to_region(v[0], v[1], clip=False) for v in self._vertices]
        shader = self._shader
        batch = batch_for_shader(shader, "LINES", {"pos": viewport_vertices})
        shader.bind()
        shader.uniform_float("color", self._color)
        batch.draw(shader)

    @classmethod
    def unregister(cls):
        cls.remove_handler()


@bpy.app.handlers.persistent
def load_handler(dummy):
    UV_OT_mio3_guide_padding.remove_handler()


def register():
    bpy.utils.register_class(UV_OT_mio3_guide_padding)
    bpy.app.handlers.load_post.append(load_handler)


def unregister():
    bpy.app.handlers.load_post.remove(load_handler)
    bpy.utils.unregister_class(UV_OT_mio3_guide_padding)
