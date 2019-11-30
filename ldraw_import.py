import os
import bpy

from . import filesystem
from .ldraw_file import LDrawNode
from .ldraw_file import LDrawFile
from .ldraw_colors import LDrawColors
from .blender_materials import BlenderMaterials
from .special_bricks import SpecialBricks

reuse_mesh_data = True


def do_import(filepath, ldraw_path):
    bpy.context.scene.eevee.use_ssr = True
    bpy.context.scene.eevee.use_ssr_refraction = True
    bpy.context.scene.eevee.use_taa_reprojection = True

    filesystem.search_paths = []
    filesystem.append_search_paths(ldraw_path)

    LDrawColors.colors = {}
    LDrawColors.read_color_table(ldraw_path)

    LDrawNode.file_cache = {}
    LDrawNode.face_info_cache = {}
    LDrawNode.geometry_cache = {}

    BlenderMaterials.material_list = {}
    BlenderMaterials.create_blender_node_groups()

    SpecialBricks.slope_angles = {}
    SpecialBricks.build_slope_angles()

    root_file = None

    if os.path.exists(filepath):
        file_encoding = filesystem.check_encoding(filepath)
        with open(filepath, 'rt', encoding=file_encoding) as file:
            lines = file.read().strip().splitlines()
            current_file = None
            for line in lines:
                params = line.strip().split()

                if len(params) == 0:
                    continue

                if params[0] == "0" and params[1] == "FILE":
                    while len(params) < 3:
                        params.append("")

                    if current_file is None:
                        current_file = LDrawFile(params[2])
                        current_file.lines = []

                    if root_file is None:
                        root_file = params[2]

                elif params[0] == "0" and params[1] == "NOFILE":
                    if current_file is not None:
                        current_file.parse_file()
                        LDrawNode.file_cache[current_file.filepath] = current_file
                        current_file = None

                else:
                    if current_file is not None:
                        current_file.lines.append(line)

    if root_file is not None:
        filepath = root_file

    root_node = LDrawNode(filepath)
    root_node.load()

    for name in ['Parts', 'Edges']:
        if name in bpy.data.collections:
            if name not in bpy.context.scene.collection.children:
                collection = bpy.data.collections[name]
                bpy.context.scene.collection.children.link(collection)
