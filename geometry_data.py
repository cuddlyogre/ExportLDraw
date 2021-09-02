class FaceInfo:
    """
    A file's face information. The raw model data before any transforms.
    """

    def __init__(self, color_code, vertices, texmap=None):
        self.color_code = color_code
        self.vertices = vertices
        self.texmap = texmap


class GeometryData:
    """
    Accumulated FaceData used to build the final mesh.
    """

    def __init__(self):
        self.edge_data = []
        self.face_data = []
        self.edge_vert_count = 0
        self.face_vert_count = 0

    def add_edge_data(self, matrix, color_code, geometry):
        self.edge_vert_count += geometry.edge_vert_count
        self.edge_data.append(FaceData(
            matrix=matrix,
            color_code=color_code,
            face_infos=geometry.edge_infos,
        ))

    def add_face_data(self, matrix, color_code, geometry):
        self.face_vert_count += geometry.face_vert_count
        self.face_data.append(FaceData(
            matrix=matrix,
            color_code=color_code,
            face_infos=geometry.face_infos,
        ))


class FaceData:
    """
    The data required to transform a file's face info into the needed mesh part.
    """

    def __init__(self, matrix, color_code, face_infos):
        self.matrix = matrix
        self.color_code = color_code
        self.face_infos = face_infos
