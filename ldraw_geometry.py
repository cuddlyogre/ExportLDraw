import mathutils

from . import import_options
from .face_info import FaceInfo


class LDrawGeometry:
    def __init__(self):
        self.edge_vertices = []
        self.edge_infos = []

        self.face_vertices = []
        self.face_infos = []

    def parse_face(self, params, texmap=None):
        vert_count = int(params[0])
        color_code = params[1]

        verts = []
        for i in range(vert_count):
            x = float(params[i * 3 + 2])
            y = float(params[i * 3 + 3])
            z = float(params[i * 3 + 4])
            vertex = mathutils.Vector((x, y, z))
            verts.append(vertex)

        if vert_count == 2:
            self.edge_infos.append(FaceInfo(color_code, verts, texmap=texmap))

        elif vert_count == 3:
            self.face_infos.append(FaceInfo(color_code, verts, texmap=texmap))

        elif vert_count == 4:
            if import_options.triangulate:
                verts1 = [verts[0], verts[1], verts[2]]
                self.face_infos.append(FaceInfo(color_code, verts1, texmap=texmap))

                verts2 = [verts[2], verts[3], verts[0]]
                self.face_infos.append(FaceInfo(color_code, verts2, texmap=texmap))
            else:
                self.face_infos.append(FaceInfo(color_code, verts, texmap=texmap))


class LDrawGeometryData:
    def __init__(self):
        self.edge_data = []
        self.face_data = []
