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

    def add_edge_data(self, matrix, color_code, face_info):
        self.edge_vert_count += len(face_info.vertices)
        self.edge_data.append(FaceData(
            matrix=matrix,
            color_code=color_code,
            face_infos=face_info,
        ))

    def add_face_data(self, matrix, color_code, face_info):
        self.face_vert_count += len(face_info.vertices)
        self.face_data.append(FaceData(
            matrix=matrix,
            color_code=color_code,
            face_infos=face_info,
        ))

    def add_line_data(self, matrix, color_code, face_info):
        self.line_vert_count += len(face_info.vertices)
        self.line_data.append(FaceData(
            matrix=matrix,
            color_code=color_code,
            face_infos=face_info,
        ))


class FaceData:
    """
    The data required to transform a file's face info into the needed mesh part.
    """

    def __init__(self, matrix, color_code, face_infos):
        self.matrix = matrix
        self.color_code = color_code
        self.face_infos = face_infos
