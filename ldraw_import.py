import os
import bpy

from . import options
from . import filesystem

from .ldraw_node import LDrawNode
from .ldraw_file import LDrawFile
from .ldraw_colors import LDrawColors
from .blender_materials import BlenderMaterials
from .special_bricks import SpecialBricks


class LDrawImporter:
    @staticmethod
    def handle_mpd(filepath):
        root_file = None

        if os.path.exists(filepath):
            file_encoding = filesystem.check_encoding(filepath)
            with open(filepath, 'rt', encoding=file_encoding) as file:
                lines = file.read().strip()
                if not lines.lower().startswith("0 f"):
                    return filepath
                lines = lines.splitlines()

                current_file = None
                for line in lines:
                    params = line.strip().split()

                    if len(params) == 0:
                        continue

                    while len(params) < 9:
                        params.append("")

                    if params[0] == "0" and params[1].lower() == "file":
                        LDrawImporter.parse_current_file(current_file)
                        current_file = LDrawFile(line[7:].lower())
                        current_file.lines = []

                        if root_file is None:
                            root_file = line[7:].lower()

                    elif params[0] == "0" and params[1].lower() == "nofile":
                        LDrawImporter.parse_current_file(current_file)
                        current_file = None

                    else:
                        if current_file is not None:
                            current_file.lines.append(line)

                LDrawImporter.parse_current_file(current_file)

        if root_file is not None:
            return root_file
        return filepath

    @staticmethod
    def parse_current_file(ldraw_file):
        if ldraw_file is not None:
            LDrawFile.mpd_file_cache[ldraw_file.filepath] = ldraw_file

    @staticmethod
    def do_import(filename, ldraw_path, clear_cache=False):
        bpy.context.scene.eevee.use_ssr = True
        bpy.context.scene.eevee.use_ssr_refraction = True
        bpy.context.scene.eevee.use_taa_reprojection = True

        if clear_cache or options.first_run:
            filesystem.reset_caches()
            filesystem.append_search_paths(ldraw_path)

            LDrawColors.reset_caches()
            LDrawColors.read_color_table(ldraw_path)

            SpecialBricks.reset_caches()
            SpecialBricks.build_slope_angles()

            LDrawFile.reset_caches()
            LDrawNode.reset_caches()

        BlenderMaterials.reset_caches()
        BlenderMaterials.create_blender_node_groups()

        options.first_run = False

        LDrawNode.reset()

        filename = LDrawImporter.handle_mpd(filename)
        ldraw_file = LDrawFile(filename)
        ldraw_file.read_file()
        ldraw_file.parse_file()

        root_node = LDrawNode(ldraw_file)
        root_node.load()

        if ldraw_file.name in bpy.data.collections:
            root_collection = bpy.data.collections[ldraw_file.name]
            if ldraw_file.name not in bpy.context.scene.collection.children:
                bpy.context.scene.collection.children.link(root_collection)

        if options.meta_step:
            if options.set_end_frame:
                bpy.context.scene.frame_end = LDrawNode.last_frame + options.frames_per_step
                bpy.context.scene.frame_set(bpy.context.scene.frame_end)

        # https://blender.stackexchange.com/questions/38611/setting-camera-clip-end-via-python
        clip_end = 10000
        if bpy.context.scene.camera is not None:
            bpy.context.scene.camera.data.clip_end = clip_end

        for area in bpy.context.screen.areas:
            if area.type == 'VIEW_3D':
                for space in area.spaces:
                    if space.type == 'VIEW_3D':
                        space.clip_end = 10000
