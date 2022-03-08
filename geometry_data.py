class FaceData:
    """
    The data required to transform a file's face info into the needed mesh part.
    """

    def __init__(self, color_code, matrix, face_info, winding=None, texmap=None, pe_texmap=None):
        self.matrix = matrix
        self.color_code = color_code
        self.face_info = face_info
        self.winding = winding
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

    def add_edge_data(self, matrix, color_code, face_info):
        self.edge_vert_count += face_info.vert_count()
        self.edge_data.append(FaceData(
            color_code=color_code,
            matrix=matrix,
            face_info=face_info
        ))

    def add_face_data(self, matrix, color_code, face_info, winding=None, texmap=None, pe_texmap=None):
        self.face_vert_count += face_info.vert_count()
        self.face_data.append(FaceData(
            color_code=color_code,
            matrix=matrix,
            face_info=face_info,
            winding=winding,
            texmap=texmap,
            pe_texmap=pe_texmap,
        ))

    def add_line_data(self, matrix, color_code, face_info):
        self.line_vert_count += face_info.vert_count()
        self.line_data.append(FaceData(
            color_code=color_code,
            matrix=matrix,
            face_info=face_info
        ))
