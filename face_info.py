class FaceInfo:
    def __init__(self, color_code, cull=False, ccw=False, grain_slope_allowed=False):
        self.color_code = color_code
        self.cull = cull
        self.ccw = ccw
        self.grain_slope_allowed = grain_slope_allowed
