import mathutils

from . import import_options
from .geometry_data import FaceInfo


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

    def parse_face(self, params, texmap=None, inverted=False):
        line_type = params[0]

        if line_type == '2':
            vert_count = 2
        elif line_type == '3':
            vert_count = 3
        elif line_type == '4':
            vert_count = 4
        elif line_type == '5':
            vert_count = 2
        else:
            return

        verts = []
        for i in range(vert_count):
            if inverted:
                z = float(params[i * 3 + 4])
                y = float(params[i * 3 + 3])
                x = float(params[i * 3 + 2])
            else:
                x = float(params[i * 3 + 2])
                y = float(params[i * 3 + 3])
                z = float(params[i * 3 + 4])
            vertex = mathutils.Vector((x, y, z))
            verts.append(vertex)

        color_code = params[1]

        if line_type == '2':
            self.edge_infos.append(FaceInfo(color_code, verts))
            self.edge_vert_count += len(verts)
        elif line_type == '3':
            self.face_infos.append(FaceInfo(color_code, verts, texmap=texmap))
            self.face_vert_count += len(verts)
        elif line_type == '4':
            if import_options.triangulate:
                verts1 = [verts[0], verts[1], verts[2]]
                self.face_infos.append(FaceInfo(color_code, verts1, texmap=texmap))
                self.face_vert_count += len(verts1)

                verts2 = [verts[2], verts[3], verts[0]]
                self.face_infos.append(FaceInfo(color_code, verts2, texmap=texmap))
                self.face_vert_count += len(verts2)
            else:
                self.face_infos.append(FaceInfo(color_code, verts, texmap=texmap))
                self.face_vert_count += len(verts)
        elif line_type == '5':
            self.line_infos.append(FaceInfo(color_code, verts))
            self.line_vert_count += len(verts)
