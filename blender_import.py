import bpy
import bmesh

from .blender_materials import BlenderMaterials
from .import_options import ImportOptions
from .ldraw_file import LDrawFile
from .ldraw_node import LDrawNode
from .filesystem import FileSystem
from . import blender_camera
from .ldraw_colors import LDrawColor
from . import helpers
from . import strings

from . import group


def do_import(filepath):
    print(filepath)  # TODO: multiple filepaths?

    __scene_setup()
    LDrawFile.reset_caches()
    LDrawNode.reset_caches()
    FileSystem.build_search_paths(parent_filepath=filepath)
    LDrawFile.read_color_table()
    BlenderMaterials.create_blender_node_groups()

    ldraw_file = LDrawFile.get_cached_file(filepath)
    if ldraw_file is None:
        return

    if ldraw_file.is_configuration():
        __load_materials(ldraw_file)
        return

    root_node = LDrawNode()
    root_node.is_root = True
    root_node.file = ldraw_file
    root_node.load()

    if ImportOptions.meta_step:
        if ImportOptions.set_end_frame:
            bpy.context.scene.frame_end = LDrawNode.current_frame + ImportOptions.frames_per_step
            bpy.context.scene.frame_set(bpy.context.scene.frame_end)

    max_clip_end = 0
    for camera in LDrawNode.cameras:
        camera = blender_camera.create_camera(camera, empty=LDrawNode.top_empty, collection=LDrawNode.top_collection)
        if bpy.context.scene.camera is None:
            if camera.data.clip_end > max_clip_end:
                max_clip_end = camera.data.clip_end
            bpy.context.scene.camera = camera

    for area in bpy.context.screen.areas:
        if area.type == "VIEW_3D":
            for space in area.spaces:
                if space.type == "VIEW_3D":
                    if space.clip_end < max_clip_end:
                        space.clip_end = max_clip_end


def __scene_setup():
    bpy.context.scene.eevee.use_ssr = True
    bpy.context.scene.eevee.use_ssr_refraction = True
    bpy.context.scene.eevee.use_taa_reprojection = True

    # https://blender.stackexchange.com/a/146838
    if ImportOptions.use_freestyle_edges:
        bpy.context.scene.render.use_freestyle = True
        linesets = bpy.context.view_layer.freestyle_settings.linesets
        if len(linesets) < 1:
            linesets.new("LDraw LineSet")
        lineset = linesets[0]
        # lineset.linestyle.color = color.edge_color
        lineset.select_by_visibility = True
        lineset.select_by_edge_types = True
        lineset.select_by_face_marks = False
        lineset.select_by_collection = False
        lineset.select_by_image_border = False
        lineset.visibility = 'VISIBLE'
        lineset.edge_type_negation = 'INCLUSIVE'
        lineset.edge_type_combination = 'OR'
        lineset.select_silhouette = False
        lineset.select_border = False
        lineset.select_contour = False
        lineset.select_suggestive_contour = False
        lineset.select_ridge_valley = False
        lineset.select_crease = False
        lineset.select_edge_mark = True
        lineset.select_external_contour = False
        lineset.select_material_boundary = False


def __load_materials(file):
    colors = {}
    group_name = 'blank'
    for line in file.lines:
        clean_line = helpers.clean_line(line)
        strip_line = line.strip()

        if clean_line.startswith('0 // LDraw'):
            group_name = clean_line
            colors[group_name] = []
            continue

        if clean_line.startswith("0 !COLOUR"):
            _params = helpers.get_params(clean_line, "0 !COLOUR ", lowercase=False)
            colors[group_name].append(LDrawColor.parse_color(_params))
            continue

    j = 0
    for collection_name, codes in colors.items():
        collection = group.get_collection(collection_name, bpy.context.scene.collection)

        for i, color_code in enumerate(codes):
            bm = bmesh.new()

            monkey = True
            if monkey:
                prefix = 'monkey'
                bmesh.ops.create_monkey(bm)
            else:
                prefix = 'cube'
                bmesh.ops.create_cube(bm, size=1.0)

            helpers.ensure_bmesh(bm)

            for f in bm.faces:
                f.smooth = True

            mesh = bpy.data.meshes.new(f"{prefix}_{color_code}")
            mesh[strings.ldraw_color_code_key] = color_code

            material = BlenderMaterials.get_material(color_code)

            # https://blender.stackexchange.com/questions/23905/select-faces-depending-on-material
            if material.name not in mesh.materials:
                mesh.materials.append(material)
            for face in bm.faces:
                face.material_index = mesh.materials.find(material.name)

            helpers.finish_bmesh(bm, mesh)

            mesh.validate()
            mesh.update(calc_edges=True)

            obj = bpy.data.objects.new(mesh.name, mesh)
            obj[strings.ldraw_filename_key] = file.name
            obj[strings.ldraw_color_code_key] = color_code

            obj.modifiers.new("Subdivision", type='SUBSURF')
            obj.location.x = i * 3
            obj.location.y = -j * 3

            color = LDrawColor.get_color(color_code)
            obj.color = color.color_a

            group.link_obj(collection, obj)
        j += 1
