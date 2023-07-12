import mathutils


class PETexInfo:
    def __init__(self, point_min=None, point_max=None, point_diff=None, box_extents=None, matrix=None, matrix_inverse=None, image=None):
        self.point_min = point_min  # bottom corner of bounding box
        self.point_max = point_max  # top corner of bounding box
        self.point_diff = point_diff  # center of bounding box
        self.box_extents = box_extents
        self.matrix = matrix
        self.matrix_inverse = matrix_inverse
        self.image = image


class PETexmap:
    def __init__(self):
        self.texture = None
        self.uvs = []

    def uv_unwrap_face(self, bm, face):
        uv_layer = bm.loops.layers.uv.verify()
        for i, loop in enumerate(face.loops):
            loop[uv_layer].uv = self.uvs[i]

    @staticmethod
    def build_pe_texmap(ldraw_node, child_node):
        # child_node is a 3 or 4 line
        clean_line = child_node.line
        _params = clean_line.split()[2:]

        vert_count = len(child_node.vertices)

        pe_texmap = None
        for p in ldraw_node.pe_tex_info:
            # if we have uv data and a pe_tex_info, otherwise pass
            # # custom minifig head > 3626tex.dat (has no pe_tex) > 3626texpole.dat (has no uv data)
            if len(_params) == 15:  # use uvs provided in file
                pe_texmap = PETexmap()
                pe_texmap.texture = p.image

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
            else:
                continue
                # TODO: calculate uvs
                pe_texmap = PETexmap()
                pe_texmap.texture = p.image

                face_normal = (child_node.vertices[1] - child_node.vertices[0]).cross(child_node.vertices[2] - child_node.vertices[1])
                face_normal.normalize()

                texture_normal = mathutils.Vector((0.0, -1, 0.0))
                face_normal_within_texture_normal = True
                if face_normal.dot(texture_normal) < 1.0 / 1000.0:
                    face_normal_within_texture_normal = False

                for i in range(vert_count):
                    # if face is within p.boundingbox
                    vert = child_node.vertices[i]
                    # is_intersecting = (p.matrix @ p.bounding_box).interects(vert)

                    if face_normal_within_texture_normal:  # and is_intersecting:
                        uv = mathutils.Vector((0, 0))
                        uv.x = (vert.x - p.point_min.x) / p.point_diff.x
                        uv.y = (vert.z - p.point_min.y) / p.point_diff.y
                        pe_texmap.uvs.append(uv)

        return pe_texmap
