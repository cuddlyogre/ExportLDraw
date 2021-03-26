class FaceInfo:
    def __init__(self, color_code, use_edge_color=False, grain_slope_allowed=False, texmap=None):
        self.color_code = color_code
        self.use_edge_color = use_edge_color
        self.grain_slope_allowed = grain_slope_allowed
        self.texmap = texmap
