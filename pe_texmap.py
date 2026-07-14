import mathutils

# Projection axis of a PE texture, in the texture's own space (Studio: Vector3.down).
TEXTURE_NORMAL = mathutils.Vector((0, -1, 0))


def _vkey(v):
    # Adjacency key for the flood-fill: two faces are "connected" when they share a
    # vertex position. LDraw file coordinates are written to ~3 decimals, so rounding
    # here reliably matches shared corners without welding genuinely distinct vertices.
    return (round(v.x, 3), round(v.y, 3), round(v.z, 3))


class PETexPath:
    def __init__(self):
        self.tex_path = None
        self.tex_infos = []
        self.tex_info = None

    def build_uv_texmaps(self, child_node):
        # Faces that already carry explicit UVs in the file (type 3/4 with >=17 tokens)
        # are mapped directly here -- no projection needed.
        #
        # The bounding-box (projection) case is NOT handled per-face. It is deferred to
        # project_box_texmaps(), which runs once the whole mesh has been collected, so the
        # decal can flood-fill across connected faces (see that function).
        pe_texmaps = []
        if len(child_node.uvs) == 0:
            return pe_texmaps
        for tex_info in self.tex_infos:
            pe_texmap = PETexmap()
            pe_texmap.image_name = tex_info.image_name
            pe_texmap.uvs = child_node.uvs.copy()
            pe_texmaps.append(pe_texmap)
        return pe_texmaps


class PETexInfo:
    def __init__(self):
        self.next_shear = False
        self.matrix = None
        self.matrix_inverse = None
        self.image_name = None

        self.uvs = None  # uvs included in the file

        self.point_min = None  # bottom corner of bounding box
        self.point_max = None  # top corner of bounding box
        self.point_diff = None  # center of bounding box
        self.camera_origin = None  # center of bounding box


class PETexmap:
    def __init__(self):
        self.image_name = None
        self.uvs = []

    def uv_unwrap_face(self, bm, face):
        if not self.uvs:
            return

        uv_layer = bm.loops.layers.uv.verify()
        uvs = {}
        for i, loop in enumerate(face.loops):
            p = loop.vert.co.copy().freeze()
            if p not in uvs:
                uvs[p] = self.uvs[i]
            loop[uv_layer].uv = uvs[p]


def is_sheared_matrix(matrix, eps=0.01):
    """
    True when matrix's 3x3 carries shear -- its basis vectors are not mutually orthogonal.

    Mirrors Studio's PEPart.IsShearedPart: it QR-decomposes the part transform (TRS-S split)
    and treats it as sheared when the upper-triangular factor R has a non-trivial off-diagonal
    term (abs(R.m01), abs(R.m02) or abs(R.m12) > 0.01). Non-uniform but orthogonal scaling (a
    stretched-but-square box) is NOT shear and yields zero off-diagonals, exactly like Studio.
    Gram-Schmidt produces the same off-diagonal magnitudes as Studio's Householder QR, so the
    0.01 threshold matches.
    """
    # columns = images of the basis vectors (mathutils.Matrix is row-major: matrix[row][col])
    c0 = mathutils.Vector((matrix[0][0], matrix[1][0], matrix[2][0]))
    c1 = mathutils.Vector((matrix[0][1], matrix[1][1], matrix[2][1]))
    c2 = mathutils.Vector((matrix[0][2], matrix[1][2], matrix[2][2]))
    if c0.length < 1e-6 or c1.length < 1e-6 or c2.length < 1e-6:
        return False
    e0 = c0.normalized()
    r01 = e0.dot(c1)  # R.m01
    r02 = e0.dot(c2)  # R.m02
    u1 = c1 - r01 * e0
    if u1.length < 1e-6:
        return False
    e1 = u1.normalized()
    r12 = e1.dot(c2)  # R.m12
    return abs(r01) > eps or abs(r02) > eps or abs(r12) > eps


