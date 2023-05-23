import bpy

from . import group
from . import strings
from .import_options import ImportOptions
from .ldraw_colors import LDrawColor
from . import ldraw_props
from . import ldraw_meta
from . import ldraw_mesh
from . import matrices

top_empty = None
gap_scale_empty = None


def reset_caches():
    global top_empty
    global gap_scale_empty

    top_empty = None
    gap_scale_empty = None


# TODO: to add rigid body - must apply scale and cannot be parented to empty
def process_top_object(ldraw_node, mesh, key, accum_matrix, color_code, collection):
    obj = __get_top_object(ldraw_node, mesh, color_code)
    __process_top_object_matrix(obj, accum_matrix)
    __process_top_object_gap(obj, accum_matrix)
    __process_top_object_edges(obj)
    ldraw_meta.do_meta_step(obj)
    __link_obj_to_collection(collection, obj)
    ldraw_props.set_props(obj, ldraw_node.file, color_code)
    __process_top_edges(ldraw_node, key, obj, color_code, collection)

    return obj


def __get_top_object(ldraw_node, mesh, color_code):
    obj = bpy.data.objects.new(mesh.name, mesh)
    obj[strings.ldraw_filename_key] = ldraw_node.file.name
    obj[strings.ldraw_color_code_key] = color_code

    # bpy.context.space_data.shading.color_type = 'MATERIAL'
    # bpy.context.space_data.shading.color_type = 'OBJECT'
    # Shading > Color > Object to see object colors
    color = LDrawColor.get_color(color_code)
    obj.color = color.color_a
    return obj


def __process_top_object_matrix(obj, accum_matrix):
    if ImportOptions.parent_to_empty:
        global top_empty
        if top_empty is None:
            top_empty = bpy.data.objects.new(group.top_collection.name, None)
            group.link_obj(group.top_collection, top_empty)

        top_empty.matrix_world = matrices.transform_matrix
        obj.matrix_world = accum_matrix
        obj.parent = top_empty  # must be after matrix_world set or else transform is incorrect
    else:
        matrix_world = matrices.transform_matrix @ accum_matrix
        obj.matrix_world = matrix_world


def __process_top_object_gap(obj, accum_matrix):
    if ImportOptions.preserve_hierarchy:
        return

    if ImportOptions.make_gaps and ImportOptions.gap_target == "object":
        if ImportOptions.gap_scale_strategy == "object":
            matrix_world = matrices.transform_matrix @ accum_matrix @ matrices.gap_scale_matrix
            obj.matrix_world = matrix_world
        elif ImportOptions.gap_scale_strategy == "constraint":
            global gap_scale_empty
            if gap_scale_empty is None:
                gap_scale_empty = bpy.data.objects.new("gap_scale", None)
                gap_scale_empty.use_fake_user = True
                if ImportOptions.parent_to_empty:
                    matrix_world = matrices.gap_scale_matrix
                    gap_scale_empty.matrix_world = matrix_world
                    gap_scale_empty.parent = top_empty
                else:
                    matrix_world = matrices.transform_matrix @ matrices.gap_scale_matrix
                    gap_scale_empty.matrix_world = matrix_world
                group.link_obj(group.top_collection, gap_scale_empty)
            copy_scale_constraint = obj.constraints.new("COPY_SCALE")
            copy_scale_constraint.target = gap_scale_empty


def __process_top_object_edges(obj):
    if ImportOptions.smooth_type == "edge_split":
        edge_modifier = obj.modifiers.new("Edge Split", type='EDGE_SPLIT')
        edge_modifier.use_edge_sharp = True
        # need this or else items like the back blue window stripes in 10252-1 - Volkswagen Beetle.mpd aren't shaded properly
        edge_modifier.use_edge_angle = True
        edge_modifier.split_angle = matrices.auto_smooth_angle


def __process_top_edges(ldraw_node, key, obj, color_code, collection):
    if ImportOptions.import_edges:
        edge_key = f"e_{key}"
        edge_mesh = ldraw_mesh.get_mesh(edge_key)
        edge_obj = bpy.data.objects.new(edge_mesh.name, edge_mesh)
        edge_obj[strings.ldraw_filename_key] = f"{ldraw_node.file.name}_edges"
        edge_obj[strings.ldraw_color_code_key] = color_code

        color = LDrawColor.get_color(color_code)
        edge_obj.color = color.edge_color_d

        ldraw_meta.do_meta_step(edge_obj)

        __link_obj_to_collection(collection, edge_obj)

        edge_obj.parent = obj
        edge_obj.matrix_world = obj.matrix_world


def __link_obj_to_collection(_collection, obj):
    group.link_obj(_collection, obj)

    if group.current_step_group is not None:
        group.link_obj(group.current_step_group, obj)

    if ImportOptions.meta_group:
        if group.next_collection is not None:
            group.link_obj(group.next_collection, obj)
        else:
            group.link_obj(group.ungrouped_collection, obj)
