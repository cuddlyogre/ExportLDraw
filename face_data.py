class FaceData:
    def __init__(self, matrix, color_code, face_vertices, face_infos):
        self.matrix = matrix
        self.color_code = color_code
        self.face_vertices = face_vertices
        self.face_infos = face_infos


class EdgeData:
    def __init__(self, matrix, color_code, edge_vertices):
        self.matrix = matrix
        self.color_code = color_code
        self.edge_vertices = edge_vertices