def descend_tex_info(tex_info, child_matrix):
    """
    Re-express a PETexInfo so a projection declared on a parent file also applies to a child
    subfile's geometry. A box (matrix) projection is rebased into the child's local frame
    (M_child = child_matrix^-1 @ M_parent) so it "descends" to wherever the real faces live --
    e.g. the minifig hand grip is assembled from sub-primitives (2-4cyli...) that have no faces
    of their own, so a projection targeting them must reach one level deeper. Explicit-UV
    tex_infos (no matrix) already apply to child_nodes, so they pass through unchanged.

    Matches Studio, where a PE_TEX_PATH projects onto the entire subtree of the targeted node.

    PE_TEX_NEXT_SHEAR: when the descended-into child's placement (child_matrix) is sheared,
    Studio (Studio Part Designer) does NOT keep that shear on the part transform. PEPart.Is-
    ShearedPart factors the shear out into the model (model.ShearMatrix) and resets the part to
    a rigid TRS, then PETextureInfo.InitMatrixWithTargetPartMatrix re-applies it to the box:
        m_texToTarget = model.ShearMatrix * m_texToTarget    (only while m_includeShear is set)
    So the PE_TEX_INFO matrix in the file is calibrated to recombine with that shear: it is
    M_part @ matrix that yields the true, un-sheared projection box (verified: for 15068pb046a
    M_part @ matrix is exactly axis-aligned). Rebasing the box through the full sheared
    child_matrix here would divide that shear back out (child_matrix^-1 @ matrix) and, once the
    build matrix re-applies child_matrix, cancel it -- collapsing the box to the thin, skewed
    in-file matrix and smearing (usually dropping) the decal.

    So for a next_shear box descending through a sheared child we leave the matrix un-rebased
    and let the build matrix supply child_matrix's shear -- the build matrix's contribution
    (Studio globalTransformMatrix * ShearMatrix) equals Studio's corrected m_texToTarget. The
    flag is then consumed so any deeper level rebases normally (Studio applies the shear once).
    Non-shear descents are unchanged, so PE_TEX_PATHs that already route straight to the sheared
    target (e.g. 15068pb046a "0 1") -- where the build matrix supplies the shear without any
    descend at all -- are unaffected.
    """
    if tex_info.matrix is None:
        return tex_info
    descended = PETexInfo()
    descended.next_shear = tex_info.next_shear
    descended.image_name = tex_info.image_name
    if tex_info.next_shear and is_sheared_matrix(child_matrix):
        descended.matrix = tex_info.matrix
        descended.next_shear = False
    else:
        descended.matrix = (child_matrix.inverted() @ tex_info.matrix).freeze()
    descended.matrix_inverse = descended.matrix.inverted().freeze()
    descended.point_min = tex_info.point_min
    descended.point_max = tex_info.point_max
    descended.point_diff = tex_info.point_diff
    descended.camera_origin = tex_info.camera_origin
    return descended


def project_box_texmaps(face_datas):
    """
    Apply PE_TEX_INFO bounding-box (projection) textures to a fully-collected mesh.

    This mirrors Studio's LDrawTextureAtlas.OptimizeMode: the projection is applied to the
    assembled mesh, not per-face during the build. For each projection we
      1. seed the faces that face the projector AND intersect the (thin) projection box
         (LDrawTextureInfo.CollectVerticesInBoxExtents), then
      2. flood-fill the decal across connected faces that still face the projector,
         WITHOUT re-testing the box (LDrawTextureInfo.CollectConnectVertices).

    Step 2 is what lets the decal follow a concave surface (e.g. the scoop of a skirt)
    that recedes behind the box, while the thin box depth still keeps it off the opposite
    interior wall -- the flood-fill can't reach that wall without crossing back-facing
    faces, which breaks the chain.

    Blender stores UVs per loop, so the C# vertex-splitting at the decal boundary is
    unnecessary: only the loops of selected faces get written, so UVs never bleed onto a
    neighbouring face through a shared vertex.

    Operates on a list of FaceData (duck-typed: .vertices, .matrix, .pe_tex_path,
    .child_node, .pe_texmaps) and appends the resulting PETexmap(s) to each face.
    """
    # Faces eligible for box projection. Explicit-UV faces are handled in build_uv_texmaps;
    # faces without a pe_tex_path (e.g. merged primitives) are never textured.
    faces = [fd for fd in face_datas
             if fd.pe_tex_path is not None and len(fd.child_node.uvs) == 0]
    if not faces:
        return

    # Adjacency map: shared vertex position -> indices into `faces`.
    pos_to_faces = {}
    for idx, fd in enumerate(faces):
        for v in fd.vertices:
            pos_to_faces.setdefault(_vkey(v), set()).add(idx)

    # Faces already claimed by any projection. Mirrors C# IsUVOfFaceAlreadyAssigned, so a
    # face caught by an earlier PE_TEX_INFO (e.g. the back decal) is not re-claimed by a
    # later one (e.g. the front decal).
    covered = set()

    # Preserve file order of the distinct tex paths present on these faces.
    paths = []
    for fd in faces:
        if fd.pe_tex_path not in paths:
            paths.append(fd.pe_tex_path)

    for path in paths:
        path_idxs = [i for i, fd in enumerate(faces) if fd.pe_tex_path is path]
        path_set = set(path_idxs)
        for tex_info in path.tex_infos:
            if tex_info.matrix is None:
                continue  # explicit-uv tex_info, nothing to project
            _project_one(faces, path_idxs, path_set, tex_info, pos_to_faces, covered)


