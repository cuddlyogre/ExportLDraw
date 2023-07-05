class FaceData:
    """
    The data required to transform a file's face info into the needed mesh part.
    """

    def __init__(self, vertices, color_code, texmap=None, pe_texmap=None):
        self.vertices = vertices
        self.color_code = color_code
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

    def add_edge_data(self, vertices, color_code):
        self.edge_data.append(FaceData(
            vertices=vertices,
            color_code=color_code,
        ))

    def add_face_data(self, vertices, color_code, texmap=None, pe_texmap=None):
        self.face_data.append(FaceData(
            vertices=vertices,
            color_code=color_code,
            texmap=texmap,
            pe_texmap=pe_texmap,
        ))

    def add_line_data(self, vertices, color_code):
        self.line_data.append(FaceData(
            vertices=vertices,
            color_code=color_code,
        ))
