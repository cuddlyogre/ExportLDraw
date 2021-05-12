import bpy
import mathutils
import math

from . import options

cameras = []


def reset_caches():
    global cameras
    cameras = []


def look_at(obj, target_location, up_vector):
    # back vector is a vector pointing from the target to the camera
    back = obj.location - target_location
    back.normalize()

    # If our back and up vectors are very close to pointing the same way (or opposite), choose a different up_vector
    if abs(back.dot(up_vector)) > 0.9999:
        up_vector = mathutils.Vector((0.0, 0.0, 1.0))
        if abs(back.dot(up_vector)) > 0.9999:
            up_vector = mathutils.Vector((1.0, 0.0, 0.0))

    right = up_vector.cross(back)
    right.normalize()

    up = back.cross(right)
    up.normalize()

    row1 = [right.x, up.x, back.x, obj.location.x]
    row2 = [right.y, up.y, back.y, obj.location.y]
    row3 = [right.z, up.z, back.z, obj.location.z]
    row4 = [0.0, 0.0, 0.0, 1.0]

    obj.matrix_world = mathutils.Matrix((row1, row2, row3, row4))


def create_camera(camera, empty=None, collection=None):
    blender_camera = bpy.data.cameras.new(camera.name)

    obj = bpy.data.objects.new(camera.name, blender_camera)

    obj.name = camera.name
    obj.location = camera.position
    obj.hide_viewport = camera.hidden
    obj.hide_render = camera.hidden

    blender_camera.sensor_fit = "VERTICAL"
    # camera.sensor_height = self.fov
    blender_camera.lens_unit = "FOV"
    blender_camera.angle = math.radians(camera.fov)  # self.fov * 3.1415926 / 180.0
    blender_camera.clip_start = camera.z_near
    blender_camera.clip_end = camera.z_far

    if camera.orthographic:
        dist_target_to_camera = (camera.position - camera.target_position).length
        blender_camera.ortho_scale = dist_target_to_camera / 1.92
        blender_camera.type = "ORTHO"
    else:
        blender_camera.type = "PERSP"

    blender_camera.clip_start = blender_camera.clip_start * options.import_scale
    blender_camera.clip_end = blender_camera.clip_end * options.import_scale

    location = obj.location.copy()
    location.x = location.x * options.import_scale
    location.y = location.y * options.import_scale
    location.z = location.z * options.import_scale
    obj.location = location
    # bpy.context.view_layer.update()

    camera.target_position.x = camera.target_position.x * options.import_scale
    camera.target_position.y = camera.target_position.y * options.import_scale
    camera.target_position.z = camera.target_position.z * options.import_scale

    camera.up_vector.x = camera.up_vector.x * options.import_scale
    camera.up_vector.y = camera.up_vector.y * options.import_scale
    camera.up_vector.z = camera.up_vector.z * options.import_scale

    if collection is None:
        collection = bpy.context.scene.collection
    if obj.name not in collection:
        collection.objects.link(obj)

    # https://blender.stackexchange.com/a/72899
    # https://blender.stackexchange.com/a/154926
    # https://blender.stackexchange.com/a/29148
    # when parenting the location of the parented obj is affected by the transform of the empty
    # this undoes the transform of the empty
    obj.parent = empty
    if obj.parent is not None:
        obj.matrix_parent_inverse = obj.parent.matrix_world.inverted()

    # https://docs.blender.org/api/current/info_gotcha.html#stale-data
    # https://blenderartists.org/t/how-to-avoid-bpy-context-scene-update/579222/6
    # https://blenderartists.org/t/where-do-matrix-changes-get-stored-before-view-layer-update/1182838
    bpy.context.view_layer.update()

    look_at(obj, camera.target_position, camera.up_vector)

    return obj


class LDrawCamera:
    """Data about a camera"""

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
