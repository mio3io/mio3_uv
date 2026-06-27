import bpy
from mathutils import Vector
from bpy.props import BoolProperty, FloatProperty, EnumProperty, FloatVectorProperty
from ..classes import Mio3UVOperator, UVIslandManager


class UV_OT_mio3_paste(Mio3UVOperator):
    bl_idname = "uv.mio3_paste"
    bl_label = "Paste"
    bl_description = "Paste selected UV vertices"
    bl_options = {"REGISTER", "UNDO"}

    mode: EnumProperty(
        name="Mode", items=[("PASTE", "Paste", ""), ("AUTO", "Auto", "")], default="PASTE", options={"HIDDEN"}
    )
    keep_position: BoolProperty(name="Keep Position", default=True)

    def execute(self, context):
        objects = self.get_selected_objects(context)
        use_uv_select_sync = context.tool_settings.use_uv_select_sync

        island_manager = UVIslandManager(objects, sync=use_uv_select_sync)
        if self.mode == "AUTO":
            bpy.ops.uv.copy()

        bpy.ops.uv.paste()

        if self.keep_position:
            for island in island_manager.islands:
                island.update_bounds()
                offset = island.original_center - island.center
                island.move(offset)

        island_manager.update_uvmeshes()

        return {"FINISHED"}


class UV_OT_mio3_stack(Mio3UVOperator):
    bl_idname = "uv.mio3_stack"
    bl_label = "Stack"
    bl_description = "Overlap similar UV shapes"
    bl_options = {"REGISTER", "UNDO"}

    selected: BoolProperty(name="Selected Only", default=False)
    use_offset: BoolProperty(name="Offset", default=False)
    offset: FloatVectorProperty(name="Offset", size=2, default=(1.0, 0.0))

    def execute(self, context):
        self.start_time()
        self.objects = self.get_selected_objects(context)
        use_uv_select_sync = context.tool_settings.use_uv_select_sync

        island_manager = UVIslandManager(self.objects, sync=use_uv_select_sync, find_all=True)

        selected_islands = [i for i in island_manager.islands if i.is_any_uv_selected()]
        among_islands = selected_islands if self.selected else island_manager.islands

        bpy.ops.uv.copy()

        processed = set()
        stacked_islands = set(selected_islands)
        for source_island in selected_islands:
            if source_island in processed:
                continue
            base_face_count = len(source_island.faces)

            for island in among_islands:
                if island == source_island:
                    continue
                if not self.is_different(island, base_face_count):
                    island.uv_select_set_all(True)
                    for face in island.faces:
                        face.select = True
                    processed.add(island)
                    stacked_islands.add(island)

        bpy.ops.uv.paste()

        if self.use_offset:
            ordered_islands = [island for island in island_manager.islands if island in stacked_islands]
            for i, island in enumerate(ordered_islands):
                island.move(Vector(self.offset) * i)

        island_manager.update_uvmeshes()
        self.end_time()
        return {"FINISHED"}

    def is_different(self, island, base_face_count):
        if len(island.faces) != base_face_count:
            return True
        return False

    def draw(self, context):
        layout = self.layout
        layout.use_property_decorate = False
        layout.use_property_split = True
        layout.prop(self, "selected")
        layout.prop(self, "use_offset")
        col = layout.column(align=True)
        if not self.use_offset:
            col.enabled = False
        col.prop(self, "offset", index=0, text="Offset X")
        col.prop(self, "offset", index=1, text="Y")


classes = [
    UV_OT_mio3_paste,
    UV_OT_mio3_stack,
]


def register():
    for c in classes:
        bpy.utils.register_class(c)


def unregister():
    for c in classes:
        bpy.utils.unregister_class(c)
