import bpy
from bpy.types import PropertyGroup
from bpy.props import BoolProperty, FloatProperty, IntProperty, EnumProperty, PointerProperty
from .icons import preview_collections
from .operators import view_padding


class MIO3_UVProperties(PropertyGroup):
    def callback_update_exposure(self, context):
        context.scene.view_settings.exposure = self.exposure

    edge_mode: BoolProperty(name="Edge Mode", description="Edge Mode", default=False)
    island_mode: BoolProperty(name="Island Mode", description="Island Mode", default=False)

    align_mode: EnumProperty(
        name="Mode",
        items=[
            ("AUTO", "Auto", "Auto"),
            ("ISLAND", "Island", "Island"),
            ("GROUP", "Group", "Group"),
        ],
        default="AUTO",
    )

    def symmetry_center_items(self, context):
        icons = preview_collections["icons"]
        return [
            ("X", "X", "", icons["AXIS_X"].icon_id, 0),
            ("Y", "Y", "", icons["AXIS_Y"].icon_id, 1),
        ]

    udim: BoolProperty(name="UDIM", default=False)

    symmetry_center: EnumProperty(
        name="Center",
        items=[
            ("GLOBAL", "Center", "Center"),
            ("CURSOR", "Cursor", "2D Cursor"),
            ("SELECT", "Selection", "Bounding Box Center"),
        ],
        default="GLOBAL",
    )

    symmetry_uv_axis: EnumProperty(
        name="Axis",
        description="Axis of symmetry in UV space",
        items=symmetry_center_items,
        default=0,
    )
    symmetry_3d_axis: EnumProperty(
        name="Axis",
        description="Axis of symmetry in 3D space",
        items=[
            ("AUTO", "Auto", "Sync UV Axis"),
            ("X", "X", "X axis in 3D space"),
            ("Y", "Y", "Y axis in 3D space"),
            ("Z", "Z", "Z axis in 3D space"),
        ],
        default="AUTO",
    )
    use_exposure: BoolProperty(name="Exposure", description="Default", default=False) # Dummy Property
    exposure: FloatProperty(name="Exposure Level", default=-5, min=-7, max=5, step=10, update=callback_update_exposure)


class MIO3UV_ObjectProps(PropertyGroup):
    def callback_update_padding(self, context):
        view_padding.MIO3UV_OT_view_padding.redraw(context)

    def callback_update_uvmesh_factor(self, context):
        modifier = context.active_object.modifiers.get("Mio3UVMeshModifier")
        if modifier:
            node_group = modifier.node_group
            if hasattr(node_group, "interface"):
                modifier[node_group.interface.items_tree["Factor"].identifier] = self.uvmesh_factor
            else:
                modifier[node_group.inputs["Factor"].identifier] = self.uvmesh_factor

    def callback_update_uvmesh_size(self, context):
        modifier = context.active_object.modifiers.get("Mio3UVMeshModifier")
        if modifier:
            node_group = modifier.node_group
            if hasattr(node_group, "interface"):
                if node_group.interface.items_tree["Size"].socket_type == "NodeSocketInt":
                    node_group.interface.items_tree["Size"].socket_type = "NodeSocketFloat"
                modifier[node_group.interface.items_tree["Size"].identifier] = self.uvmesh_size
            else:
                if node_group.inputs["Size"].socket_type == "NodeSocketInt":
                    node_group.inputs["Size"].socket_type = "NodeSocketFloat"
                modifier[node_group.inputs["Size"].identifier] = self.uvmesh_size

    realtime: BoolProperty(name="Realtime", description="Warning: This option may poor performance", default=False)
    image_size: EnumProperty(
        name="Size",
        description="Choose an image size",
        items=[
            ("512", "512", "512x512 (4px)"),
            ("1024", "1024", "1024x1024 (8px)"),
            ("2048", "2048", "2048x2048 (16px)"),
            ("4096", "4096", "4096x4096 (32px)"),
            ("8192", "8192", "8192x8192 (64px)"),
        ],
        default="1024",
        update=callback_update_padding,
    )
    padding_px: IntProperty(name="Padding (px)", default=16, update=callback_update_padding)
    uvmesh_factor: FloatProperty(name="Factor", default=1, min=0, max=1, update=callback_update_uvmesh_factor)
    uvmesh_size: FloatProperty(name="Size", default=2, min=1, max=100, update=callback_update_uvmesh_size)


class MIO3UV_ImageProps(PropertyGroup):
    def callback_update_use_exposure(self, context):
        if hasattr(context, "edit_image"):
            context.edit_image.use_view_as_render = self.use_exposure
            context.scene.mio3uv.use_exposure = self.use_exposure
            context.scene.view_settings.exposure = context.scene.mio3uv.exposure if self.use_exposure else 0

    use_exposure: BoolProperty(name="Exposure", default=False, update=callback_update_use_exposure)

    @classmethod
    def reset_images(cls):
        for img in bpy.data.images:
            if hasattr(img, "mio3uv") and img.mio3uv.use_exposure:
                img.use_view_as_render = False
                img.mio3uv.use_exposure = False
        for scene in bpy.data.scenes:
            if hasattr(scene, "mio3uv") and scene.mio3uv.use_exposure:
                scene.view_settings.exposure = 0


classes = [MIO3_UVProperties, MIO3UV_ObjectProps, MIO3UV_ImageProps]


def register():
    for c in classes:
        bpy.utils.register_class(c)
    bpy.types.Scene.mio3uv = PointerProperty(type=MIO3_UVProperties)
    bpy.types.Object.mio3uv = PointerProperty(type=MIO3UV_ObjectProps)
    bpy.types.Image.mio3uv = PointerProperty(type=MIO3UV_ImageProps)


def unregister():
    MIO3UV_ImageProps.reset_images()
    del bpy.types.Image.mio3uv
    del bpy.types.Object.mio3uv
    del bpy.types.Scene.mio3uv
    for c in classes:
        bpy.utils.unregister_class(c)
