import bpy
from bpy.props import EnumProperty, BoolProperty
from bpy.app.translations import pgettext_iface as tt_iface
from mathutils import Vector
from ..classes import UVIslandManager, Mio3UVOperator


class MIO3UV_OT_unwrap(Mio3UVOperator):
    bl_idname = "uv.mio3_unwrap"
    bl_label = "UV Unwrap"
    bl_description = "UV Unwrap"
    bl_options = {"REGISTER", "UNDO"}

    @classmethod
    def description(cls, context, properties):
        if properties.axis == "X":
            return tt_iface("Unwrap Horizontal(X) Only")
        elif properties.axis == "Y":
            return tt_iface("Unwrap Vertical(Y) Only")
        return tt_iface("UV Unwrap")

    method: EnumProperty(
        name="Method",
        items=[
            ("ANGLE_BASED", "Angle Based", "Angle based unwrapping method"),
            ("CONFORMAL", "Conformal", "Conformal mapping method"),
            ("MINIMUM_STRETCH", "Minimum Stretch", "Minimum stretch mapping method"),
        ],
    )
    axis: EnumProperty(
        name="Direction",
        items=[
            ("BOTH", "Both", ""),
            ("X", "X", ""),
            ("Y", "Y", ""),
        ],
    )
    keep_position: BoolProperty(name="Position", description="Keep UV position", default=True)
    keep_scale: BoolProperty(name="Scale", description="Keep UV scale", default=True)
    keep_rotate: BoolProperty(name="Angle", description="Keep UV angle", default=True)
    merge_uv: BoolProperty(name="Merge Seamless Parts", description="Treat islands without seams as one island", default=False)

    @classmethod
    def poll(cls, context):
        return cls.is_valid_object(context.active_object)

    def execute(self, context):
        self.start_time()
        objects = self.get_selected_objects(context)

        for obj in objects:
            if not obj.data.uv_layers:
                bpy.ops.uv.unwrap(method=self.method, margin=0.001)
                return {"FINISHED"}

        use_uv_select_sync = context.tool_settings.use_uv_select_sync

        island_manager = UVIslandManager(objects, sync=use_uv_select_sync, uv_split=not self.merge_uv)

        axis = self.axis
        use_keep = self.keep_position or self.keep_scale or self.keep_rotate

        original_axis_uvs = {}
        original_keep_samples = {}
        for island in island_manager.islands:
            island.inplace_flag = use_keep and self.should_restore(island)

            if axis != "BOTH":
                original_uvs_island = []
                uv_layer = island.uv_layer
                for face in island.faces:
                    for loop in face.loops:
                        if loop.uv_select_vert:
                            original_uvs_island.append((loop, loop[uv_layer].uv.copy()))
                original_axis_uvs[island] = original_uvs_island

            if island.inplace_flag:
                original_keep_samples[island] = self.capture_uv_samples(island)

        bpy.ops.uv.unwrap(method=self.method, margin=0.001)

        for island in island_manager.islands:
            if island.inplace_flag:
                self.apply_transform(island, original_keep_samples[island])
            if axis != "BOTH":
                uv_layer = island.uv_layer
                for loop, orig_uv in original_axis_uvs.get(island, ()):
                    curr_uv = loop[uv_layer].uv
                    if axis == "X":
                        curr_uv.y = orig_uv.y
                    elif axis == "Y":
                        curr_uv.x = orig_uv.x

        island_manager.update_uvmeshes(True)

        self.print_time()
        return {"FINISHED"}

    def should_restore(self, island):
        uv_layer = island.uv_layer

        pinned_nodes = set()
        deselect_count = 0
        for face in island.faces:
            for loop in face.loops:
                loop_uv = loop[uv_layer]
                if loop_uv.pin_uv:
                    pinned_nodes.add((loop.vert.index, loop_uv.uv.x, loop_uv.uv.y))
                if not loop.uv_select_vert:
                    deselect_count += 1
                    if deselect_count >= 2:
                        return False

        if len(pinned_nodes) >= 2:
            return False

        return True

    def capture_uv_samples(self, island):
        uv_samples = []
        uv_layer = island.uv_layer
        for face in island.faces:
            for loop in face.loops:
                uv_samples.append((loop, loop[uv_layer].uv.copy()))
        return uv_samples

    def apply_transform(self, island, uv_samples):
        pair_count = len(uv_samples)
        if pair_count < 2:
            return

        uv_layer = island.uv_layer
        original_center = Vector((0.0, 0.0))
        current_center = Vector((0.0, 0.0))
        for loop, orig_uv in uv_samples:
            curr_uv = loop[uv_layer].uv
            original_center += orig_uv
            current_center += curr_uv
        count = float(pair_count)
        original_center /= count
        current_center /= count

        denominator = 0.0
        for loop, _ in uv_samples:
            curr_uv = loop[uv_layer].uv
            curr = curr_uv - current_center
            denominator += curr.x * curr.x + curr.y * curr.y

        if denominator < 1e-20:
            base_cos_term = 1.0
            base_sin_term = 0.0
            scale = 1.0
        else:
            dot_sum = 0.0
            cross_sum = 0.0
            for loop, orig_uv in uv_samples:
                curr_uv = loop[uv_layer].uv
                orig = orig_uv - original_center
                curr = curr_uv - current_center
                dot_sum += curr.x * orig.x + curr.y * orig.y
                cross_sum += curr.x * orig.y - curr.y * orig.x

            base_cos_term = dot_sum / denominator
            base_sin_term = cross_sum / denominator
            scale = max((base_cos_term * base_cos_term + base_sin_term * base_sin_term) ** 0.5, 1e-8)

        if self.keep_rotate:
            scale_for_rotation = max(scale, 1e-8)
            rot_cos = base_cos_term / scale_for_rotation
            rot_sin = base_sin_term / scale_for_rotation
        else:
            rot_cos = 1.0
            rot_sin = 0.0

        final_scale = scale if self.keep_scale else 1.0
        cos_term = rot_cos * final_scale
        sin_term = rot_sin * final_scale

        if self.keep_position:
            target_center = original_center
        else:
            target_center = current_center

        tx = target_center.x - (cos_term * current_center.x - sin_term * current_center.y)
        ty = target_center.y - (sin_term * current_center.x + cos_term * current_center.y)

        if abs(cos_term - 1.0) < 1e-12 and abs(sin_term) < 1e-12 and abs(tx) < 1e-12 and abs(ty) < 1e-12:
            return

        for face in island.faces:
            for loop in face.loops:
                uv = loop[uv_layer].uv
                x = uv.x
                y = uv.y
                uv.x = cos_term * x - sin_term * y + tx
                uv.y = sin_term * x + cos_term * y + ty

    def draw(self, context):
        layout = self.layout
        layout.use_property_split = False
        layout.use_property_decorate = False

        split = layout.split(factor=0.3, align=True)
        split.alignment = "RIGHT"
        split.label(text="Method")
        split.prop(self, "method", text="")
        split = layout.split(factor=0.3, align=True)
        split.alignment = "RIGHT"
        split.label(text="Keep")
        row = split.row(align=True)
        row.prop(self, "keep_position", toggle=True)
        row.prop(self, "keep_scale", toggle=True)
        row.prop(self, "keep_rotate", toggle=True)
        split = layout.split(factor=0.3, align=True)
        split.alignment = "RIGHT"
        split.label(text="Direction")
        split.row().prop(self, "axis", expand=True)
        split = layout.split(factor=0.3, align=True)
        split.label(text="")
        split.prop(self, "merge_uv")


def register():
    bpy.utils.register_class(MIO3UV_OT_unwrap)


def unregister():
    bpy.utils.unregister_class(MIO3UV_OT_unwrap)