def _project_one(faces, path_idxs, path_set, tex_info, pos_to_faces, covered):
    # Every face in one mesh shares the same build matrix, so any of them composes the
    # same projection. local = (matrix @ tex_info.matrix)^-1 @ vertex  (the per-face build
    # matrix cancels, exactly as the previous per-face code computed it).
    matrix = faces[path_idxs[0]].matrix
    (translation, rotation, box_extents) = (matrix @ tex_info.matrix).decompose()

    # Half-extents are 0.5 * scale (Studio: m_boxExtents = 0.5f * s). A too-deep box
    # punches through the part and lands the decal on the opposite interior wall.
    box_extents = box_extents * 0.5
    mirroring = mathutils.Vector((1, 1, 1))
    for dim in range(3):
        if box_extents[dim] < 0:
            mirroring[dim] *= -1
            box_extents[dim] *= -1

    # Composed matrix without scale (matches Studio re-composing with the +/-1 mirror only),
    # so vertices land in box space at true LDU distances from the projection plane.
    composed_inverse = mathutils.Matrix.LocRotScale(translation, rotation, mirroring).inverted()

    local_cache = {}  # face idx -> [local vertex Vectors]
    normal_cache = {}  # face idx -> face normal in texture space

    def localize(idx):
        lv = local_cache.get(idx)
        if lv is None:
            lv = [composed_inverse @ v for v in faces[idx].vertices]
            local_cache[idx] = lv
            normal = (lv[1] - lv[0]).cross(lv[2] - lv[1]).normalized()
            # The stored vertex order already encodes BFC/INVERTNEXT (GeometryData folds the
            # accumulated inversion into the winding, our equivalent of Studio's MeshBackFace),
            # so this raw cross product is the true outward normal. Do NOT flip it for inverted
            # faces -- that double-counts the inversion and drops decals that belong on inverted
            # surfaces (e.g. the inside of a minifig hand grip).
            normal_cache[idx] = normal
        return lv

    # 1. Seed: faces that face the projector (dot >= 0.001) and intersect the box.
    frontier = []
    selected = set()
    for idx in path_idxs:
        if idx in covered:
            continue
        local_vertices = localize(idx)
        if normal_cache[idx].dot(TEXTURE_NORMAL) < 0.001:
            continue
        if not intersect(local_vertices, box_extents):
            continue
        selected.add(idx)
        covered.add(idx)
        frontier.append(idx)

    # 2. Grow: connected faces that still face the projector (dot > 0). No box test --
    #    this is what carries the decal onto the scoop that recedes behind the box.
    while frontier:
        idx = frontier.pop()
        neighbors = set()
        for v in faces[idx].vertices:
            neighbors |= pos_to_faces.get(_vkey(v), set())
        for j in neighbors:
            if j in covered or j not in path_set:
                continue
            localize(j)
            if normal_cache[j].dot(TEXTURE_NORMAL) <= 0.0:
                continue
            selected.add(j)
            covered.add(j)
            frontier.append(j)

    # 3. Assign projected UVs to every selected face.
    point_min = tex_info.point_min
    point_diff = tex_info.point_diff
    for idx in selected:
        pe_texmap = PETexmap()
        pe_texmap.image_name = tex_info.image_name
        for vert in local_cache[idx]:
            u = (vert.x - point_min.x) / point_diff.x
            v = (vert.z - -point_min.y) / -point_diff.y
            pe_texmap.uvs.append(mathutils.Vector((u, v)))
        faces[idx].pe_texmaps.append(pe_texmap)


def intersect(polygon, box_extents):
    match polygon:
        case [a, b, c]:
            pass
        case [a, b, c, d]:
            return intersect([a, b, c], box_extents) or intersect([c, d, a], box_extents)
        case _:
            raise ValueError

    edges = [b - a, c - b, a - c]
    for i in range(3):
        for j in range(3):
            e = edges[j]
            ex = e.x
            ey = e.y
            ez = e.z

            be = box_extents
            bx = be.x
            by = be.y
            bz = be.z

            if i == 0:
                rhs = mathutils.Vector((0, -ez, ey))
                num = by * abs(ez) + bz * abs(ey)
            elif i == 1:
                rhs = mathutils.Vector((ez, 0, -ex))
                num = bx * abs(ez) + bz * abs(ex)
            elif i == 2:
                rhs = mathutils.Vector((-ey, ex, 0))
                num = bx * abs(ey) + by * abs(ex)

            dot_products = [v.dot(rhs) for v in (a, b, c)]
            miximum = max(-max(dot_products), min(dot_products))
            if miximum > num:
                return False

    for dim in range(3):
        coords = (a[dim], b[dim], c[dim])
        if max(coords) < -box_extents[dim] or min(coords) > box_extents[dim]:
            return False

    normal = edges[0].cross(edges[1])
    abs_normal = mathutils.Vector(abs(v) for v in normal.to_tuple())
    return normal.dot(a) <= abs_normal.dot(box_extents)
