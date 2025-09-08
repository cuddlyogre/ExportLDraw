import mathutils


class PETexInfo:
    def __init__(self):
        self.tex_path = None
        self.next_shear = False
        self.matrix = None
        self.image = None

        self.point_min = None  # bottom corner of bounding box
        self.point_max = None  # top corner of bounding box
        self.point_diff = None  # center of bounding box


class PETexmap:
    def __init__(self):
        self.texture = None
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

    @staticmethod
    def build_pe_texmap(ldraw_node, child_node, winding, pe_tex_info_list):
        # child_node is a 3 or 4 line
        clean_line = child_node.line
        _params = clean_line.split()[2:]

        vert_count = len(child_node.vertices)

        pe_texmap = PETexmap()
        for pe_tex_info in pe_tex_info_list:
            pe_texmap.texture = pe_tex_info.image

            # if we have uv data and a pe_tex_info, otherwise pass
            # # custom minifig head > 3626tex.dat (has no pe_tex) > 3626texpole.dat (has no uv data)
            if len(_params) == 15:  # use uvs provided in file
                for i in range(vert_count):
                    if vert_count == 3:
                        x = round(float(_params[i * 2 + 9]), 3)
                        y = round(float(_params[i * 2 + 10]), 3)
                        uv = mathutils.Vector((x, y))
                        pe_texmap.uvs.append(uv)
                    elif vert_count == 4:
                        x = round(float(_params[i * 2 + 11]), 3)
                        y = round(float(_params[i * 2 + 12]), 3)
                        uv = mathutils.Vector((x, y))
                        pe_texmap.uvs.append(uv)

            elif pe_tex_info.matrix:
                next_shear = pe_tex_info.next_shear
                # if next_shear:
                # process shear

                (translation, rotation, scale) = (ldraw_node.matrix @ pe_tex_info.matrix).decompose()

                mirroring = mathutils.Vector((1, 1, 1))
                rhs = mathutils.Matrix.LocRotScale(translation, rotation, mirroring)

                matrix = ldraw_node.matrix.inverted() @ rhs
                matrix_inverse = matrix.inverted()

                vertices = [matrix_inverse @ v for v in child_node.vertices]

                if winding == "CW":
                    if vert_count == 3:
                        vertices = [
                            vertices[0],
                            vertices[2],
                            vertices[1],
                        ]
                    elif vert_count == 4:
                        vertices = [
                            vertices[0],
                            vertices[3],
                            vertices[2],
                            vertices[1],
                        ]

                if not intersect(vertices, scale):
                    continue

                ab = vertices[1] - vertices[0]
                bc = vertices[2] - vertices[1]
                face_normal = ab.cross(bc).normalized()
                texture_normal = mathutils.Vector((0, -1, 0))
                dot = face_normal.dot(texture_normal)
                # if abs(dot) < 0.001: continue
                if dot <= 0.001: continue

                for vert in vertices:
                    u = (vert.x - pe_tex_info.point_min.x) / pe_tex_info.point_diff.x
                    v = (vert.z - -pe_tex_info.point_min.y) / -pe_tex_info.point_diff.y
                    uv = mathutils.Vector((u, v))
                    pe_texmap.uvs.append(uv)

        return pe_texmap


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
            be = box_extents
            if i == 0:
                rhs = mathutils.Vector((0, -e.z, e.y))
                num = be.y * abs(e.z) + be.z * abs(e.y)
            elif i == 1:
                rhs = mathutils.Vector((e.z, 0, -e.x))
                num = be.x * abs(e.z) + be.z * abs(e.x)
            else:
                rhs = mathutils.Vector((-e.y, e.x, 0))
                num = be.x * abs(e.y) + be.y * abs(e.x)

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
