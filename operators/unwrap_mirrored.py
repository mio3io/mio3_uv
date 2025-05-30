import bpy
import bmesh
from bpy.props import EnumProperty
from mathutils import kdtree
from ..classes import Mio3UVOperator


class MIO3UV_OT_unwrap_mirror(Mio3UVOperator):
    bl_idname = "uv.mio3_unwrap_mirrored"
    bl_label = "Mirror-applied Unwrap"
    bl_description = "Unwrap as if the mirror modifier is applied"
    bl_options = {"REGISTER", "UNDO"}

    method: EnumProperty(
        name="Method",
        items=[
            ("ANGLE_BASED", "Angle Based", "Angle based unwrapping method"),
            ("CONFORMAL", "Conformal", "Conformal mapping method"),
        ],
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

        bpy.ops.uv.unwrap(method=self.method, margin=0.001)

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

        is_editor = context.area.type == "IMAGE_EDITOR"

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
                if loop_uv.select or not is_editor:
                    closest_vert = min(face_src.verts, key=lambda v: (v.co - v_co).length_squared)
                    for loop_src in face_src.loops:
                        if loop_src.vert == closest_vert:
                            loop_uv.uv = loop_src[uv_layer_copy].uv
                            break

        bmesh.update_edit_mesh(obj.data)

        obj.use_shape_key_edit_mode = show_only_shape_key

        bpy.data.objects.remove(copy_obj, do_unlink=True)
        bpy.data.meshes.remove(copy_mesh, do_unlink=True)

        self.print_time()
        return {"FINISHED"}

    @staticmethod
    def store_state(obj):
        modifier_states = {}
        for mod in obj.modifiers:
            if mod.type == "MIRROR":
                modifier_states[mod.name] = (mod.show_viewport, mod.use_mirror_merge)
                mod.use_mirror_merge = True
            else:
                modifier_states[mod.name] = (mod.show_viewport, None)
        for mod in obj.modifiers:
            mod.show_viewport = mod.type == "MIRROR"
        return modifier_states

    @staticmethod
    def restore_state(obj, modifier_states):
        for mod in obj.modifiers:
            if mod.name in modifier_states:
                mod.show_viewport = modifier_states[mod.name][0]
                if mod.type == "MIRROR":
                    mod.use_mirror_merge = modifier_states[mod.name][1]


def menu_context(self, context):
    self.layout.separator()
    self.layout.operator(MIO3UV_OT_unwrap_mirror.bl_idname)


def register():
    bpy.utils.register_class(MIO3UV_OT_unwrap_mirror)
    bpy.types.IMAGE_MT_uvs_unwrap.append(menu_context)


def unregister():
    bpy.utils.unregister_class(MIO3UV_OT_unwrap_mirror)
    bpy.types.IMAGE_MT_uvs_unwrap.remove(menu_context)
