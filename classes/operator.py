import bpy
import bmesh
import time
from bpy.types import Context, Object, Operator, Panel
from bmesh.types import BMVert, BMLoop, BMLayerItem, BMesh, BMFace, BMEdge
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
        # print("Time: {:.5f}".format(time.time() - self._start_time))
        pass


class Mio3UVOperator(Operator, Mio3UVDebug):
    @classmethod
    def poll(cls, context):
        obj = context.active_object
        return cls.is_valid_object(obj) and obj.data.uv_layers

    @staticmethod
    def is_valid_object(obj: Object):
        return obj is not None and obj.type == "MESH" and obj.mode == "EDIT"

    @staticmethod
    def get_selected_objects(context: Context):
        return [obj for obj in context.objects_in_mode if obj.type == "MESH"]

    @staticmethod
    def sync_uv_from_mesh(context, selected_objects):
        sync_uv_from_mesh(context, selected_objects)

    @staticmethod
    def sync_mesh_from_uv(context, selected_objects):
        sync_mesh_from_uv(context, selected_objects)

    @staticmethod
    def store_mesh_select_mode(context: Context, mode=None):
        select_mode = context.tool_settings.mesh_select_mode[:]
        if mode is not None:
            context.tool_settings.mesh_select_mode = mode
        return select_mode

    @staticmethod
    def restore_mesh_select_mode(context: Context, select_mode):
        context.tool_settings.mesh_select_mode = select_mode

    @staticmethod
    def store_uv_select_mode(context: Context, mode=None):
        select_mode = context.tool_settings.uv_select_mode
        if mode is not None:
            context.tool_settings.uv_select_mode = mode
        return select_mode

    def check_selected_face_objects(self, objects: list[Object]) -> bool:
        if bpy.context.tool_settings.use_uv_select_sync:
            for obj in objects:
                if obj.type == "MESH":
                    if obj.data.total_face_sel > 0:
                        return True
            return False
        is_selected_face_objects = False
        for obj in objects:
            bm = bmesh.from_edit_mesh(obj.data)
            uv_layer = bm.loops.layers.uv.verify()
            selected_face = self.check_selected_uv(bm, uv_layer)
            bm.free()
            if selected_face:
                is_selected_face_objects = True
                break
        return is_selected_face_objects

    def check_selected_uv(self, bm:BMesh, uv_layer: BMLayerItem):
        for face in bm.faces:
            if face.select:
                if all({l[uv_layer].select_edge for l in face.loops}): # select_edge -> エッジ選択時の〼を許容しない
                    return True
        return False
    

class Mio3UVGlobalOperator(Operator, Mio3UVDebug):
    @staticmethod
    def get_selected_objects(context):
        return [obj for obj in context.selected_objects if obj.type == "MESH"]


