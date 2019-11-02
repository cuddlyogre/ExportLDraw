import mathutils
from .face_info import FaceInfo


class LDrawGeometry:
    def __init__(self):
        self.verts = []
        self.edges = []
        self.edge_indices = []
        self.faces = []
        self.face_info = []

    def parse_edge(self, params):
        vert_count = int(params[0])
        color_code = params[1]

        if color_code != "24":
            return

        verts = []
        for i in range(vert_count):
            vert = mathutils.Vector((float(params[i * 3 + 2]), float(params[i * 3 + 3]), float(params[i * 3 + 4])))
            verts.append(vert)

        self.edges.extend(verts)

    def parse_face(self, params, bfc_cull, bfc_winding_ccw):
        vert_count = int(params[0])
        color_code = params[1]

        verts = []
        for i in range(vert_count):
            vert = mathutils.Vector((float(params[i * 3 + 2]), float(params[i * 3 + 3]), float(params[i * 3 + 4])))
            verts.append(vert)

        # https://wiki.ldraw.org/wiki/LDraw_Files_Requirements#Complex_quadrilaterals
        if vert_count == 4:
            vA = (verts[1] - verts[0]).cross(verts[2] - verts[0])
            vB = (verts[2] - verts[1]).cross(verts[3] - verts[1])
            if vA.dot(vB) < 0:
                verts[2], verts[3] = verts[3], verts[2]

        all_vert_count = len(self.verts)
        new_face = list(range(all_vert_count, all_vert_count + vert_count))
        self.verts.extend(verts)
        self.faces.append(new_face)
        self.face_info.append(FaceInfo(color_code, bfc_cull, bfc_winding_ccw))
