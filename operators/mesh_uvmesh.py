import bpy
import os
from bpy.props import EnumProperty
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
    bl_description = ""
    bl_options = {"REGISTER", "UNDO"}

    @classmethod
    def poll(cls, context):
        obj = context.active_object
        return obj is not None and obj.type == "MESH"

    def execute(self, context):
        obj = context.active_object
        props_object = obj.mio3uv

        existing_modifier = self.find_modifier(obj)
        if not existing_modifier:

            existing_geometry_node = self.find_node_groups()
            if existing_geometry_node:
                geometry_node = existing_geometry_node
            else:
                geometry_node = self.create_new_geometry_node()

            modifier = obj.modifiers.new(name=NAME_MOD_UV_MESH, type="NODES")
            modifier.show_expanded = False
            modifier.node_group = geometry_node
            modifier["Socket_3_use_attribute"] = True
            modifier["Socket_3_attribute_name"] = obj.data.uv_layers.active.name
            # modifier["Socket_4"] = 1
            # modifier["Socket_6"] = 2
            props_object.uvmesh_factor = 1
            props_object.uvmesh_size = 2

        return {"FINISHED"}

    def find_node_groups(self):
        return bpy.data.node_groups.get(NAME_NODE_GROUP_UV_MESH)

    def find_modifier(self, obj):
        return obj.modifiers.get(NAME_MOD_UV_MESH)

    def create_new_geometry_node(self):
        blend_path = os.path.join(BLEND_DIR, "mio3uv.blend")
        try:
            bpy.ops.object.mode_set(mode="OBJECT")
            bpy.ops.wm.append(
                filename=NAME_NODE_GROUP_UV_MESH,
                directory=os.path.join(blend_path, "NodeTree"),
                link=False,
            )
            node_group = bpy.data.node_groups.get(NAME_NODE_GROUP_UV_MESH)
            node_group.use_fake_user = True
            bpy.ops.object.mode_set(mode="EDIT")

            return node_group
        except:
            self.report({"ERROR"}, "Failed import node group")
        return None


class MIO3UV_OT_uvmesh_cotrol(Mio3UVOperator):
    bl_idname = "mesh.mio3_uvmesh_cotrol"
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
                "mesh.mio3_uvmesh_cotrol",
                text="",
                icon_value=icons["UNFOLDIFY"].icon_id if props_object.uvmesh_factor > 0 else icons["CUBE"].icon_id,
                depress=True if props_object.uvmesh_factor > 0 else False,
            ).mode = "TOGGLE"


classes = [MIO3UV_OT_uvmesh, MIO3UV_OT_uvmesh_cotrol, MIO3UV_OT_uvmesh_clear]


def register():
    for c in classes:
        bpy.utils.register_class(c)
    bpy.types.VIEW3D_HT_tool_header.append(panel_tools)


def unregister():
    bpy.types.VIEW3D_HT_tool_header.remove(panel_tools)
    for c in classes:
        bpy.utils.unregister_class(c)
