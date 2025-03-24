import bpy
import bmesh
from bpy.app.handlers import persistent
from bpy.types import PropertyGroup
from bpy.props import BoolProperty, FloatProperty, IntProperty, EnumProperty, PointerProperty
from .icons import preview_collections
from .operators import view_padding
from .utils import sync_uv_from_mesh_obj, sync_mesh_from_uv_obj


def items_checker_maps(self, context):
    return [
        ("512", "512", "512x512 (4px)"),
        ("1024", "1024", "1024x1024 (8px)"),
        ("2048", "2048", "2048x2048 (16px)"),
        ("4096", "4096", "4096x4096 (32px)"),
        ("8192", "8192", "8192x8192 (64px)"),
    ]


class MIO3UV_PG_scene(PropertyGroup):
    def callback_update_exposure(self, context):
        context.scene.view_settings.exposure = self.exposure

    auto_uv_sync: BoolProperty(name="UV Sync Auto Select", default=True)
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
        items=items_checker_maps,
        default=1,
    )
    use_exposure: BoolProperty(name="Exposure", description="Default", default=False)  # Dummy Property
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
    image_size: EnumProperty(
        name="Size",
        description="Choose an image size",
        items=items_checker_maps,
        default=1,
        update=callback_update_padding,
    )
    padding_px: IntProperty(name="Padding (px)", default=16, update=callback_update_padding)
    uvmesh_factor: FloatProperty(name="Factor", default=1, min=0, max=1, update=callback_update_uvmesh_factor)
    uvmesh_size: FloatProperty(name="Size", default=2, min=1, max=100, update=callback_update_uvmesh_size)


class MIO3UV_PG_image(PropertyGroup):
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



def callback_use_uv_select_sync():
    context = bpy.context
    props_s = context.scene.mio3uv
    # print("callback_use_uv_select_sync [{}]".format(str(props_s.auto_uv_sync_skip)))

    if props_s.auto_uv_sync:
        if not props_s.auto_uv_sync_skip:
            if context.scene.tool_settings.use_uv_select_sync:
                selected_objects = [obj for obj in context.objects_in_mode if obj.type == "MESH"]
                for obj in selected_objects:
                    sync_mesh_from_uv_obj(obj)
                    obj.data.update()
            else:
                selected_objects = [obj for obj in context.objects_in_mode if obj.type == "MESH"]
                for obj in selected_objects:
                    sync_uv_from_mesh_obj(obj)
                    bm = bmesh.from_edit_mesh(obj.data)
                    for face in bm.faces:
                        face.select = True
                    bm.select_flush(True)
                    bmesh.update_edit_mesh(obj.data)

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
