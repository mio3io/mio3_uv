import bpy
import os
from bpy.props import EnumProperty
from ..classes.operator import Mio3UVOperator

CHECKER_MAP_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "images", "checker_maps")


class MIO3UV_OT_checker_map(Mio3UVOperator):
    bl_idname = "mio3uv.checker_map"
    bl_label = "Cheker Maps"
    bl_description = ""
    bl_options = {"REGISTER", "UNDO"}

    size = 2048

    @classmethod
    def poll(cls, context):
        obj = context.active_object
        return obj is not None

    def execute(self, context):
        mio3uv = context.active_object.mio3uv

        obj = context.active_object

        self.size = int(mio3uv.image_size)

        existing_modifier = self.find_modifier(obj)
        if not existing_modifier:
            existing_material = self.find_material()
            if existing_material:
                mat = existing_material
            else:
                mat = self.create_new_material()

            existing_geometry_node = self.find_geometry_node()
            if existing_geometry_node:
                geometry_node = existing_geometry_node
            else:
                geometry_node = self.create_new_geometry_node(mat)

            modifier = obj.modifiers.new(name="Mio3CheckerMapModifier", type="NODES")
            modifier.node_group = geometry_node
            modifier["Socket_2"] = mat

        for area in context.screen.areas:
            if area.type == "VIEW_3D":
                if area.spaces.active.shading.type != "MATERIAL":
                    area.spaces.active.shading.type = "MATERIAL"
                area.tag_redraw()
                break

        return {"FINISHED"}

    def find_material(self):
        return bpy.data.materials.get("Mio3CheckerMapMat_{}".format(self.size))

    def find_geometry_node(self):
        return bpy.data.node_groups.get("Mio3CheckerMap")

    def find_modifier(self, obj):
        return obj.modifiers.get("Mio3CheckerMapModifier")

    def create_new_geometry_node(self, mat):
        node_group = bpy.data.node_groups.new(type="GeometryNodeTree", name="Mio3CheckerMap")
        node_group.is_modifier = True

        node_group.interface.new_socket(name="Geometry", in_out="OUTPUT", socket_type="NodeSocketGeometry")
        node_group.interface.new_socket(name="Geometry", in_out="INPUT", socket_type="NodeSocketGeometry")
        node_group.interface.new_socket(name="Material", in_out="INPUT", socket_type="NodeSocketMaterial")

        group_input = node_group.nodes.new("NodeGroupInput")
        node_set_material = node_group.nodes.new("GeometryNodeSetMaterial")
        group_output = node_group.nodes.new("NodeGroupOutput")

        group_input.location = (-200, 0)
        node_set_material.location = (0, 0)
        group_output.location = (200, 0)

        node_group.links.new(group_input.outputs[0], node_set_material.inputs[0])
        node_group.links.new(node_set_material.outputs[0], group_output.inputs[0])
        node_group.links.new(group_input.outputs[1], node_set_material.inputs[2])

        return node_group

    def create_new_material(self):
        mat = bpy.data.materials.new(name="Mio3CheckerMapMat_{}".format(self.size))
        mat.use_nodes = True

        nodes = mat.node_tree.nodes
        links = mat.node_tree.links

        nodes.clear()

        node_tex_coord = nodes.new(type="ShaderNodeTexCoord")
        node_mapping = nodes.new(type="ShaderNodeMapping")
        node_image = nodes.new(type="ShaderNodeTexImage")
        node_bsdf = nodes.new(type="ShaderNodeBsdfPrincipled")
        node_output = nodes.new(type="ShaderNodeOutputMaterial")

        node_tex_coord.location = (0, 0)
        node_mapping.location = (160, 0)
        node_image.location = (340, 0)
        node_bsdf.location = (600, 0)
        node_output.location = (860, 0)

        links.new(node_tex_coord.outputs["UV"], node_mapping.inputs["Vector"])
        links.new(node_mapping.outputs["Vector"], node_image.inputs["Vector"])
        links.new(node_image.outputs["Color"], node_bsdf.inputs["Base Color"])
        links.new(node_bsdf.outputs["BSDF"], node_output.inputs["Surface"])

        image_name = "chocomint_{}.png".format(self.size)
        image_path = os.path.join(bpy.path.abspath(CHECKER_MAP_DIR), image_name)

        if os.path.exists(image_path):
            image = bpy.data.images.load(image_path)
        else:
            self.report({"WARNING"}, "Image not found: {}. Using default color grid.".format(image_path))
            image = bpy.data.images.new("Mio3CheckerMapTex_{}".format(self.size), width=self.size, height=self.size)
            image.generated_type = "COLOR_GRID"

        node_image.image = image

        return mat


class MIO3UV_OT_checker_map_clear(Mio3UVOperator):
    bl_idname = "mio3uv.checker_map_clear"
    bl_label = "Clear Cheker Maps"
    bl_description = ""
    bl_options = {"REGISTER", "UNDO", "INTERNAL"}

    @classmethod
    def poll(cls, context):
        obj = context.active_object
        return obj is not None

    def execute(self, context):
        obj = context.active_object
        modifier = obj.modifiers.get("Mio3CheckerMapModifier")
        if not modifier:
            return {"CANCELLED"}

        obj.modifiers.remove(modifier)
        return {"FINISHED"}


classes = [MIO3UV_OT_checker_map, MIO3UV_OT_checker_map_clear]


def register():
    for c in classes:
        bpy.utils.register_class(c)


def unregister():
    for c in classes:
        bpy.utils.unregister_class(c)
