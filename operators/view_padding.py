import bpy
import bmesh
import gpu
from collections import defaultdict
from mathutils import Vector
from bpy.types import SpaceImageEditor
from gpu_extras.batch import batch_for_shader
from ..classes import Mio3UVOperator
from ..globals import PADDING_AUTO, get_preferences

msgbus_owner = object()


def reload_view(context):
    for window in context.window_manager.windows:
        for area in window.screen.areas:
            if area.type == "IMAGE_EDITOR":
                area.tag_redraw()


class UV_OT_mio3_guide_padding(Mio3UVOperator):
    bl_idname = "uv.mio3_guide_padding"
    bl_label = "Preview Padding"
    bl_description = "Preview the padding lines"
    bl_options = {"REGISTER", "UNDO"}

    _handle = None
    _color = (0.1, 0.5, 1.0, 1)
    _padding = 16 / 1024

    _shader = None
    _vertices = []
    _excluded_ops = {
        "UV_OT_select_linked",
        "UV_OT_select_more",
        "UV_OT_select_all",
    }

    @classmethod
    def is_running(cls):
        return cls._handle is not None

    @classmethod
    def is_relevant_uv_operator(cls, bl_idname):
        if bl_idname in cls._excluded_ops:
            return False
        return bl_idname.startswith(("TRANSFORM_OT_", "UV_OT_", "MIO3UV_"))

    @classmethod
    def remove_handler(cls):
        if cls.is_running():
            SpaceImageEditor.draw_handler_remove(cls._handle, "WINDOW")
            cls._handle = None
        bpy.msgbus.clear_by_owner(msgbus_owner)
        reload_view(bpy.context)

    def invoke(self, context, event):
        cls = self.__class__
        is_running = cls.is_running()
        cls.remove_handler()
        if is_running:
            return {"FINISHED"}

        prefs = get_preferences()
        cls._handle = SpaceImageEditor.draw_handler_add(self.draw_2d, ((self, context, prefs)), "WINDOW", "POST_PIXEL")

        def callback():
            cls.remove_handler()

        bpy.msgbus.subscribe_rna(key=(bpy.types.Object, "mode"), owner=msgbus_owner, args=(), notify=callback)

        self._shader = gpu.shader.from_builtin("UNIFORM_COLOR")
        self._prev_active_op_key = None

        self.update_state(context)
        self.update_mesh(context)
        reload_view(context)
        context.window_manager.modal_handler_add(self)
        return {"RUNNING_MODAL"}

    def modal(self, context, event):
        cls = self.__class__
        if not cls.is_running():
            return {"FINISHED"}

        active_op = getattr(context, "active_operator", None)
        current_active_op_key = (active_op.bl_idname, id(active_op)) if active_op else None
        is_new_active_op = current_active_op_key is not None and current_active_op_key != self._prev_active_op_key
        is_relevant_active_op = bool(active_op and cls.is_relevant_uv_operator(active_op.bl_idname))

        if is_new_active_op and is_relevant_active_op:
            self.update_mesh(context)

        if event.type == "RET" and event.value == "PRESS":
            self.update_mesh(context)

        if event.type == "Z" and event.ctrl and event.value == "RELEASE":
            self.update_mesh(context)

        self._prev_active_op_key = current_active_op_key
        return {"PASS_THROUGH"}

    @classmethod
    def redraw(cls, context):
        cls.update_state(context)
        cls.update_mesh(context)
        reload_view(context)

    @classmethod
    def update_mesh(cls, context):
        cls._vertices = []
        selected_objects = [obj for obj in context.selected_objects if obj.type == "MESH" and obj.mode == "EDIT"]
        padding = cls._padding

        for obj in selected_objects:
            obj.data.update()
            bm = bmesh.from_edit_mesh(obj.data)
            uv_layer = bm.loops.layers.uv.verify()

            edge_segs = defaultdict(list)
            uv_by_key = {}
            for face in bm.faces:
                for loop in face.loops:
                    uv1 = loop[uv_layer].uv.copy()
                    uv2 = loop.link_loop_next[uv_layer].uv.copy()
                    k1, k2 = uv1.to_tuple(5), uv2.to_tuple(5)
                    edge_segs[loop.edge].append((k1, k2))
                    uv_by_key.setdefault(k1, uv1)
                    uv_by_key.setdefault(k2, uv2)

            boundary_edges = set()
            for edge, segs in edge_segs.items():
                if edge.is_boundary or edge.seam or len(segs) != 2:
                    for k1, k2 in segs:
                        if k1 != k2:
                            boundary_edges.add(frozenset((k1, k2)))
                else:
                    (a1, a2), (b1, b2) = segs
                    if {a1, a2} != {b1, b2}:
                        for k1, k2 in segs:
                            if k1 != k2:
                                boundary_edges.add(frozenset((k1, k2)))

            neighbors = defaultdict(set)
            for e in boundary_edges:
                k1, k2 = tuple(e)
                neighbors[k1].add(k2)
                neighbors[k2].add(k1)

            unused = set(boundary_edges)

            def pop_next(curr, prev=None):
                for nxt in neighbors[curr]:
                    if nxt != prev and frozenset((curr, nxt)) in unused:
                        return nxt
                for nxt in neighbors[curr]:
                    if frozenset((curr, nxt)) in unused:
                        return nxt
                return None

            polylines = []
            for start in [k for k, ns in neighbors.items() if len(ns) == 1]:
                if not any(frozenset((start, n)) in unused for n in neighbors[start]):
                    continue
                chain, prev, curr = [start], None, start
                while True:
                    nxt = pop_next(curr, prev)
                    if nxt is None:
                        break
                    unused.discard(frozenset((curr, nxt)))
                    chain.append(nxt)
                    prev, curr = curr, nxt
                if len(chain) >= 2:
                    polylines.append((chain, False))

            while unused:
                e = unused.pop()
                a, b = tuple(e)
                chain, prev, curr = [a, b], a, b
                while True:
                    nxt = pop_next(curr, prev)
                    if nxt is None or frozenset((curr, nxt)) not in unused:
                        break
                    unused.discard(frozenset((curr, nxt)))
                    if nxt == chain[0]:
                        break
                    chain.append(nxt)
                    prev, curr = curr, nxt
                closed = len(chain) >= 3 and frozenset((chain[-1], chain[0])) in boundary_edges
                if len(chain) >= 2:
                    polylines.append((chain, closed))

            # CCW正規化 + ポイントリスト作成
            resolved = []
            for keys, closed in polylines:
                points = [uv_by_key[k] for k in keys]
                n = len(points)
                if n < 2:
                    continue
                if closed and n >= 3:
                    area2 = sum(
                        points[i].x * points[(i + 1) % n].y - points[(i + 1) % n].x * points[i].y for i in range(n)
                    )
                    if area2 < 0:
                        points.reverse()
                resolved.append((points, closed))

            # 閉ループの判定
            closed_loops = [(pts, i) for i, (pts, c) in enumerate(resolved) if c and len(pts) >= 3]
            nest_sign = {}
            for idx, (pts, ri) in enumerate(closed_loops):
                px, py = pts[0].x, pts[0].y
                depth = 0
                for jdx, (other, _) in enumerate(closed_loops):
                    if idx == jdx:
                        continue
                    inside = False
                    m = len(other)
                    j = m - 1
                    for i in range(m):
                        iy, jy = other[i].y, other[j].y
                        if (iy > py) != (jy > py):
                            if px < (other[j].x - other[i].x) * (py - iy) / (jy - iy) + other[i].x:
                                inside = not inside
                        j = i
                    if inside:
                        depth += 1
                nest_sign[ri] = -1.0 if depth % 2 == 1 else 1.0

            for ri, (points, closed) in enumerate(resolved):
                n = len(points)
                sign = nest_sign.get(ri, 1.0)

                seg_right = []
                for i in range(n if closed else n - 1):
                    d = points[(i + 1) % n] - points[i]
                    if d.length > 0:
                        d = d.normalized()
                        seg_right.append(Vector((d.y, -d.x)))
                    else:
                        seg_right.append(Vector((0, 0)))

                offset_pts = []
                for i in range(n):
                    if closed:
                        nrm = seg_right[(i - 1) % n] + seg_right[i]
                    elif i == 0:
                        nrm = seg_right[0]
                    elif i == n - 1:
                        nrm = seg_right[-1]
                    else:
                        nrm = seg_right[i - 1] + seg_right[i]
                    offset_pts.append(points[i] + (nrm.normalized() if nrm.length > 0 else nrm) * padding * sign)

                for i in range(n - 1):
                    cls._vertices.extend([offset_pts[i], offset_pts[i + 1]])
                if closed and n >= 3:
                    cls._vertices.extend([offset_pts[-1], offset_pts[0]])

            bm.free()

    @classmethod
    def update_state(cls, context):
        obj = context.active_object
        if obj.mio3uv.padding_px == "AUTO":
            calc_padding_px = PADDING_AUTO.get(obj.mio3uv.image_size, 16)
        else:
            calc_padding_px = int(obj.mio3uv.padding_px)
        cls._padding = int(calc_padding_px) / int(obj.mio3uv.image_size)

    @staticmethod
    def draw_2d(self, context, prefs):
        viewport_vertices = [context.region.view2d.view_to_region(v[0], v[1], clip=False) for v in self._vertices]
        shader = self._shader
        batch = batch_for_shader(shader, "LINES", {"pos": viewport_vertices})
        shader.bind()
        shader.uniform_float("color", prefs.ui_padding_col)
        batch.draw(shader)

    @classmethod
    def unregister(cls):
        cls.remove_handler()


@bpy.app.handlers.persistent
def load_handler(dummy):
    UV_OT_mio3_guide_padding.remove_handler()


def register():
    bpy.utils.register_class(UV_OT_mio3_guide_padding)
    bpy.app.handlers.load_post.append(load_handler)


def unregister():
    bpy.app.handlers.load_post.remove(load_handler)
    bpy.utils.unregister_class(UV_OT_mio3_guide_padding)
