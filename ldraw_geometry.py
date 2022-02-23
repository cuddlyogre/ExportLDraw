import mathutils

from .import_options import ImportOptions


class FaceInfo:
    """
    A file's face information. The raw model data before any transforms.
    """

    def __init__(self, color_code, vertices, texmap=None):
        self.color_code = color_code
        self.vertices = vertices
        self.texmap = texmap


class LDrawGeometry:
    """
    A file's geometry information.
    """

    def __init__(self):
        self.edge_infos = []
        self.face_infos = []
        self.line_infos = []
        self.edge_vert_count = 0
        self.face_vert_count = 0
        self.line_vert_count = 0

    def vert_count(self):
        return self.edge_vert_count + self.face_vert_count + self.line_vert_count

    def parse_face(self, _params, texmap=None, inverted=False):
        line_type = _params[0]

        color_code = _params[1]

        if line_type == "2":
            vert_count = 2
        elif line_type == "3":
            vert_count = 3
        elif line_type == "4":
            vert_count = 4
        elif line_type == "5":
            vert_count = 2
        else:
            return

        verts = []
        for i in range(vert_count):
            if inverted:
                z = float(_params[i * 3 + 4])
                y = float(_params[i * 3 + 3])
                x = float(_params[i * 3 + 2])
            else:
                x = float(_params[i * 3 + 2])
                y = float(_params[i * 3 + 3])
                z = float(_params[i * 3 + 4])
            vertex = mathutils.Vector((x, y, z))
            verts.append(vertex)

        if line_type == "2":
            self.edge_vert_count += len(verts)
            self.edge_infos.append(FaceInfo(color_code, verts))
        elif line_type == "3":
            self.face_vert_count += len(verts)
            self.face_infos.append(FaceInfo(color_code, verts, texmap=texmap))
        elif line_type == "4":
            # bowtie quads - https://wiki.ldraw.org/wiki/LDraw_Files_Requirements#Complex_quadrilaterals
            # vA = (verts[1] - verts[0]).cross(verts[2] - verts[0])
            # vB = (verts[2] - verts[1]).cross(verts[3] - verts[1])
            # if vA.dot(vB) < 0:
            #     verts[2], verts[3] = verts[3], verts[2]

            self.face_vert_count += len(verts)
            if ImportOptions.triangulate:
                verts1 = [verts[0], verts[1], verts[2]]
                self.face_infos.append(FaceInfo(color_code, verts1, texmap=texmap))
                verts2 = [verts[2], verts[3], verts[0]]
                self.face_infos.append(FaceInfo(color_code, verts2, texmap=texmap))
            else:
                self.face_infos.append(FaceInfo(color_code, verts, texmap=texmap))
        elif line_type == "5":
            self.line_vert_count += len(verts)
            self.line_infos.append(FaceInfo(color_code, verts))
