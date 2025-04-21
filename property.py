import bpy
import bmesh
from bpy.app.handlers import persistent
from bpy.types import PropertyGroup
from bpy.props import BoolProperty, FloatProperty, IntProperty, EnumProperty, PointerProperty
from .icons import preview_collections
from .operators import view_padding
from .globals import get_preferences


ITEMS_TEXTURE_SIZE = [
    ("512", "512", "512x512 (4px)"),
    ("1024", "1024", "1024x1024 (8px)"),
    ("2048", "2048", "2048x2048 (16px)"),
    ("4096", "4096", "4096x4096 (32px)"),
    ("8192", "8192", "8192x8192 (64px)"),
]


class MIO3UV_PG_scene(PropertyGroup):
    def callback_update_exposure(self, context):
        context.scene.view_settings.exposure = self.exposure

    # auto_uv_sync: BoolProperty(name="UV Sync Auto Select", default=False)
    auto_uv_sync_skip: BoolProperty(name="UV Sync Auto Select Skip", default=False)

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
    checker_map_size: EnumProperty(
        name="Checker Map Size",
        description="Choose an image size",
        items=ITEMS_TEXTURE_SIZE,
        default="1024",
    )
    use_exposure: BoolProperty(
        name="Exposure",
        default=False,
        description="Adjusts Exposure if image is set",
    )  # Dummy Property
    exposure: FloatProperty(name="Exposure Level", default=-5, min=-7, max=5, step=10, update=callback_update_exposure)


class MIO3UV_PG_object(PropertyGroup):
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

    def callback_update_texture_size_x(self, context):
        if self.texture_size_link:
            current_index = [i for i, item in enumerate(ITEMS_TEXTURE_SIZE) if item[0] == self.texture_size_x][0]
            self["texture_size_y"] = current_index

    def callback_update_texture_size_y(self, context):
        if self.texture_size_link:
            current_index = [i for i, item in enumerate(ITEMS_TEXTURE_SIZE) if item[0] == self.texture_size_y][0]
            self["texture_size_x"] = current_index

    texture_size_x: EnumProperty(
        name="Size X",
        description="Choose an image size",
        items=ITEMS_TEXTURE_SIZE,
        default="1024",
        update=callback_update_texture_size_x,
    )
    texture_size_y: EnumProperty(
        name="Size Y",
        description="Choose an image size",
        items=ITEMS_TEXTURE_SIZE,
        default="1024",
        update=callback_update_texture_size_y,
    )
    texture_size_link: BoolProperty(name="Size Link", default=True)

    image_size: EnumProperty(
        name="Size",
        description="Choose an image size",
        items=ITEMS_TEXTURE_SIZE,
        default=1,
        update=callback_update_padding,
    )

    padding_px: EnumProperty(
        name="Padding (px)",
        items=[("4", "4", ""), ("8", "8", ""), ("16", "16", ""), ("32", "32", ""), ("64", "64", "")],
        default="16",
        update=callback_update_padding,
    )

    uvmesh_factor: FloatProperty(name="Factor", default=1, min=0, max=1, update=callback_update_uvmesh_factor)
    uvmesh_size: FloatProperty(
        name="Size", description="1 = 1m", default=2, min=0.1, max=200, update=callback_update_uvmesh_size
    )


class MIO3UV_PG_image(PropertyGroup):
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


def callback_use_uv_select_sync():
    pref = get_preferences()
    context = bpy.context
    props_s = context.scene.mio3uv
    if pref.auto_uv_sync:
        if not props_s.auto_uv_sync_skip:
            bpy.ops.uv.mio3_auto_uv_sync("EXEC_DEFAULT")
    props_s.auto_uv_sync_skip = False


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
    MIO3UV_PG_scene,
    MIO3UV_PG_object,
    MIO3UV_PG_image,
]


def register():
    for c in classes:
        bpy.utils.register_class(c)
    bpy.types.Scene.mio3uv = PointerProperty(type=MIO3UV_PG_scene)
    bpy.types.Object.mio3uv = PointerProperty(type=MIO3UV_PG_object)
    bpy.types.Image.mio3uv = PointerProperty(type=MIO3UV_PG_image)
    handler_register()


def unregister():
    MIO3UV_PG_image.reset_images()
    del bpy.types.Image.mio3uv
    del bpy.types.Object.mio3uv
    del bpy.types.Scene.mio3uv
    for c in classes:
        bpy.utils.unregister_class(c)

    bpy.msgbus.clear_by_owner(msgbus_owner)
    bpy.app.handlers.load_post.remove(load_handler)
