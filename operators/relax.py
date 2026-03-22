import bpy
from mathutils import Vector
from bpy.props import BoolProperty, EnumProperty, FloatProperty, IntProperty
from ..classes import UVNodeManager, Mio3UVOperator


class MIO3UV_OT_relax(Mio3UVOperator):
    bl_idname = "uv.mio3_relax"
    bl_label = "Relax"
    bl_description = "Relax UVs"
    bl_options = {"REGISTER", "UNDO"}

    method: EnumProperty(
        items=[
            ("DEFAULT", "Default", ""),
            ("MINIMIZE", "Minimize Stretch", ""),
        ],
        name="Mode",
    )
    keep_pin: BoolProperty(name="Keep Pin", default=True)
    keep_boundary: BoolProperty(name="Keep Boundary", default=True)
    relax_x: BoolProperty(name="X", default=True)
    relax_y: BoolProperty(name="Y", default=True)
    strength: FloatProperty(
        name="Strength",
        description="Strength of the relaxation effect",
        default=1.0,
        min=0.1,
        max=1.0,
    )
    iterations: IntProperty(
        name="Iterations",
        description="Number of relaxation iterations to perform",
        default=10,
        min=1,
        max=100,
    )
    _lambda = 0.5
    _mu = -0.53
    _eps = 0.00001
    _face_selected = False

    def invoke(self, context, event):
        objects = self.get_selected_objects(context)
        self._face_selected = self.check_selected_face_objects(objects)

        if not objects:
            self.report({"WARNING"}, "Object is not selected")
            return {"CANCELLED"}
        return self.execute(context)

    def execute(self, context):
        self.start_time()
        objects = self.get_selected_objects(context)

        if self.method == "MINIMIZE":
            bpy.ops.uv.minimize_stretch(fill_holes=True, blend=0, iterations=self.iterations)
        else:
            use_uv_select_sync = context.tool_settings.use_uv_select_sync

            node_manager = UVNodeManager(objects, sync=use_uv_select_sync)
            keep_boundary = self.keep_boundary and self._face_selected
            keep_pin = self.keep_pin
            for group in node_manager.groups:
                node_index_map = {id(node): index for index, node in enumerate(group.nodes)}
                fixed_nodes = [False] * len(group.nodes)
                neighbor_cache = [[] for _ in group.nodes]
                selection_boundary_cache = {}
                uv_layer = group.obj_info.uv_layer

                for index, node in enumerate(group.nodes):
                    if keep_boundary:
                        is_boundary_node = any(
                            loop.edge.is_boundary
                            or loop.edge.seam
                            or self.is_selection_boundary(loop.edge, selection_boundary_cache)
                            for loop in node.loops
                        )
                    else:
                        is_boundary_node = False

                    is_pinned = any(loop[uv_layer].pin_uv for loop in node.loops) if keep_pin else False
                    fixed_nodes[index] = len(node.neighbors) <= 1 or is_pinned or is_boundary_node

                    if fixed_nodes[index]:
                        continue

                    node_co = node.vert.co
                    weighted_neighbors = []
                    for neighbor in node.neighbors:
                        distance = max((neighbor.vert.co - node_co).length, 0.000001)
                        weighted_neighbors.append((node_index_map[id(neighbor)], 1.0 / distance))
                    neighbor_cache[index] = weighted_neighbors

                group.relax_nodes = group.nodes
                group.relax_fixed_nodes = fixed_nodes
                group.relax_neighbor_cache = neighbor_cache

                self.relax_group(group)

            node_manager.update_uvmeshes()

        self.print_time()
        return {"FINISHED"}

    @staticmethod
    def is_selection_boundary(edge, cache):
        if edge in cache:
            return cache[edge]

        has_is_face_selected = False
        has_unselected_face = False
        for face in edge.link_faces:
            if face.select:
                has_is_face_selected = True
            else:
                has_unselected_face = True
            if has_is_face_selected and has_unselected_face:
                cache[edge] = True
                return True
        cache[edge] = False
        return False

    def apply_laplacian(self, positions, target_positions, fixed_nodes, neighbor_cache, factor, ref_positions=None):
        relax_x = self.relax_x
        relax_y = self.relax_y

        max_move = 0.0
        for index, position in enumerate(positions):
            if fixed_nodes[index]:
                target_positions[index] = position
                continue

            weighted_neighbors = neighbor_cache[index]
            if not weighted_neighbors:
                target_positions[index] = position
                continue

            total_weight = 0.0
            average_position = Vector((0, 0))
            for neighbor_index, weight in weighted_neighbors:
                average_position += positions[neighbor_index] * weight
                total_weight += weight

            if total_weight == 0:
                target_positions[index] = position
                continue

            average_position /= total_weight
            next_position = position + (average_position - position) * factor
            if not relax_x:
                next_position.x = position.x
            if not relax_y:
                next_position.y = position.y
            target_positions[index] = next_position

            if ref_positions is not None:
                movement = (next_position - ref_positions[index]).length
                if movement > max_move:
                    max_move = movement

        return max_move

    def relax_group(self, group):
        nodes = group.relax_nodes
        fixed_nodes = group.relax_fixed_nodes
        neighbor_cache = group.relax_neighbor_cache
        uv_layer = group.uv_layer

        positions = [node.uv.copy() for node in nodes]
        lambda_positions = positions.copy()
        next_positions = positions.copy()
        lambda_factor = self._lambda * self.strength
        mu_factor = self._mu * self.strength

        for _ in range(self.iterations):
            self.apply_laplacian(positions, lambda_positions, fixed_nodes, neighbor_cache, lambda_factor)
            max_move = self.apply_laplacian(
                lambda_positions, next_positions, fixed_nodes, neighbor_cache, mu_factor, ref_positions=positions
            )

            positions, lambda_positions, next_positions = next_positions, positions, lambda_positions

            if max_move < self._eps:
                break

        for index, node in enumerate(nodes):
            node.uv = positions[index]
            node.update_uv(uv_layer)

    def draw(self, context):
        layout = self.layout
        layout.use_property_split = True
        layout.use_property_decorate = False
        layout.prop(self, "method")

        row = layout.row()
        row.prop(self, "keep_pin")
        if self.method == "MINIMIZE":
            row.enabled = False

        row = layout.row()
        row.prop(self, "keep_boundary")
        if self.method == "MINIMIZE":
            row.enabled = False

        row = layout.row(align=True)
        row.prop(self, "relax_x", toggle=True)
        row.prop(self, "relax_y", toggle=True)
        if self.method == "MINIMIZE":
            row.enabled = False

        row = layout.row()
        row.prop(self, "strength")
        if self.method == "MINIMIZE":
            row.enabled = False

        row = layout.row()
        row.prop(self, "iterations")


def register():
    bpy.utils.register_class(MIO3UV_OT_relax)


def unregister():
    bpy.utils.unregister_class(MIO3UV_OT_relax)
