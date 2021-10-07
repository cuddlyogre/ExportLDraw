class FaceInfo:
    """
    A file's face information. The raw model data before any transforms.
    """

    def __init__(self, color_code, vertices, texmap=None):
        self.color_code = color_code
        self.vertices = vertices
        self.texmap = texmap
