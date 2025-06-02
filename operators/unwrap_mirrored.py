import bpy
import bmesh
from bpy.props import BoolProperty
from mathutils import kdtree
from ..classes import Mio3UVOperator


class MIO3UV_OT_unwrap_mirror(Mio3UVOperator):
    bl_idname = "uv.mio3_unwrap_mirrored"
    bl_label = "Unwrap Virtual Mirror"
    bl_description = "Unwrap as if the mirror modifier is applied"
    bl_options = {"REGISTER", "UNDO"}

    orient_world: BoolProperty(
        name="Orient World",
        default=True,
    )

    def execute(self, context):
        self.start_time()
        obj = context.active_object

        show_only_shape_key = obj.show_only_shape_key
        obj.show_only_shape_key = True

        bpy.ops.object.mode_set(mode="OBJECT")

        for o in context.selected_objects:
            o.select_set(False)

        modifier_states = self.store_state(obj)

        depsgraph = context.evaluated_depsgraph_get()
        eval_obj = obj.evaluated_get(depsgraph)
        copy_mesh = bpy.data.meshes.new_from_object(eval_obj, depsgraph=depsgraph)
        copy_obj = bpy.data.objects.new(obj.name + "_eval", copy_mesh)
        context.collection.objects.link(copy_obj)

        copy_obj.select_set(True)

        self.restore_state(obj, modifier_states)

        # obj_copyを編集モードにする
        context.view_layer.objects.active = copy_obj
        bpy.ops.object.mode_set(mode="EDIT")

        bpy.ops.uv.unwrap(method="ANGLE_BASED", margin=0.001)
        if self.orient_world:
            bpy.ops.uv.align_rotation(method="GEOMETRY", axis="Z")

        obj.select_set(True)

        # 元オブジェクトを編集モードにする
        context.view_layer.objects.active = obj
        bpy.ops.object.mode_set(mode="EDIT")

        # obj_copyのUVをobjに転送
        bm_src = bmesh.from_edit_mesh(copy_obj.data)
        bm_src.faces.ensure_lookup_table()
        uv_layer_copy = bm_src.loops.layers.uv.verify()

        kd = kdtree.KDTree(len(bm_src.faces))
        for i, face in enumerate(bm_src.faces):
            if face.select:
                face_center = face.calc_center_median()
                kd.insert(face_center, i)
        kd.balance()

        bm = bmesh.from_edit_mesh(obj.data)
        uv_layer = bm.loops.layers.uv.verify()

        for face in bm.faces:
            if not face.select:
                continue
            _, idx, dist = kd.find(face.calc_center_median())
            if dist > 1e-4:
                continue
            face_src = bm_src.faces[idx]
            for loop in face.loops:
                loop_uv = loop[uv_layer]
                v_co = loop.vert.co
                if loop_uv.select:
                    closest_vert = min(face_src.verts, key=lambda v: (v.co - v_co).length_squared)
                    for loop_src in face_src.loops:
                        if loop_src.vert == closest_vert:
                            loop_uv.uv = loop_src[uv_layer_copy].uv
                            break

        bmesh.update_edit_mesh(obj.data)

        obj.show_only_shape_key = show_only_shape_key

        bpy.data.objects.remove(copy_obj, do_unlink=True)
        bpy.data.meshes.remove(copy_mesh, do_unlink=True)

        self.print_time()
        return {"FINISHED"}

    @staticmethod
    def store_state(obj):
        modifier_states = {}
        for mod in obj.modifiers:
            if mod.type == "MIRROR":
                modifier_states[mod.name] = (
                    mod.show_viewport,
                    mod.use_mirror_merge,
                    mod.use_mirror_u,
                    mod.use_mirror_v,
                )
                mod.use_mirror_merge = True
                mod.use_mirror_u = False
                mod.use_mirror_v = False
            else:
                modifier_states[mod.name] = (mod.show_viewport, None)
        for mod in obj.modifiers:
            mod.show_viewport = mod.type == "MIRROR"
        return modifier_states

    @staticmethod
    def restore_state(obj, modifier_states):
        for mod in obj.modifiers:
            if mod.name in modifier_states:
                mod_state = modifier_states[mod.name]
                mod.show_viewport = mod_state[0]
                if mod.type == "MIRROR":
                    mod.use_mirror_merge = mod_state[1]
                    mod.use_mirror_u = mod_state[2]
                    mod.use_mirror_v = mod_state[3]


def register():
    bpy.utils.register_class(MIO3UV_OT_unwrap_mirror)


def unregister():
    bpy.utils.unregister_class(MIO3UV_OT_unwrap_mirror)
