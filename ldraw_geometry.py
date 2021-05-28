from . import options
from . import matrices
from . import face_info


class LDrawGeometry:
    def __init__(self):
        self.face_data = []
        self.edge_data = []

        self.face_infos = []
        self.face_vertices = []
        self.edge_vertices = []

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
            # TODO: edge_face_info
            self.edge_vertices.append(face)

        elif vert_count == 3:
            self.face_vertices.append(face)
            self.face_infos.append(face_info.FaceInfo(color_code, texmap=texmap))

        elif vert_count == 4:
            if options.triangulate_import:
                face1 = [face[0], face[1], face[2]]
                self.face_vertices.append(face1)
                self.face_infos.append(face_info.FaceInfo(color_code, texmap=texmap))

                face2 = [face[2], face[3], face[0]]
                self.face_vertices.append(face2)
                self.face_infos.append(face_info.FaceInfo(color_code, texmap=texmap))
            else:
                self.face_vertices.append(face)
                self.face_infos.append(face_info.FaceInfo(color_code, texmap=texmap))
