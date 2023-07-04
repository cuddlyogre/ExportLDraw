import mathutils

cameras = []


def reset_caches():
    global cameras
    cameras.clear()


class LDrawCamera:
    """Data about a camera"""

    def __init__(self):
        self.hidden = False
        self.orthographic = False
        self.fov = 30.0
        self.z_near = 1.0
        self.z_far = 10000.0
        self.position = mathutils.Vector((0.0, 0.0, 0.0))
        self.target_position = mathutils.Vector((1.0, 0.0, 0.0))
        self.up_vector = mathutils.Vector((0.0, 1.0, 0.0))
        self.name = "Camera"
