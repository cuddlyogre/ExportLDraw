class FaceInfo:
    def __init__(self, color_code, use_edge_color=False, texmap=None):
        self.color_code = color_code
        self.use_edge_color = use_edge_color
        self.texmap = texmap
        self.vertices = []
