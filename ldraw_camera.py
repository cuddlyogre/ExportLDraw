from . import options
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
        self.fov = options.camera_fov
        self.z_near = options.camera_near
        self.z_far = options.camera_far
        self.position = matrices.Vector((0.0, 0.0, 0.0))
        self.target_position = matrices.Vector((1.0, 0.0, 0.0))
        self.up_vector = matrices.Vector((0.0, 1.0, 0.0))
        self.name = "Camera"
