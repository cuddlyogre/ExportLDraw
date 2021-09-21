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
        self.edge_vert_count = 0
        self.face_vert_count = 0

    def parse_face(self, params, texmap=None, inverted=False):
        vert_count = int(params[0])
        color_code = params[1]

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

        if vert_count == 2:
            self.edge_vert_count += len(verts)
            self.edge_infos.append(FaceInfo(color_code, verts, texmap=texmap))

        elif vert_count == 3:
            self.face_vert_count += len(verts)
            self.face_infos.append(FaceInfo(color_code, verts, texmap=texmap))

        elif vert_count == 4:
            if import_options.triangulate:
                verts1 = [verts[0], verts[1], verts[2]]
                self.face_vert_count += len(verts1)
                self.face_infos.append(FaceInfo(color_code, verts1, texmap=texmap))

                verts2 = [verts[2], verts[3], verts[0]]
                self.face_vert_count += len(verts2)
                self.face_infos.append(FaceInfo(color_code, verts2, texmap=texmap))
            else:
                self.face_vert_count += len(verts)
                self.face_infos.append(FaceInfo(color_code, verts, texmap=texmap))
