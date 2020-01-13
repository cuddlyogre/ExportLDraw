import bpy
import mathutils
import math

from . import options


class LDrawCamera:
    """Data about a camera"""

    cameras = []

    def __init__(self):
        self.hidden = False
        self.orthographic = False
        self.fov = options.camera_fov
        self.z_near = options.camera_near
        self.z_far = options.camera_far
        self.position = mathutils.Vector((0.0, 0.0, 0.0))
        self.target_position = mathutils.Vector((1.0, 0.0, 0.0))
        self.up_vector = mathutils.Vector((0.0, 1.0, 0.0))
        self.name = "Camera"

    @classmethod
    def reset(cls):
        cls.cameras = []

    @staticmethod
    def get_cameras():
        return LDrawCamera.cameras

    def create_camera_node(self, empty=None, collection=None):
        camera = bpy.data.cameras.new(self.name)
        obj = bpy.data.objects.new(self.name, camera)

        obj.name = self.name
        obj.location = self.position
        obj.hide_viewport = self.hidden
        obj.hide_render = self.hidden

        camera.sensor_fit = 'VERTICAL'
        # camera.sensor_height = self.fov
        camera.lens_unit = 'FOV'
        camera.angle = math.radians(self.fov)  # self.fov * 3.1415926 / 180.0
        camera.clip_start = self.z_near
        camera.clip_end = self.z_far

        if self.orthographic:
            dist_target_to_camera = (self.position - self.target_position).length
            camera.ortho_scale = dist_target_to_camera / 1.92
            camera.type = 'ORTHO'
        else:
            camera.type = 'PERSP'

        obj.parent = empty
        if collection is None:
            collection = bpy.context.scene.collection
        if obj.name not in collection:
            collection.objects.link(obj)

        LDrawCamera.look_at(obj, self.target_position, self.up_vector)

        return obj

    @staticmethod
    def look_at(obj, target_location, up_vector):
        obj.matrix_parent_inverse = obj.parent.matrix_world.inverted()
        bpy.context.view_layer.update()

        location = obj.matrix_world.to_translation()

        location.x = location.x * options.scale
        location.y = location.y * options.scale
        location.z = location.z * options.scale

        target_location.x = target_location.x * options.scale
        target_location.y = target_location.y * options.scale
        target_location.z = target_location.z * options.scale

        up_vector.x = up_vector.x * options.scale
        up_vector.y = up_vector.y * options.scale
        up_vector.z = up_vector.z * options.scale

        # back vector is a vector pointing from the target to the camera
        back = location - target_location
        back.normalize()

        obj.data.clip_start = obj.data.clip_start * options.scale
        obj.data.clip_end = obj.data.clip_end * options.scale
        obj.data.clip_end = obj.data.clip_end * options.scale

        # If our back and up vectors are very close to pointing the same way (or opposite), choose a different up_vector
        if abs(back.dot(up_vector)) > 0.9999:
            up_vector = mathutils.Vector((0.0, 0.0, 1.0))
            if abs(back.dot(up_vector)) > 0.9999:
                up_vector = mathutils.Vector((1.0, 0.0, 0.0))

        right = up_vector.cross(back)
        right.normalize()

        up = back.cross(right)
        up.normalize()

        row1 = [right.x, up.x, back.x, location.x]
        row2 = [right.y, up.y, back.y, location.y]
        row3 = [right.z, up.z, back.z, location.z]
        row4 = [0.0, 0.0, 0.0, 1.0]

        obj.matrix_world = mathutils.Matrix((row1, row2, row3, row4))

    @staticmethod
    def add_camera(ldraw_camera):
        LDrawCamera.cameras.append(ldraw_camera)
