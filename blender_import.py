import bpy
import bmesh

from .blender_materials import BlenderMaterials
from .import_options import ImportOptions
from .ldraw_file import LDrawFile
from .ldraw_node import LDrawNode
from .filesystem import FileSystem
from .ldraw_color import LDrawColor
from . import blender_camera
from . import helpers
from . import strings
from . import group
from . import ldraw_meta
from . import ldraw_object
from . import matrices


def do_import(filepath):
    print(filepath)  # TODO: multiple filepaths?

    __scene_setup()

    LDrawFile.reset_caches()
    LDrawNode.reset_caches()
    group.reset_caches()
    ldraw_meta.reset_caches()
    ldraw_object.reset_caches()
    matrices.reset_caches()

    FileSystem.build_search_paths(parent_filepath=filepath)
    LDrawFile.read_color_table()
    BlenderMaterials.create_blender_node_groups()

    ldraw_file = LDrawFile.get_file(filepath)
    if ldraw_file is None:
        return

    if ldraw_file.is_configuration():
        __load_materials(ldraw_file)
        return

    ldraw_meta.meta_step()

    root_node = LDrawNode()
    root_node.is_root = True
    root_node.file = ldraw_file

    group.groups_setup(root_node)

    # return root_node.load()
    obj = root_node.load()

    # s = {str(k): v for k, v in sorted(LDrawNode.geometry_datas2.items(), key=lambda ele: ele[1], reverse=True)}
    # helpers.write_json("gs2.json", s, indent=4)

    if ImportOptions.meta_step:
        if ImportOptions.set_end_frame:
            bpy.context.scene.frame_end = ldraw_meta.current_frame + ImportOptions.frames_per_step
            bpy.context.scene.frame_set(bpy.context.scene.frame_end)

    max_clip_end = 0
    for camera in ldraw_meta.cameras:
        camera = blender_camera.create_camera(camera, empty=ldraw_object.top_empty, collection=group.top_collection)
        if bpy.context.scene.camera is None:
            if camera.data.clip_end > max_clip_end:
                max_clip_end = camera.data.clip_end
            bpy.context.scene.camera = camera

    for area in bpy.context.screen.areas:
        if area.type == "VIEW_3D":
            for space in area.spaces:
                # space.shading.show_backface_culling = False
                if space.type == "VIEW_3D":
                    if space.clip_end < max_clip_end:
                        space.clip_end = max_clip_end

    return obj


def __scene_setup():
    bpy.context.scene.eevee.use_ssr = True
    bpy.context.scene.eevee.use_ssr_refraction = True
    bpy.context.scene.eevee.use_taa_reprojection = True

    # view vertex colors in solid view
    for window in bpy.context.window_manager.windows:
        for area in window.screen.areas:
            if area.type == 'VIEW_3D':
                for space in area.spaces:
                    if space.type == 'VIEW_3D':
                        if ImportOptions.meta_bfc:
                            space.shading.show_backface_culling = True
                        space.shading.type = 'SOLID'
                        # Shading > Color > Object to see object colors
                        space.shading.color_type = 'VERTEX'
                        # space.shading.color_type = 'MATERIAL'
                        # space.shading.color_type = 'OBJECT'

    # https://blender.stackexchange.com/a/146838
    # TODO: use line art modifier with grease pencil object
    #  parts can't be in more than one group if those group's parent is targeted by the modifier
    #  groups and ungroup collections can't be under model.ldr collection or else the lines don't render
    #  studs, and maybe other intersecting geometry, may have broken lines
    #  checking "overlapping edges as contour" helps, applying edge split, scale, marking freestyle edge does not seem to make a difference
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
    ImportOptions.meta_group = False
    ImportOptions.parent_to_empty = False
    ImportOptions.make_gaps = False

    # slope texture demonstration
    obj = do_import('3044.dat')
    if obj is not None:
        obj.location.x = 0.0
        obj.location.y = 5.0
        obj.location.z = 0.5

    # texmap demonstration
    obj = do_import('27062p01.dat')
    if obj is not None:
        obj.location.x = 3
        obj.location.y = 5

    # cloth demonstration
    obj = do_import('50231.dat')
    if obj is not None:
        obj.location.x = 6
        obj.location.y = 5

    colors = {}
    group_name = 'blank'
    for line in file.lines:
        clean_line = helpers.clean_line(line)
        strip_line = line.strip()

        if clean_line.startswith('0 // LDraw'):
            group_name = clean_line
            colors[group_name] = []
            continue

        if clean_line.startswith("0 !COLOUR "):
            colors[group_name].append(LDrawColor.parse_color(clean_line))
            continue

    j = 0
    for collection_name, codes in colors.items():
        scene_collection = group.get_scene_collection()
        collection = group.get_collection(collection_name, scene_collection)

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

            material = BlenderMaterials.get_material(color_code, easy_key=True)

            # https://blender.stackexchange.com/questions/23905/select-faces-depending-on-material
            if material.name not in mesh.materials:
                mesh.materials.append(material)
            for face in bm.faces:
                face.material_index = mesh.materials.find(material.name)

            helpers.finish_bmesh(bm, mesh)
            helpers.finish_mesh(mesh)

            obj = bpy.data.objects.new(mesh.name, mesh)
            obj[strings.ldraw_filename_key] = file.name
            obj[strings.ldraw_color_code_key] = color_code

            obj.modifiers.new("Subdivision", type='SUBSURF')
            obj.location.x = i * 3
            obj.location.y = -j * 3

            color = LDrawColor.get_color(color_code)
            obj.color = color.linear_color_a

            group.link_obj(collection, obj)
        j += 1
