import mathutils


class PETexInfo:
    def __init__(self, image=None, matrix=None, v1=None, v2=None):
        self.image = image
        self.matrix = matrix
        self.v1 = v1
        self.v2 = v2


class PETexmap:
    def __init__(self):
        self.texture = None
        self.uvs = []

    def uv_unwrap_face(self, bm, face):
        uv_layer = bm.loops.layers.uv.verify()
        for i, loop in enumerate(face.loops):
            loop[uv_layer].uv = self.uvs[i]
