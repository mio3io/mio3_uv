import bpy
import os
import math
import bmesh
from bpy.props import BoolProperty, EnumProperty
from ..classes.operator import Mio3UVOperator
from ..icons import preview_collections

BLEND_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "blend")
NAME_NODE_GROUP_UV_MESH = "Mio3UVMesh"

NAME_MOD_UV_MESH = "Mio3UVMeshModifier"

# This node tree was customized using from Nikita's blog and stackexchange as a reference.
# https://b3d.interplanety.org/en/transforming-mesh-to-its-uv-map-with-geometry-nodes-in-blender/
# https://blender.stackexchange.com/questions/302193/get-edge-seams-from-uv-islands-in-geometry-nodes/


class MIO3UV_OT_uvmesh(Mio3UVOperator):
    bl_idname = "mesh.mio3_uvmesh"
    bl_label = "UV Mesh"
    bl_description = "Set up a modifier for UV to Mesh (using Geometry Nodes)"
    bl_options = {"REGISTER", "UNDO"}

    auto_scale: BoolProperty(name="Auto Scaling", default=True)

    @classmethod
    def poll(cls, context):
        obj = context.active_object
        return obj is not None and obj.type == "MESH" and obj.mode == "OBJECT"

    def execute(self, context):
        obj = context.active_object
        props_object = obj.mio3uv

        existing_modifier = self.get_modifier(obj)
        if not existing_modifier:

            existing_geometry_node = self.get_node_groups()
            if existing_geometry_node:
                geometry_node = existing_geometry_node
            else:
                geometry_node = self.create_new_geometry_node(context)

            modifier = obj.modifiers.new(name=NAME_MOD_UV_MESH, type="NODES")
            modifier.show_expanded = False
            modifier.node_group = geometry_node
            modifier["Socket_3_use_attribute"] = True
            modifier["Socket_3_attribute_name"] = obj.data.uv_layers.active.name
            # modifier["Socket_4"] = 1
            # modifier["Socket_6"] = 2
            props_object.uvmesh_factor = 1
            if self.auto_scale:
                props_object.uvmesh_size = self.auto_adjust_size(obj)
            else:
                props_object.uvmesh_size = 2

        return {"FINISHED"}

    def auto_adjust_size(self, obj):
        bm = bmesh.new()
        bm.from_mesh(obj.data)
        mesh_area = self.calc_mesh_area(bm)
        uv_area = self.calc_uv_area(bm)
        bm.free()
        if uv_area > 0:
            size = math.sqrt(mesh_area / uv_area)
            size = max(0.1, min(size, 200.0))
            props_object = obj.mio3uv
            props_object.uvmesh_size = size
            return size
        return 2

    def calc_mesh_area(self, bm):
        area = sum(f.calc_area() for f in bm.faces)
        return area

    def calc_uv_area(self, bm):
        uv_layer = bm.loops.layers.uv.verify()
        total_area = 0.0
        for face in bm.faces:
            if len(face.loops) < 3:
                continue
            uv_coords = [loop[uv_layer].uv for loop in face.loops]
            uv0 = uv_coords[0]
            for i in range(1, len(uv_coords) - 1):
                uv1 = uv_coords[i]
                uv2 = uv_coords[i + 1]
                area = 0.5 * abs((uv1.x - uv0.x) * (uv2.y - uv0.y) - (uv2.x - uv0.x) * (uv1.y - uv0.y))
                total_area += area
        return total_area

    def get_node_groups(self):
        return bpy.data.node_groups.get(NAME_NODE_GROUP_UV_MESH)

    def get_modifier(self, obj):
        return obj.modifiers.get(NAME_MOD_UV_MESH)

    def create_new_geometry_node(self, context):
        blend_path = os.path.join(BLEND_DIR, "mio3uv.blend")
        try:
            mode = context.active_object.mode
            if mode != "OBJECT":
                bpy.ops.object.mode_set(mode="OBJECT")
            bpy.ops.wm.append(
                filename=NAME_NODE_GROUP_UV_MESH,
                directory=os.path.join(blend_path, "NodeTree"),
                link=False,
            )
            node_group = bpy.data.node_groups.get(NAME_NODE_GROUP_UV_MESH)
            node_group.use_fake_user = True
            if mode != context.active_object.mode:
                bpy.ops.object.mode_set(mode=mode)
            return node_group
        except:
            self.report({"ERROR"}, "Failed import node group")
        return None


class MIO3UV_OT_uvmesh_control(Mio3UVOperator):
    bl_idname = "mesh.mio3_uvmesh_control"
    bl_label = "UV Mesh"
    bl_description = "Control UV Mesh Factor"
    bl_options = {"REGISTER", "UNDO", "INTERNAL"}
    mode: EnumProperty(
        items=[
            ("UV", "UV", ""),
            ("MESH", "Mesh", ""),
            ("TOGGLE", "Toggle", ""),
        ],
        options={"HIDDEN"},
    )

    @classmethod
    def poll(cls, context):
        return context.active_object is not None

    def execute(self, context):
        props_object = context.active_object.mio3uv
        if self.mode == "UV":
            props_object.uvmesh_factor = 1
        elif self.mode == "MESH":
            props_object.uvmesh_factor = 0
        else:
            props_object.uvmesh_factor = 0 if props_object.uvmesh_factor > 0 else 1
        return {"FINISHED"}


class MIO3UV_OT_uvmesh_clear(Mio3UVOperator):
    bl_idname = "mesh.mio3_uvmesh_clear"
    bl_label = "UV Mesh"
    bl_description = ""
    bl_options = {"REGISTER", "UNDO", "INTERNAL"}

    @classmethod
    def poll(cls, context):
        obj = context.active_object
        return obj is not None

    def execute(self, context):
        obj = context.active_object
        modifier = obj.modifiers.get(NAME_MOD_UV_MESH)
        if not modifier:
            return {"CANCELLED"}

        obj.modifiers.remove(modifier)
        return {"FINISHED"}


def panel_tools(self, context):
    if context.active_object:
        modifier = context.active_object.modifiers.get("Mio3UVMeshModifier")
        if modifier:
            icons = preview_collections["icons"]
            props_object = context.active_object.mio3uv
            row = self.layout.row(align=True)
            row.operator(
                "mesh.mio3_uvmesh_control",
                text="",
                icon_value=icons["UNFOLDIFY"].icon_id if props_object.uvmesh_factor > 0 else icons["CUBE"].icon_id,
                depress=True if props_object.uvmesh_factor > 0 else False,
            ).mode = "TOGGLE"


classes = [MIO3UV_OT_uvmesh, MIO3UV_OT_uvmesh_control, MIO3UV_OT_uvmesh_clear]


def register():
    for c in classes:
        bpy.utils.register_class(c)
    bpy.types.VIEW3D_HT_tool_header.append(panel_tools)


def unregister():
    bpy.types.VIEW3D_HT_tool_header.remove(panel_tools)
    for c in classes:
        bpy.utils.unregister_class(c)
