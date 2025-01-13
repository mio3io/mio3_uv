import bpy
import bmesh
import time
from bpy.types import Operator, Panel


class Mio3UVPanel(Panel):
    @classmethod
    def poll(cls, context):
        obj = context.active_object
        return context.area.spaces.active.mode == "UV" and context.mode == "EDIT_MESH"
        # obj = context.active_object
        # return obj is not None and obj.type == "MESH"


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

    def get_selected_objects(self, context):
        return [obj for obj in context.objects_in_mode if obj.type == "MESH"]

    def sync_uv_from_mesh(self, context, selected_objects):
        objects = selected_objects if selected_objects else context.objects_in_mode
        for obj in objects:
            bm = bmesh.from_edit_mesh(obj.data)
            uv_layer = bm.loops.layers.uv.verify()
            for face in bm.faces:
                for loop in face.loops:
                    loop[uv_layer].select = False
                    loop[uv_layer].select_edge = False
            for vert in bm.verts:
                if vert.select:
                    for loop in vert.link_loops:
                        loop[uv_layer].select = True
            for edge in bm.edges:
                if edge.select:
                    for loop in edge.link_loops:
                        loop[uv_layer].select_edge = True
            bmesh.update_edit_mesh(obj.data)

    def sync_mesh_from_uv(self, context, selected_objects):
        objects = selected_objects if selected_objects else context.selected_objects
        for obj in objects:
            bm = bmesh.from_edit_mesh(obj.data)
            uv_layer = bm.loops.layers.uv.verify()

            for vert in bm.verts:
                vert.select = False
            bm.select_flush(False)

            for vert in bm.verts:
                vert.select = all(loop[uv_layer].select for loop in vert.link_loops)
            # for edge in bm.edges:
            #     if all(loop[uv_layer].select_edge for loop in edge.link_loops):
            #         edge.select = True
            for face in bm.faces:
                if all(loop[uv_layer].select for loop in face.loops):
                    face.select = True
            bm.select_flush(True)
            bmesh.update_edit_mesh(obj.data)
            obj.data.update()

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
