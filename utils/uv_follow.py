# SPDX-FileCopyrightText: 2009-2023 Blender Authors
#
# SPDX-License-Identifier: GPL-2.0-or-later
#
# Modifications:
# - Adapted for this add-on
# - Minor changes by Mio (2026)


def get_uv_key(uv):
    return (round(uv.x, 6), round(uv.y, 6))


def build_uv_loop_index(bm, uv_layer):
    uv_loop_index = {}

    for face in bm.faces:
        for loop in face.loops:
            key = (loop.vert, get_uv_key(loop[uv_layer].uv))
            uv_loop_index.setdefault(key, []).append(loop)

    return uv_loop_index


def collect_shared_uv_loops(uv_layer, faces, uv_loop_index):
    shared_uvs = {}

    for face in faces:
        for loop in face.loops:
            key = (loop.vert, get_uv_key(loop[uv_layer].uv))
            if key not in shared_uvs:
                shared_uvs[key] = {"source": loop, "loops": uv_loop_index.get(key, [])}

    return shared_uvs


def sync_shared_uv_loops(uv_layer, shared_uvs):
    for entry in shared_uvs.values():
        source_loop = entry["source"]
        uv = source_loop[uv_layer].uv.copy()
        for loop in entry["loops"]:
            if loop is source_loop:
                continue
            loop[uv_layer].uv = uv


def uv_follow(extend_blend, island, f_act, shared_uvs):
    bm = island.bm
    uv_layer = island.uv_layer
    faces = island.faces

    if f_act is None:
        return

    faces = [face for face in faces if len(face.loops) == 4]
    if not faces or f_act not in faces:
        return

    # Our own local walker.

    def walk_face_init(faces, f_act):
        # First tag all faces True (so we don't UV-map them).
        for f in bm.faces:
            f.tag = True
        # Then tag faces argument False.
        for f in faces:
            f.tag = False
        # Tag the active face True since we begin there.
        f_act.tag = True

    def walk_face(f):
        # All faces in this list must be tagged.
        f.tag = True
        faces_a = [f]
        faces_b = []

        while faces_a:
            for f in faces_a:
                for l in f.loops:
                    l_edge = l.edge
                    if (l_edge.is_manifold is True) and (l_edge.seam is False):
                        l_other = l.link_loop_radial_next
                        f_other = l_other.face
                        if not f_other.tag:
                            yield (f, l, f_other)
                            f_other.tag = True
                            faces_b.append(f_other)
            # Swap.
            faces_a, faces_b = faces_b, faces_a
            faces_b.clear()

    # Utility, only for `walk_edgeloop_all`.
    def walk_edgeloop_all_impl_loop(loop_stack, edges_visited, l):
        l_other = l.link_loop_next.link_loop_next
        l_other_edge = l_other.edge
        if l_other_edge not in edges_visited:
            edges_visited.add(l_other_edge)
            yield l_other_edge
            if not l_other_edge.is_boundary:
                loop_stack.append(l_other)

    def walk_edgeloop_all(e):
        # Walks over all edge loops connected by quads (even edges with 3+ users).
        # Could make this a generic function.

        loop_stack = []
        edges_visited = {e}

        yield e

        # This initial iteration is needed because the loops never walk back over the face they come from.
        for l in e.link_loops:
            if len(l.face.verts) != 4:
                continue
            yield from walk_edgeloop_all_impl_loop(loop_stack, edges_visited, l)

        while loop_stack and (l_test := loop_stack.pop()):
            # Walk around the quad and then onto the next face.
            l = l_test
            while (l := l.link_loop_radial_next) is not l_test:
                if len(l.face.verts) != 4:
                    continue
                yield from walk_edgeloop_all_impl_loop(loop_stack, edges_visited, l)

    def extrapolate_uv(fac, l_a_outer, l_a_inner, l_b_outer, l_b_inner):
        l_b_inner[:] = l_a_inner
        l_b_outer[:] = l_a_inner + ((l_a_inner - l_a_outer) * fac)

    def blend_length_average_factor(ratio, blend):
        return ratio + ((1.0 - ratio) * blend)

    def apply_uv(_f_prev, l_prev, _f_next):
        l_a = [None, None, None, None]
        l_b = [None, None, None, None]

        l_a[0] = l_prev
        l_a[1] = l_a[0].link_loop_next
        l_a[2] = l_a[1].link_loop_next
        l_a[3] = l_a[2].link_loop_next

        #  l_b
        #  +-----------+
        #  |(3)        |(2)
        #  |           |
        #  |l_next(0)  |(1)
        #  +-----------+
        #        ^
        #  l_a   |
        #  +-----------+
        #  |l_prev(0)  |(1)
        #  |    (f)    |
        #  |(3)        |(2)
        #  +-----------+
        #  Copy from this face to the one above.

        # Get the other loops.
        l_next = l_prev.link_loop_radial_next
        if l_next.vert != l_prev.vert:
            l_b[1] = l_next
            l_b[0] = l_b[1].link_loop_next
            l_b[3] = l_b[0].link_loop_next
            l_b[2] = l_b[3].link_loop_next
        else:
            l_b[0] = l_next
            l_b[1] = l_b[0].link_loop_next
            l_b[2] = l_b[1].link_loop_next
            l_b[3] = l_b[2].link_loop_next

        l_a_uv = [l[uv_layer].uv for l in l_a]
        l_b_uv = [l[uv_layer].uv for l in l_b]

        if extend_blend < 1.0:
            d1 = edge_lengths[l_a[1].edge.index][0]
            d2 = edge_lengths[l_b[2].edge.index][0]
            try:
                fac = blend_length_average_factor(d2 / d1, extend_blend)
            except ZeroDivisionError:
                fac = 1.0
        else:
            fac = 1.0

        extrapolate_uv(
            fac,
            l_a_uv[3],
            l_a_uv[0],
            l_b_uv[3],
            l_b_uv[0],
        )

        extrapolate_uv(
            fac,
            l_a_uv[2],
            l_a_uv[1],
            l_b_uv[2],
            l_b_uv[1],
        )

    # -------------------------------------------
    # Calculate average length per loop if needed.

    if extend_blend < 1.0:
        bm.edges.index_update()
        edge_lengths = [None] * len(bm.edges)

        for f in faces:
            # We know it's a quad.
            l_quad = f.loops[:]

            # The opposite loops `l_quad[2]` & `l_quad[3]` are implicit (walking will handle).
            for l_init in (l_quad[0], l_quad[1]):
                # No need to check both because the initializing
                # one side of the pair will have initialized the second.
                l_init_edge = l_init.edge
                if edge_lengths[l_init_edge.index] is not None:
                    continue

                edge_length_store = [-1.0]
                edge_length_accum = 0.0
                edge_length_total = 0

                for e in walk_edgeloop_all(l_init_edge):
                    # Any previously met edges should have expanded into `l_init_edge`
                    # (which has no length).
                    assert edge_lengths[e.index] is None

                    edge_lengths[e.index] = edge_length_store
                    edge_length_accum += e.calc_length()
                    edge_length_total += 1

                edge_length_store[0] = edge_length_accum / edge_length_total

    # done with average length
    # ------------------------

    walk_face_init(faces, f_act)
    for f_triple in walk_face(f_act):
        apply_uv(*f_triple)

    if shared_uvs is not None:
        sync_shared_uv_loops(uv_layer, shared_uvs)
