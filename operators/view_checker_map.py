import bpy
import os
from ..classes.operator import Mio3UVGlobalOperator

CHECKER_MAP_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "images", "checker_maps")
BLEND_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "blend")
NAME_NODE_GROUP_OVERRIDE = "Mio3MaterialOverride"
NAME_MOD_CHECKER_MAP = "Mio3CheckerMapModifier"


class MIO3UV_OT_checker_map(Mio3UVGlobalOperator):
    bl_idname = "mio3uv.checker_map"
    bl_label = "Checker Map"
    bl_description = "Set the checker map (using Geometry Nodes)"
    bl_options = {"REGISTER", "UNDO"}

    size = None

    @classmethod
    def poll(cls, context):
        obj = context.active_object
        return obj is not None and obj.type == "MESH"

    def execute(self, context):
        selected_objects = [obj for obj in context.selected_objects if obj.type == "MESH"]
        if not selected_objects:
            return {"CANCELLED"}

        self.size = int(context.scene.mio3uv.checker_map_size)

        mode = context.active_object.mode
        if mode != "OBJECT":
            bpy.ops.object.mode_set(mode="OBJECT")

        existing_material = self.get_material()
        if existing_material:
            mat = existing_material
        else:
            mat = self.create_new_material()

        existing_geometry_node = self.get_node_groups()
        if existing_geometry_node:
            geometry_node = existing_geometry_node
        else:
            geometry_node = self.create_new_geometry_node(context)

        for obj in selected_objects:
            existing_modifier = self.get_modifier(obj)
            if existing_modifier:
                obj.modifiers.remove(existing_modifier)

            modifier = obj.modifiers.new(name=NAME_MOD_CHECKER_MAP, type="NODES")
            modifier.show_expanded = False
            modifier.node_group = geometry_node
            modifier["Socket_2"] = mat
            obj.select_set(True)

        if mode != "OBJECT":
            bpy.ops.object.mode_set(mode="EDIT")

        return {"FINISHED"}

    def get_material(self):
        return bpy.data.materials.get("Mio3CheckerMapMat_{}".format(self.size))

    def get_node_groups(self):
        return bpy.data.node_groups.get(NAME_NODE_GROUP_OVERRIDE)

    def get_modifier(self, obj):
        return obj.modifiers.get(NAME_MOD_CHECKER_MAP)

    def create_new_geometry_node(self, context):
        blend_path = os.path.join(BLEND_DIR, "mio3uv.blend")
        try:
            bpy.ops.wm.append(
                filename=NAME_NODE_GROUP_OVERRIDE,
                directory=os.path.join(blend_path, "NodeTree"),
                link=False,
            )
            node_group = bpy.data.node_groups.get(NAME_NODE_GROUP_OVERRIDE)
            node_group.use_fake_user = True
            return node_group
        except:
            self.report({"ERROR"}, "Failed import node group")
        return None

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


class MIO3UV_OT_checker_map_clear(Mio3UVGlobalOperator):
    bl_idname = "mio3uv.checker_map_clear"
    bl_label = "Clear Checker Map"
    bl_description = "Clear Checker Map"
    bl_options = {"REGISTER", "UNDO", "INTERNAL"}

    @classmethod
    def poll(cls, context):
        obj = context.active_object
        return obj is not None

    def execute(self, context):
        selected_objects = [obj for obj in context.selected_objects if obj.type == "MESH"]
        if not selected_objects:
            return {"CANCELLED"}
        
        for obj in selected_objects:
            modifier = obj.modifiers.get(NAME_MOD_CHECKER_MAP)
            if modifier:
                obj.modifiers.remove(modifier)
        return {"FINISHED"}


class MIO3UV_OT_checker_map_cleanup(Mio3UVGlobalOperator):
    bl_idname = "mio3uv.checker_map_cleanup"
    bl_label = "Cleanup Checker Maps"
    bl_description = "Cleanup Checker Maps"
    bl_options = {"REGISTER", "UNDO", "INTERNAL"}

    @classmethod
    def poll(cls, context):
        return context.active_object is not None
    
    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self)

    def execute(self, context):
        removed_modifiers = 0
        removed_nodegroups = 0
        removed_materials = 0
        removed_images = 0

        for obj in bpy.data.objects:
            for mod in obj.modifiers[:]:
                if mod.name == NAME_MOD_CHECKER_MAP:
                    obj.modifiers.remove(mod)
                    removed_modifiers += 1

        if NAME_NODE_GROUP_OVERRIDE in bpy.data.node_groups:
            bpy.data.node_groups.remove(bpy.data.node_groups[NAME_NODE_GROUP_OVERRIDE])
            removed_nodegroups += 1

        for mat in bpy.data.materials[:]:
            if mat.name.startswith("Mio3CheckerMapMat_"):
                bpy.data.materials.remove(mat)
                removed_materials += 1

        checker_path_pattern = os.path.join("mio3_uv", "images", "checker_maps")
        normalized_pattern = checker_path_pattern.replace(os.path.sep, "/")
        for img in bpy.data.images[:]:
            if img.filepath:
                normalized_path = img.filepath.replace("\\", "/")
                if normalized_pattern in normalized_path:
                    bpy.data.images.remove(img)
                    removed_images += 1

        self.report(
            {"INFO"},
            "Cleanup: Modifier {}, Node Group {}, Material {}, Image {}".format(
                removed_modifiers,
                removed_nodegroups,
                removed_materials,
                removed_images,
            ),
        )

        return {"FINISHED"}


classes = [
    MIO3UV_OT_checker_map,
    MIO3UV_OT_checker_map_clear,
    MIO3UV_OT_checker_map_cleanup,
]


def register():
    for c in classes:
        bpy.utils.register_class(c)


def unregister():
    for c in classes:
        bpy.utils.unregister_class(c)
