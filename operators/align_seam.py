import bpy
import bmesh
import time
from bpy.props import EnumProperty
from bpy.app.translations import pgettext_iface as tt_iface
from ..icons import preview_collections
from ..classes.uv import UVNodeManager
from ..classes.operator import Mio3UVOperator


class MIO3UV_OT_align_seam(Mio3UVOperator):
    bl_idname = "uv.mio3_align_seam"
    bl_label = "Align Seam"
    bl_description = "Align UVs of the same 3D vertex split by a seam"
    bl_options = {"REGISTER", "UNDO"}

    axis: EnumProperty(
        name="Axis",
        items=[
            ("AUTO", "Auto", ""),
            ("Y", "Y", ""),
            ("X", "X", ""),
        ],
        default="AUTO",
    )
    align: EnumProperty(
        name="Source",
        items=[
            ("A", "Top / Right", "Positive"),
            ("B", "Left / Bottom", "Negative"),
            ("Average", "Average", "Average"),
        ],
        default="A",
    )

    def execute(self, context):
        self.start_time()
        obj = context.active_object

        self.use_uv_select_sync = context.tool_settings.use_uv_select_sync
        if self.use_uv_select_sync:
            self.sync_uv_from_mesh(context, [obj])
            context.tool_settings.use_uv_select_sync = False

        bm = bmesh.from_edit_mesh(obj.data)
        uv_layer = bm.loops.layers.uv.verify()

        node_manager = UVNodeManager.from_object(obj, bm, uv_layer)

        if len(node_manager.groups) == 1:
            selected_uv_verts = set()
            for face in bm.faces:
                for loop in face.loops:
                    if loop[uv_layer].select:
                        selected_uv_verts.add(loop.vert)
            for face in bm.faces:
                for loop in face.loops:
                    if loop.vert in selected_uv_verts:
                        loop[uv_layer].select = True
                        # エッジ
                        # edge = loop.edge
                        # vert1 = edge.verts[0]
                        # vert2 = edge.verts[1]
                        # if vert1 in selected_uv_verts and vert2 in selected_uv_verts:
                        #     loop[uv_layer].select_edge = True

            node_manager = UVNodeManager.from_object(obj, bm, uv_layer)
            groups = []
            for group in node_manager.groups:
                if len(group.nodes) == 1:
                    group.deselect_all_uv()
                else:
                    groups.append(group)
        else:
            groups = node_manager.groups

        if len(groups) != 2:
            self.report({"WARNING"}, "Select the two edge loops")
            return self.cancel_operator(context)

        if self.axis == "AUTO":
            axis = self.determine_axis(groups[0])
        else:
            axis = self.axis
        axis_index = 1 if axis == "Y" else 0

        groups.sort(key=lambda group: min(node.uv[1 if axis == "X" else 0] for node in group.nodes), reverse=True)
        group_a, group_b = groups

        # 同じ3D頂点を持つノードをグループ化
        vert_to_uv_nodes = {}
        for group in [group_a, group_b]:
            for node in group.nodes:
                if node.vert not in vert_to_uv_nodes:
                    vert_to_uv_nodes[node.vert] = []
                vert_to_uv_nodes[node.vert].append(node)

        for vert, nodes in vert_to_uv_nodes.items():
            if len(nodes) < 2:
                continue

            if self.align == "A":
                source_nodes = [n for n in nodes if n in group_a.nodes]
                move_nodes = [n for n in nodes if n in group_b.nodes]
            elif self.align == "B":
                source_nodes = [n for n in nodes if n in group_b.nodes]
                move_nodes = [n for n in nodes if n in group_a.nodes]
            else:
                source_nodes = nodes
                move_nodes = nodes

            if not source_nodes:
                continue

            pos = sum(node.uv[axis_index] for node in source_nodes) / len(source_nodes)

            for node in move_nodes:
                node.uv[axis_index] = pos

        for group in groups:
            group.update_uvs()

        node_manager.update_uvmeshes()

        if self.use_uv_select_sync:
            context.tool_settings.use_uv_select_sync = True

        self.print_time()
        return {"FINISHED"}

    def cancel_operator(self, context):
        if self.use_uv_select_sync:
            context.tool_settings.use_uv_select_sync = True
        return {"CANCELLED"}

    def determine_axis(self, group):
        min_u = min(node.uv.x for node in group.nodes)
        max_u = max(node.uv.x for node in group.nodes)
        min_v = min(node.uv.y for node in group.nodes)
        max_v = max(node.uv.y for node in group.nodes)
        width = max_u - min_u
        height = max_v - min_v
        return "Y" if height > width else "X"


classes = [MIO3UV_OT_align_seam]


def register():
    for c in classes:
        bpy.utils.register_class(c)


def unregister():
    for c in classes:
        bpy.utils.unregister_class(c)
