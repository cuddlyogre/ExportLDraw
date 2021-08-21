from . import matrices

cameras = []


def reset_caches():
    global cameras
    cameras = []


class LDrawCamera:
    """Data about a camera"""

    def __init__(self):
        self.hidden = False
        self.orthographic = False
        self.fov = 30.0
        self.z_near = 1.0
        self.z_far = 10000.0
        self.position = matrices.Vector((0.0, 0.0, 0.0))
        self.target_position = matrices.Vector((1.0, 0.0, 0.0))
        self.up_vector = matrices.Vector((0.0, 1.0, 0.0))
        self.name = "Camera"
