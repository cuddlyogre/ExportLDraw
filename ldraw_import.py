import bpy

from . import options
from . import filesystem

from .ldraw_node import LDrawNode
from .ldraw_file import LDrawFile
from .ldraw_camera import LDrawCamera
from .blender_materials import BlenderMaterials
from .special_bricks import SpecialBricks


class LDrawImporter:
    @staticmethod
    def do_import(filename):
        bpy.context.scene.eevee.use_ssr = True
        bpy.context.scene.eevee.use_ssr_refraction = True
        bpy.context.scene.eevee.use_taa_reprojection = True

        SpecialBricks.build_slope_angles()
        LDrawFile.reset_caches()
        LDrawNode.reset_caches()
        LDrawCamera.reset_caches()
        filesystem.build_search_paths()
        LDrawFile.read_color_table()
        BlenderMaterials.create_blender_node_groups()

        filename = LDrawFile.handle_mpd(filename)
        if filename is None:
            return

        ldraw_file = LDrawFile(filename)
        ldraw_file.read_file()
        ldraw_file.parse_file()

        root_node = LDrawNode(ldraw_file)
        root_node.load()

        if LDrawNode.get_top_collection() is not None:
            bpy.context.scene.collection.children.link(LDrawNode.get_top_collection())

        if options.meta_step:
            if options.set_end_frame:
                bpy.context.scene.frame_end = LDrawNode.last_frame + options.frames_per_step
                bpy.context.scene.frame_set(bpy.context.scene.frame_end)

        for area in bpy.context.screen.areas:
            if area.type == 'VIEW_3D':
                for space in area.spaces:
                    if space.type == 'VIEW_3D':
                        space.clip_end = options.camera_far #* options.scale

        for camera in LDrawCamera.get_cameras():
            camera = camera.create_camera_node(empty=LDrawNode.get_top_empty(), collection=LDrawNode.get_top_collection())
            if bpy.context.scene.camera is None:
                bpy.context.scene.camera = camera
