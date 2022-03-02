import mathutils


class FaceInfo:
    """
    A file's face information. The raw model data before any transforms.
    """

    def __init__(self, color_code, vertices):
        self.color_code = color_code
        self.vertices = vertices

    def vert_count(self):
        return len(self.vertices)


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

    def vert_count(self):
        return self.edge_vert_count + self.face_vert_count + self.line_vert_count

    def parse_face(self, _params, inverted=False):
        line_type = _params[0]

        color_code = _params[1]

        if line_type == "2":
            vert_count = 2
        elif line_type == "3":
            vert_count = 3
        elif line_type == "4":
            vert_count = 4
        elif line_type == "5":
            vert_count = 2
        else:
            return

        verts = []
        for i in range(vert_count):
            if inverted:
                z = float(_params[i * 3 + 4])
                y = float(_params[i * 3 + 3])
                x = float(_params[i * 3 + 2])
            else:
                x = float(_params[i * 3 + 2])
                y = float(_params[i * 3 + 3])
                z = float(_params[i * 3 + 4])
            vertex = mathutils.Vector((x, y, z))
            verts.append(vertex)

        if line_type == "2":
            face_info = FaceInfo(color_code, verts)
            self.edge_vert_count += face_info.vert_count()
            self.edge_infos.append(face_info)
            return face_info
        elif line_type == "3":
            face_info = FaceInfo(color_code, verts)
            self.face_vert_count += face_info.vert_count()
            self.face_infos.append(face_info)
            return face_info
        elif line_type == "4":
            face_info = FaceInfo(color_code, verts)
            self.face_vert_count += face_info.vert_count()
            self.face_infos.append(face_info)
            return face_info
        elif line_type == "5":
            face_info = FaceInfo(color_code, verts)
            self.line_vert_count += face_info.vert_count()
            self.line_infos.append(face_info)
            return face_info
