import bpy
from mathutils import Vector
from bpy.props import BoolProperty, FloatProperty
from ..classes import Mio3UVOperator, UVIslandManager
from ..utils.utils import find_uv_boundary_edges


class UV_OT_mio3_offset(Mio3UVOperator):
    bl_idname = "uv.mio3_offset"
    bl_label = "Offset"
    bl_description = "Expand/Shrink UV Borders. Ensure space for the overlapping rim created by Solidify."
    bl_options = {"REGISTER", "UNDO"}

    offset: FloatProperty(
        name="Offset",
        description="Offset to expand UV boundary.",
        default=0.005,
        min=-1.0,
        max=1.0,
        step=0.01,
        precision=3,
    )
    keep_pin: BoolProperty(name="Keep Pin", default=False)

    def execute(self, context):
        self.start_time()
        objects = self.get_selected_objects(context)

        use_uv_select_sync = context.tool_settings.use_uv_select_sync

        island_manager = UVIslandManager(objects, sync=use_uv_select_sync)

        for island in island_manager.islands:
            self.expand_uv_boundary(island, self.offset)

        island_manager.update_uvmeshes(True)

        self.end_time()
        return {"FINISHED"}

    def expand_uv_boundary(self, island, offset):
        uv_layer = island.uv_layer

        faces = {f for f in island.faces if f.select}
        boundary_edges = find_uv_boundary_edges(faces, uv_layer)

        def uv_key(loop):
            uv = loop[uv_layer].uv
            return (loop.vert.index, round(uv.x, 6), round(uv.y, 6))

        uv_groups = {}
        for face in faces:
            for loop in face.loops:
                uv_groups.setdefault(uv_key(loop), []).append(loop)

        group_perps = {}
        for edge in boundary_edges:
            for loop in edge.link_loops:
                if loop.face not in faces:
                    continue
                loop1 = loop
                loop2 = loop.link_loop_next
                if not (loop1.uv_select_vert and loop2.uv_select_vert):
                    continue

                uv1 = loop1[uv_layer].uv
                uv2 = loop2[uv_layer].uv
                edge_vec = uv2 - uv1
                length = edge_vec.length
                if length < 1e-10:
                    continue
                edge_vec = edge_vec / length
                perp = Vector((edge_vec.y, -edge_vec.x))

                face_loops = loop.face.loops
                n = len(face_loops)
                cx = sum(l[uv_layer].uv.x for l in face_loops) / n
                cy = sum(l[uv_layer].uv.y for l in face_loops) / n
                mid_x = (uv1.x + uv2.x) * 0.5
                mid_y = (uv1.y + uv2.y) * 0.5
                if perp.x * (mid_x - cx) + perp.y * (mid_y - cy) < 0.0:
                    perp = -perp

                key1, key2 = uv_key(loop1), uv_key(loop2)
                group_perps.setdefault(key1, []).append(perp)
                group_perps.setdefault(key2, []).append(perp)

        for key, perps in group_perps.items():
            p1 = perps[0]
            p2 = perps[1] if len(perps) > 1 else p1
            s = p1 + p2
            denom = 1.0 + p1.dot(p2)
            movement = s * (offset / denom) if denom > 1e-6 else s * (0.5 * offset)
            for loop in uv_groups.get(key, ()):
                if self.keep_pin and loop[uv_layer].pin_uv:
                    continue
                loop[uv_layer].uv += movement


def register():
    bpy.utils.register_class(UV_OT_mio3_offset)


def unregister():
    bpy.utils.unregister_class(UV_OT_mio3_offset)
