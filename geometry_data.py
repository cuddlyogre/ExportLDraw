class FaceData:
    """
    The data required to transform a file's face info into the needed mesh part.
    """

    def __init__(self, color_code, vertices, texmap=None, pe_texmap=None):
        self.color_code = color_code
        self.vertices = vertices
        self.texmap = texmap
        self.pe_texmap = pe_texmap


class GeometryData:
    """
    Accumulated FaceData used to build the final mesh.
    """

    def __init__(self):
        self.edge_data = []
        self.face_data = []
        self.line_data = []
        self.edge_vert_count = 0
        self.face_vert_count = 0
        self.line_vert_count = 0

    def add_edge_data(self, color_code, vertices):
        self.edge_vert_count += len(vertices)
        self.edge_data.append(FaceData(
            color_code=color_code,
            vertices=vertices
        ))

    def add_face_data(self, color_code, vertices, texmap=None, pe_texmap=None):
        self.face_vert_count += len(vertices)
        self.face_data.append(FaceData(
            color_code=color_code,
            vertices=vertices,
            texmap=texmap,
            pe_texmap=pe_texmap,
        ))

    def add_line_data(self, color_code, vertices):
        self.line_vert_count += len(vertices)
        self.line_data.append(FaceData(
            color_code=color_code,
            vertices=vertices
        ))
