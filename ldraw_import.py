import bpy

from . import options
from . import filesystem

from . import ldraw_node
from . import ldraw_file
from . import ldraw_camera
from . import blender_materials
from . import special_bricks


def do_import(filename):
    bpy.context.scene.eevee.use_ssr = True
    bpy.context.scene.eevee.use_ssr_refraction = True
    bpy.context.scene.eevee.use_taa_reprojection = True

    special_bricks.build_slope_angles()
    ldraw_file.reset_caches()
    ldraw_node.reset_caches()
    ldraw_camera.reset_caches()
    filesystem.build_search_paths()
    ldraw_file.read_color_table()
    blender_materials.create_blender_node_groups()

    if options.all_materials:
        blender_materials.create_ldraw_materials()

    filename = ldraw_file.handle_mpd(filename)
    if filename is None:
        return

    file = ldraw_file.LDrawFile(filename)
    file.read_file()
    file.parse_file()

    root_node = ldraw_node.LDrawNode(file)
    root_node.load()

    if ldraw_node.top_collection is not None:
        bpy.context.scene.collection.children.link(ldraw_node.top_collection)

    if options.meta_step:
        if options.set_end_frame:
            bpy.context.scene.frame_end = ldraw_node.last_frame + options.frames_per_step
            bpy.context.scene.frame_set(bpy.context.scene.frame_end)

    for area in bpy.context.screen.areas:
        if area.type == "VIEW_3D":
            for space in area.spaces:
                if space.type == "VIEW_3D":
                    space.clip_end = options.camera_far  # * options.import_scale

    for camera in ldraw_camera.cameras:
        blender_camera = ldraw_camera.create_camera(camera, empty=ldraw_node.top_empty, collection=ldraw_node.top_collection)
        if bpy.context.scene.camera is None:
            bpy.context.scene.camera = blender_camera
