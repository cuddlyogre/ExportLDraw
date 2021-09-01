from . import import_options
from . import matrices
from . import face_info


class LDrawGeometry:
    def __init__(self):
        self.edge_vertices = []
        self.edge_infos = []

        self.face_vertices = []
        self.face_infos = []

    def parse_face(self, params, texmap=None):
        vert_count = int(params[0])
        color_code = params[1]

        face = []
        for i in range(vert_count):
            x = float(params[i * 3 + 2])
            y = float(params[i * 3 + 3])
            z = float(params[i * 3 + 4])
            vertex = matrices.Vector4((x, y, z))
            face.append(vertex)

        if vert_count == 2:
            self.edge_vertices.append(face)
            self.edge_infos.append(face_info.FaceInfo(color_code, texmap=texmap))

        elif vert_count == 3:
            self.face_vertices.append(face)
            self.face_infos.append(face_info.FaceInfo(color_code, texmap=texmap))

        elif vert_count == 4:
            if import_options.triangulate:
                face1 = [face[0], face[1], face[2]]
                self.face_vertices.append(face1)
                self.face_infos.append(face_info.FaceInfo(color_code, texmap=texmap))

                face2 = [face[2], face[3], face[0]]
                self.face_vertices.append(face2)
                self.face_infos.append(face_info.FaceInfo(color_code, texmap=texmap))
            else:
                self.face_vertices.append(face)
                self.face_infos.append(face_info.FaceInfo(color_code, texmap=texmap))


class LDrawGeometryData:
    def __init__(self):
        self.edge_data = []
        self.face_data = []
