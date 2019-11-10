import mathutils
from .face_info import FaceInfo


class LDrawGeometry:
    def __init__(self):
        self.vertices = []
        self.edges = []
        self.edge_indices = []
        self.faces = []
        self.face_info = []

    def parse_edge(self, params):
        vert_count = int(params[0])
        color_code = params[1]

        if color_code != "24":
            return

        vertices = []
        for i in range(vert_count):
            vertex = mathutils.Vector((float(params[i * 3 + 2]), float(params[i * 3 + 3]), float(params[i * 3 + 4])))
            vertices.append(vertex)

        self.edges.extend(vertices)

    def parse_face(self, params, bfc_cull, bfc_winding_ccw):
        vert_count = int(params[0])
        color_code = params[1]

        vertices = []
        for i in range(vert_count):
            vertex = mathutils.Vector((float(params[i * 3 + 2]), float(params[i * 3 + 3]), float(params[i * 3 + 4])))
            vertices.append(vertex)

        # https://wiki.ldraw.org/wiki/LDraw_Files_Requirements#Complex_quadrilaterals
        if vert_count == 4:
            vA = (vertices[1] - vertices[0]).cross(vertices[2] - vertices[0])
            vB = (vertices[2] - vertices[1]).cross(vertices[3] - vertices[1])
            if vA.dot(vB) < 0:
                vertices[2], vertices[3] = vertices[3], vertices[2]

        all_vert_count = len(self.vertices)
        new_face = list(range(all_vert_count, all_vert_count + vert_count))
        self.vertices.extend(vertices)
        self.faces.append(new_face)
        self.face_info.append(FaceInfo(color_code, bfc_cull, bfc_winding_ccw))
