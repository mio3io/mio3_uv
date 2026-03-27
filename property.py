import bpy
from bpy.app.handlers import persistent
from bpy.types import PropertyGroup
from bpy.props import BoolProperty, FloatProperty, EnumProperty, PointerProperty
from .icons import icons
from .operators import view_padding
from .globals import get_preferences


ITEMS_TEXTURE_SIZE = [
    ("512", "512", ""),
    ("1024", "1024", ""),
    ("2048", "2048", ""),
    ("4096", "4096", ""),
    ("8192", "8192", ""),
]


class SCENE_PG_mio3uv(PropertyGroup):
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

    udim: BoolProperty(name="Use UV Tiles", description="Use UDIM UV Tiles", default=False)

    def symmetry_uv_axis_items(self, context):
        return [
            ("X", "X", "", icons.axis_x, 0),
            ("Y", "Y", "", icons.axis_y, 1),
        ]

    symmetry_uv_axis: EnumProperty(
        name="Axis",
        description="Axis of symmetry in UV space",
        items=symmetry_uv_axis_items,
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
    checker_map_size: EnumProperty(
        name="Size",
        description="Choose an image size",
        items=ITEMS_TEXTURE_SIZE,
        default=2,
    )
    use_exposure: BoolProperty(
        name="Exposure",
        default=False,
        description="Adjusts Exposure if image is set",
    )  # Dummy Property

    def callback_update_exposure(self, context):
        context.scene.view_settings.exposure = self.exposure

    exposure: FloatProperty(name="Exposure Level", default=-5, min=-7, max=5, step=10, update=callback_update_exposure)

    def callback_update_texture_size_x(self, context):
        if self.texture_size_link:
            current_index = [i for i, item in enumerate(ITEMS_TEXTURE_SIZE) if item[0] == self.texture_size_x][0]
            self["texture_size_y"] = current_index

    def callback_update_texture_size_y(self, context):
        if self.texture_size_link:
            current_index = [i for i, item in enumerate(ITEMS_TEXTURE_SIZE) if item[0] == self.texture_size_y][0]
            self["texture_size_x"] = current_index

    texture_size_x: EnumProperty(
        name="Size X", items=ITEMS_TEXTURE_SIZE, default="2048", update=callback_update_texture_size_x
    )
    texture_size_y: EnumProperty(
        name="Size Y", items=ITEMS_TEXTURE_SIZE, default="2048", update=callback_update_texture_size_y
    )
    texture_size_link: BoolProperty(name="Size Link", default=True)
    texel_density: FloatProperty(name="Texel Density", default=256, min=0.01, max=10000, step=10, precision=1)


class OBJECT_PG_mio3uv(PropertyGroup):
    def callback_update_padding(self, context):
        view_padding.UV_OT_mio3_guide_padding.redraw(context)

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
        items=ITEMS_TEXTURE_SIZE,
        default=2,
        update=callback_update_padding,
    )

    padding_px: EnumProperty(
        name="Padding",
        items=[
            ("AUTO", "Auto", ""),
            ("4", "4", ""),
            ("8", "8", ""),
            ("16", "16", ""),
            ("32", "32", ""),
            ("64", "64", ""),
        ],
        default="AUTO",
        update=callback_update_padding,
    )

    uvmesh_factor: FloatProperty(name="Factor", default=1, min=0, max=1, update=callback_update_uvmesh_factor)
    uvmesh_size: FloatProperty(
        name="Size", description="1 = 1m", default=2, min=0.1, max=200, update=callback_update_uvmesh_size
    )


class IMAGE_PG_mio3uv(PropertyGroup):
    def callback_update_use_exposure(self, context):
        if hasattr(context, "edit_image"):
            context.edit_image.use_view_as_render = self.use_exposure
            context.scene.mio3uv.use_exposure = self.use_exposure
            context.scene.view_settings.exposure = context.scene.mio3uv.exposure if self.use_exposure else 0

    use_exposure: BoolProperty(
        name="Exposure",
        default=False,
        update=callback_update_use_exposure,
        description="Adjusts Exposure if image is set",
    )

    @classmethod
    def reset_images(cls):
        for img in bpy.data.images:
            if hasattr(img, "mio3uv") and img.mio3uv.use_exposure:
                img.use_view_as_render = False
                img.mio3uv.use_exposure = False
        for scene in bpy.data.scenes:
            if hasattr(scene, "mio3uv") and scene.mio3uv.use_exposure:
                scene.view_settings.exposure = 0


class WM_PG_mio3uv(PropertyGroup):
    texel_preset_buttons: BoolProperty(
        name="Show Preset Buttons", default=False, description="Show quick set buttons for common texel densities"
    )
    texel_density_coverage_type: EnumProperty(
        name="Type",
        description="Calculate UV coverage inside the 0-1 UV space based on visible or selected UV faces",
        items=[
            ("VISIBLE", "Visible", ""),
            ("SELECT", "Selected", ""),
        ],
    )
    texel_density_percent: FloatProperty(name="Coverage", default=0, precision=4, subtype="PERCENTAGE")
    texel_use_checker: BoolProperty(
        name="Use Checker Size",
        description="Use Mio3UV checker size if available. \nDisable if the actual texture size differs from the checker size",
        default=False,
    )


def callback_use_uv_select_sync():
    pref = get_preferences()
    if pref.auto_uv_sync:
        bpy.ops.uv.mio3_auto_uv_sync("EXEC_DEFAULT")


msgbus_owner = object()


def handler_register():
    bpy.msgbus.clear_by_owner(msgbus_owner)
    bpy.msgbus.subscribe_rna(
        key=(bpy.types.ToolSettings, "use_uv_select_sync"),
        owner=msgbus_owner,
        args=(),
        notify=callback_use_uv_select_sync,
    )
    if load_handler not in bpy.app.handlers.load_post:
        bpy.app.handlers.load_post.append(load_handler)


@persistent
def load_handler(scene):
    handler_register()


classes = [
    SCENE_PG_mio3uv,
    OBJECT_PG_mio3uv,
    IMAGE_PG_mio3uv,
    WM_PG_mio3uv,
]


def register():
    for c in classes:
        bpy.utils.register_class(c)
    bpy.types.WindowManager.mio3uv = PointerProperty(type=WM_PG_mio3uv)
    bpy.types.Scene.mio3uv = PointerProperty(type=SCENE_PG_mio3uv)
    bpy.types.Object.mio3uv = PointerProperty(type=OBJECT_PG_mio3uv)
    bpy.types.Image.mio3uv = PointerProperty(type=IMAGE_PG_mio3uv)
    handler_register()


def unregister():
    IMAGE_PG_mio3uv.reset_images()
    del bpy.types.Image.mio3uv
    del bpy.types.Object.mio3uv
    del bpy.types.Scene.mio3uv
    del bpy.types.WindowManager.mio3uv
    for c in classes:
        bpy.utils.unregister_class(c)

    bpy.msgbus.clear_by_owner(msgbus_owner)
    bpy.app.handlers.load_post.remove(load_handler)
