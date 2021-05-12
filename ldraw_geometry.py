import numpy as np
from . import options
from .face_info import FaceInfo


class LDrawGeometry:
    def __init__(self):
        self.face_info = []

        self.face_index = 0
        self.face_vertices = []
        self.face_indexes = []

        self.edge_face_index = 0
        self.edge_face_vertices = []
        self.edge_face_indexes = []

    def parse_face(self, params, texmap=None):
        vert_count = int(params[0])
        color_code = params[1]

        face = []
        for i in range(vert_count):
            x = float(params[i * 3 + 2])
            y = float(params[i * 3 + 3])
            z = float(params[i * 3 + 4])
            vertex = np.array((x, y, z, 1))
            face.append(vertex)

        if vert_count == 2:
            # TODO: edge_face_info
            self.edge_face_vertices.append(face)

        elif vert_count == 3:
            self.face_vertices.append(face)
            self.face_info.append(FaceInfo(color_code, texmap=texmap))

        elif vert_count == 4:
            if options.fix_bowtie_quads:
                ba = face[1] - face[0]
                cb = face[2] - face[1]
                dc = face[3] - face[2]
                # ad = vertices[0] - vertices[3]
                ca = face[2] - face[0]
                db = face[3] - face[1]

                cA = np.cross(ba, ca)
                cB = np.cross(cb, db)
                cC = np.cross(dc, ca)
                # cD = np.cross(db, ad)

                dA = np.dot(cA, cB)
                dB = np.dot(cB, cC)
                # dC = np.dot(cC, cD)
                # dD = np.dot(cD, cA)
                if dA < 0:
                    _c = tuple([x for x in face[2]])
                    _d = tuple([x for x in face[3]])
                    face[2] = _d
                    face[3] = _c
                elif dB > 0:
                    _b = tuple([x for x in face[1]])
                    _c = tuple([x for x in face[2]])
                    face[1] = _c
                    face[2] = _b

            if options.triangulate_import:
                face1 = [face[0], face[1], face[2]]
                self.face_vertices.append(face1)
                self.face_info.append(FaceInfo(color_code, texmap=texmap))

                face2 = [face[2], face[3], face[0]]
                self.face_vertices.append(face2)
                self.face_info.append(FaceInfo(color_code, texmap=texmap))
            else:
                self.face_vertices.append(face)
                self.face_info.append(FaceInfo(color_code, texmap=texmap))
