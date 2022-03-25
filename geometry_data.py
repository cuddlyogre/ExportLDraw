class FaceData:
    """
    The data required to transform a file's face info into the needed mesh part.
    """

    def __init__(self, color_code, matrix, vertices, texmap=None, pe_texmap=None):
        self.color_code = color_code
        self.matrix = matrix
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

    def add_edge_data(self, color_code, vertices, matrix):
        self.edge_data.append(FaceData(
            color_code=color_code,
            vertices=vertices,
            matrix=matrix,
        ))

    def add_face_data(self, color_code, vertices, matrix, texmap=None, pe_texmap=None):
        self.face_data.append(FaceData(
            color_code=color_code,
            vertices=vertices,
            matrix=matrix,
            texmap=texmap,
            pe_texmap=pe_texmap,
        ))

    def add_line_data(self, color_code, vertices, matrix):
        self.line_data.append(FaceData(
            color_code=color_code,
            vertices=vertices,
            matrix=matrix,
        ))
