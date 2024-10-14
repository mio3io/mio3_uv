import bpy
import os
from ..classes.operator import Mio3UVOperator

CHECKER_MAP_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "images", "checker_maps")


class MIO3UV_OT_color_grid(Mio3UVOperator):
    bl_idname = "mio3uv.color_grid"
    bl_label = "Align Rotate"
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

        existing_material = self.find_existing_material()

        if existing_material:
            mat = existing_material
        else:
            mat = self.create_new_material()

        if obj.data.materials:
            obj.data.materials[0] = mat
        else:
            obj.data.materials.append(mat)

        for area in context.screen.areas:
            if area.type == "VIEW_3D":
                with context.temp_override(area=area):
                    area.spaces.active.shading.type = "MATERIAL"
                break

        return {"FINISHED"}

    def find_existing_material(self):
        material_name = "Mio3UVColorGridMaterial_{}".format(self.size)
        return bpy.data.materials.get(material_name)

    def create_new_material(self):
        material_name = "Mio3UVColorGridMaterial_{}".format(self.size)
        mat = bpy.data.materials.new(name=material_name)
        mat.use_nodes = True

        nodes = mat.node_tree.nodes
        links = mat.node_tree.links

        nodes.clear()

        tex_coord_node = nodes.new(type="ShaderNodeTexCoord")
        image_node = nodes.new(type="ShaderNodeTexImage")
        bsdf_node = nodes.new(type="ShaderNodeBsdfPrincipled")
        output_node = nodes.new(type="ShaderNodeOutputMaterial")

        tex_coord_node.location = (-400, 0)
        image_node.location = (-240, 0)
        bsdf_node.location = (20, 0)
        output_node.location = (280, 0)

        image_name = "chocomint_{}.png".format(self.size)
        image_path = os.path.join(bpy.path.abspath(CHECKER_MAP_DIR), image_name)

        if os.path.exists(image_path):
            image = bpy.data.images.load(image_path)
        else:
            self.report({"WARNING"}, "Image not found: {}. Using default color grid.".format(image_path))
            image = bpy.data.images.new("Mio3UColorGridTexture_{}".format(self.size), width=self.size, height=self.size)
            image.generated_type = "COLOR_GRID"

        image_node.image = image

        links.new(tex_coord_node.outputs["UV"], image_node.inputs["Vector"])
        links.new(image_node.outputs["Color"], bsdf_node.inputs["Base Color"])
        links.new(bsdf_node.outputs["BSDF"], output_node.inputs["Surface"])

        return mat


classes = [MIO3UV_OT_color_grid]


def register():
    for c in classes:
        bpy.utils.register_class(c)


def unregister():
    for c in classes:
        bpy.utils.unregister_class(c)
