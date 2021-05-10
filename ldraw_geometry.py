import mathutils
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
        #self.stud_roots = []

    def parse_face(self, params, texmap=None):
        face = []
        vert_count = int(params[0])
        for i in range(vert_count):
            x = float(params[i * 3 + 2])
            y = float(params[i * 3 + 3])
            z = float(params[i * 3 + 4])
            vertex = mathutils.Vector((x, y, z))
            face.append(vertex)

        if vert_count == 2:
            self.edge_face_vertices.append(face)
            # TODO: edge_face_info
            return

        if vert_count == 4:
            if options.fix_bowtie_quads:
                ba = face[1] - face[0]
                cb = face[2] - face[1]
                dc = face[3] - face[2]
                # ad = vertices[0] - vertices[3]
                ca = face[2] - face[0]
                db = face[3] - face[1]

                cA = ba.cross(ca)
                cB = cb.cross(db)
                cC = dc.cross(ca)
                # cD = db.cross(ad)

                dA = cA.dot(cB)
                dB = cB.dot(cC)
                # dC = cC.dot(cD)
                # dD = cD.dot(cA)
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

        if vert_count in (3, 4):
            self.face_vertices.append(face)

            color_code = params[1]
            self.face_info.append(FaceInfo(color_code, texmap=texmap))
