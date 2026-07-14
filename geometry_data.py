from .import_options import ImportOptions
from . import pe_texmap


class FaceData:
    """
    Raw vertex information
    """

    def __init__(self, child_node, matrix, color_code, winding=None, texmap=None, pe_tex_path=None):
        self.child_node = child_node
        self.matrix = matrix
        self.color_code = color_code
        self.winding = winding
        self.texmap = texmap
        self.pe_tex_path = pe_tex_path

        self.vertices = self.child_node.vertices.copy()
        self.vert_count = len(self.vertices)
        # BFC folds the accumulated INVERTNEXT state into self.winding (meta_bfc:
        # a "CCW" statement under accumulated inversion becomes "CW"), so __handle_winding
        # reverses the vertex order here for inverted geometry. The stored order therefore
        # already reflects the face's true outward orientation -- this is our equivalent of
        # Studio reading model.MeshBackFace for inverted meshes, so pe_texmap must NOT flip
        # the projection normal again (doing so double-counts the inversion and drops decals
        # from inverted surfaces, e.g. the inside of a minifig hand grip).
        self.__handle_winding()
        self.pe_texmaps = []

    def __handle_winding(self):
        if self.child_node.meta_command not in ["3", "4"]: return
        if self.winding == "CW":  # else winding == "CCW" or winding is None:
            if self.vert_count == 3:
                self.vertices = [
                    self.vertices[0],
                    self.vertices[2],
                    self.vertices[1],
                ]
            elif self.vert_count == 4:
                self.vertices = [
                    self.vertices[0],
                    self.vertices[3],
                    self.vertices[2],
                    self.vertices[1],
                ]

    def process(self):
        self.__transform_vertices()
        self.__process_bowties()
        self.__process_pe_tex_path()

    # https://github.com/rredford/LdrawToObj/blob/802924fb8d42145c4f07c10824e3a7f2292a6717/LdrawData/LdrawToData.cs#L219
    # https://github.com/rredford/LdrawToObj/blob/802924fb8d42145c4f07c10824e3a7f2292a6717/LdrawData/LdrawToData.cs#L260
    def __transform_vertices(self):
        self.vertices = [self.matrix @ v for v in self.vertices]

    def __process_bowties(self):
        # line type 5 also has 4 vertices
        if self.child_node.meta_command not in ["4"]: return
        if ImportOptions.fix_bowties:
            if self.vert_count == 4:
                FaceData.fix_bowties(self.vertices)

    def __process_pe_tex_path(self):
        # Only the explicit-UV case is resolved per-face. PE_TEX_INFO bounding-box
        # projections are deferred to GeometryData.project_pe_texmaps(), which runs once the
        # whole mesh is collected so the decal can flood-fill across connected faces and
        # follow concave surfaces -- matching Studio's LDrawTextureAtlas.OptimizeMode.
        if self.pe_tex_path is None: return
        self.pe_texmaps = self.pe_tex_path.build_uv_texmaps(self.child_node)

    # handle bowtie quadrilaterals - 6582.dat
    # https://github.com/TobyLobster/ImportLDraw/pull/65/commits/3d8cebee74bf6d0447b616660cc989e870f00085
    @staticmethod
    def fix_bowties(vertices):
        nA = (vertices[1] - vertices[0]).cross(vertices[2] - vertices[0])
        nB = (vertices[2] - vertices[1]).cross(vertices[3] - vertices[1])
        nC = (vertices[3] - vertices[2]).cross(vertices[0] - vertices[2])
        if nA.dot(nB) < 0:
            vertices[2], vertices[3] = vertices[3], vertices[2]
        elif nB.dot(nC) < 0:
            vertices[2], vertices[1] = vertices[1], vertices[2]


class GeometryData:
    """
    Raw mesh data used to build the final mesh.
    """

    def __init__(self):
        self.key = None
        self.file = None
        self.bfc_certified = None
        self.edge_data = []
        self.face_data = []
        self.line_data = []

    def process(self):
        for edge_data in self.edge_data:
            edge_data.process()

        for face_data in self.face_data:
            face_data.process()

        for line_data in self.line_data:
            line_data.process()

    def project_pe_texmaps(self):
        # Run once per mesh, after every face has been collected and transformed, so the
        # PE bounding-box projections can seed + flood-fill across connected faces.
        pe_texmap.project_box_texmaps(self.face_data)

    def add_edge_data(self, child_node, matrix, color_code):
        face_data = FaceData(
            child_node=child_node,
            matrix=matrix,
            color_code=color_code,
        )
        self.edge_data.append(face_data)
        return face_data

    def add_face_data(self, child_node, matrix, color_code, texmap=None, pe_tex_path=None, winding=None):
        face_data = FaceData(
            child_node=child_node,
            matrix=matrix,
            color_code=color_code,
            texmap=texmap,
            pe_tex_path=pe_tex_path,
            winding=winding,
        )
        self.face_data.append(face_data)
        return face_data

    def add_line_data(self, child_node, matrix, color_code):
        face_data = FaceData(
            child_node=child_node,
            matrix=matrix,
            color_code=color_code,
        )
        self.line_data.append(face_data)
        return face_data
