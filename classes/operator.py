import bpy
import bmesh
import time
from bpy.types import Operator, Panel
from ..utils import sync_uv_from_mesh, sync_mesh_from_uv


class Mio3UVPanel(Panel):
    @classmethod
    def poll(cls, context):
        return context.area.spaces.active.mode == "UV" and context.active_object is not None


class Mio3UVDebug:
    _start_time = 0

    def start_time(self):
        self._start_time = time.time()

    def print_time(self):
        # print("Time: {}".format(time.time() - self._start_time))
        pass


class Mio3UVOperator(Operator, Mio3UVDebug):
    @classmethod
    def poll(cls, context):
        obj = context.active_object
        return cls.is_valid_object(obj) and obj.data.uv_layers

    @staticmethod
    def is_valid_object(obj):
        return obj is not None and obj.type == "MESH" and obj.mode == "EDIT"

    @staticmethod
    def get_selected_objects(context):
        return [obj for obj in context.objects_in_mode if obj.type == "MESH"]

    @staticmethod
    def sync_uv_from_mesh(context, selected_objects):
        sync_uv_from_mesh(context, selected_objects)

    @staticmethod
    def sync_mesh_from_uv(context, selected_objects):
        sync_mesh_from_uv(context, selected_objects)

    def check_selected_face_objects(self, objects):
        selected_face_objects = False
        for obj in objects:
            bm = bmesh.from_edit_mesh(obj.data)
            uv_layer = bm.loops.layers.uv.verify()
            selected_face = self.check_selected_uv(bm, uv_layer)
            bm.free()
            if selected_face:
                selected_face_objects = True
                break
        return selected_face_objects

    def check_selected_uv(self, bm, uv_layer):
        use_uv_select_sync = bpy.context.tool_settings.use_uv_select_sync
        selected_face = False
        if use_uv_select_sync:
            for face in bm.faces:
                if face.select:
                    uv_selected = [l[uv_layer].select for l in face.loops]
                    if all(uv_selected):
                        selected_face = True
                        break
            return selected_face
        else:
            for face in bm.faces:
                if face.select:
                    uv_selected = [l[uv_layer].select_edge for l in face.loops]
                    if all(uv_selected):
                        selected_face = True
                        break
            return selected_face


class Mio3UVGlobalOperator(Operator, Mio3UVDebug):
    @staticmethod
    def get_selected_objects(context):
        return [obj for obj in context.selected_objects if obj.type == "MESH"]


