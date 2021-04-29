import mathutils
from . import options
from .face_info import FaceInfo


class LDrawGeometry:
    def __init__(self):
        self.edge_vertices = []
        self.edge_vert_counts = []
        self.vertices = []
        self.vert_counts = []
        self.face_info = []
        self.edges = []
        self.edge_count = 0
        self.faces = []
        self.face_count = 0

    def parse_face(self, params, texmap=None):
        vert_count = int(params[0])

        vertices = []
        for i in range(vert_count):
            x = float(params[i * 3 + 2])
            y = float(params[i * 3 + 3])
            z = float(params[i * 3 + 4])
            vertex = mathutils.Vector((x, y, z))
            vertices.append(vertex)

        if vert_count == 2:
            self.edge_vert_counts.append(vert_count)
            self.edge_vertices.extend(vertices)
            return

        if vert_count == 4:
            if options.fix_bowtie_quads:
                ba = vertices[1] - vertices[0]
                cb = vertices[2] - vertices[1]
                dc = vertices[3] - vertices[2]
                # ad = vertices[0] - vertices[3]
                ca = vertices[2] - vertices[0]
                db = vertices[3] - vertices[1]

                cA = ba.cross(ca)
                cB = cb.cross(db)
                cC = dc.cross(ca)
                # cD = db.cross(ad)

                dA = cA.dot(cB)
                dB = cB.dot(cC)
                # dC = cC.dot(cD)
                # dD = cD.dot(cA)
                if dA < 0:
                    _c = tuple([x for x in vertices[2]])
                    _d = tuple([x for x in vertices[3]])
                    vertices[2] = _d
                    vertices[3] = _c
                elif dB > 0:
                    _b = tuple([x for x in vertices[1]])
                    _c = tuple([x for x in vertices[2]])
                    vertices[1] = _c
                    vertices[2] = _b

        if vert_count in (3, 4):
            self.vert_counts.append(vert_count)
            self.vertices.extend(vertices)

            color_code = params[1]
            self.face_info.append(FaceInfo(color_code, texmap=texmap))
