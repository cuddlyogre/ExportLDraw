import os
import bpy

from . import filesystem
from .ldraw_file import LDrawNode
from .ldraw_file import LDrawFile
from .ldraw_colors import LDrawColors
from .blender_materials import BlenderMaterials
from .special_bricks import SpecialBricks


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
                    parse_current_file(current_file)
                    current_file = LDrawFile(line[7:].lower())
                    current_file.lines = []

                    if root_file is None:
                        root_file = line[7:].lower()

                elif params[0] == "0" and params[1].lower() == "nofile":
                    parse_current_file(current_file)
                    current_file = None

                else:
                    if current_file is not None:
                        current_file.lines.append(line)

            parse_current_file(current_file)

    if root_file is not None:
        return root_file
    return filepath


def parse_current_file(current_file):
    if current_file is not None:
        LDrawNode.mpd_file_cache[current_file.filepath] = current_file


def do_import(filepath, ldraw_path, clear_cache=False):
    bpy.context.scene.eevee.use_ssr = True
    bpy.context.scene.eevee.use_ssr_refraction = True
    bpy.context.scene.eevee.use_taa_reprojection = True

    LDrawNode.current_group = None
    LDrawFile.current_step = 0

    if clear_cache or LDrawNode.first_run:
        filesystem.search_paths = []
        filesystem.append_search_paths(ldraw_path)

        LDrawColors.colors = {}
        LDrawColors.read_color_table(ldraw_path)

        SpecialBricks.slope_angles = {}
        SpecialBricks.build_slope_angles()

        LDrawNode.file_cache = {}
        LDrawNode.mpd_file_cache = {}
        LDrawNode.vertex_cache = {}
        LDrawNode.face_info_cache = {}
        LDrawNode.geometry_cache = {}

        LDrawNode.first_run = False

    BlenderMaterials.material_list = {}
    BlenderMaterials.create_blender_node_groups()

    filepath = handle_mpd(filepath)
    root_node = LDrawNode(filepath)
    root_node.load()

    if root_node.file.name in bpy.data.collections:
        root_collection = bpy.data.collections[root_node.file.name]
        if root_node.file.name not in bpy.context.scene.collection.children:
            bpy.context.scene.collection.children.link(root_collection)

    if LDrawFile.meta_step:
        if LDrawFile.current_step > 0:
            bpy.context.scene.frame_end = bpy.context.scene.frame_current + 3
            bpy.context.scene.frame_set(bpy.context.scene.frame_end)

    # if clip_end
    # bpy.context.space_data.clip_end = 10000
