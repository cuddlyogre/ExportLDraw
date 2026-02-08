import bpy
import bmesh
import mathutils

from .blender_materials import BlenderMaterials
from .import_options import ImportOptions
from . import special_bricks
from . import strings
from . import helpers
from . import matrices


def _create_mesh(key):
    return bpy.data.meshes.new(key)


def create_mesh(key, geometry_data, color_code, return_mesh=False):
    mesh = bpy.data.meshes.get(key)
    if mesh is None or return_mesh:
        if mesh is None:
            mesh = _create_mesh(key)
        mesh.name = key
        mesh[strings.ldraw_filename_key] = geometry_data.file.name

        __process_bmesh(mesh, geometry_data, color_code)
        __process_mesh_sharp_edges(mesh, geometry_data)
        __process_mesh(mesh)

        mesh.transform(matrices.rotation_matrix)

    return mesh


# for edge_data in geometry_data.line_data:
# for vertex in edge_data.vertices[0:2]:  # in case line_data is being used since it has 4 verts
def create_edge_mesh(key, geometry_data):
    mesh = bpy.data.meshes.get(key)
    if mesh is None:
        e_verts = []
        e_edges = []
        e_faces = []

        i = 0
        for edge_data in geometry_data.edge_data:
            face_indices = []
            for vertex in edge_data.vertices:
                e_verts.append(vertex)
                face_indices.append(i)
                i += 1
            e_faces.append(face_indices)

        mesh = bpy.data.meshes.new(key)
        mesh.name = key
        mesh[strings.ldraw_filename_key] = geometry_data.file.name

        mesh.from_pydata(e_verts, e_edges, e_faces)
        helpers.finish_mesh(mesh)
        __scale_mesh(mesh)

        mesh.transform(matrices.rotation_matrix)

    return mesh


# https://b3d.interplanety.org/en/how-to-get-global-vertex-coordinates/
# https://blender.stackexchange.com/questions/50160/scripting-low-level-join-meshes-elements-hopefully-with-bmesh
# https://blender.stackexchange.com/questions/188039/how-to-join-only-two-objects-to-create-a-new-object-using-python
# https://blender.stackexchange.com/questions/23905/select-faces-depending-on-material
def __process_bmesh(mesh, geometry_data, color_code):
    bm = __process_bmesh_faces(mesh, geometry_data, color_code)
    helpers.ensure_bmesh(bm)
    __clean_bmesh(bm)
    __process_bmesh_edges(bm, geometry_data)
    helpers.finish_bmesh(bm, mesh)
    helpers.finish_mesh(mesh)


def __build_kd_tree(verts):
    kd = mathutils.kdtree.KDTree(len(verts))
    for i, v in enumerate(verts):
        kd.insert(v.co, i)
    kd.balance()
    return kd


def __get_edges(kd, edge_data, distance):
    edges0 = [index for (co, index, dist) in kd.find_range(edge_data.vertices[0], distance)]
    edges1 = [index for (co, index, dist) in kd.find_range(edge_data.vertices[1], distance)]
    return edges0, edges1


# bpy.context.object.data.edges[6].use_edge_sharp = True
# Create kd tree for fast "find nearest points" calculation
# https://docs.blender.org/api/blender_python_api_current/mathutils.kdtree.html
# https://docs.scipy.org/doc/scipy/reference/generated/scipy.spatial.KDTree.html
def __get_edge_indices(verts, geometry_data):
    edge_indices = set()
    if len(geometry_data.edge_data) < 1: return edge_indices

    kd = __build_kd_tree(verts)

    # increase the distance to look for edges to merge
    # merge line type 2 edges at a greater distance than mesh edges
    # the rounded part in the seat of 4079.dat has a gap just wide
    # enough that 2x isn't enough
    distance = ImportOptions.merge_distance
    distance = ImportOptions.merge_distance * 2.1

    for edge_data in geometry_data.edge_data:
        edges0, edges1 = __get_edges(kd, edge_data, distance)
        for e0 in edges0:
            for e1 in edges1:
                edge_indices.add((e0, e1))
                edge_indices.add((e1, e0))

    return edge_indices


def __process_bmesh_edges(bm, geometry_data):
    if ImportOptions.smooth_type_value() == "bmesh_split":
        edge_indices = __get_edge_indices(bm.verts, geometry_data)

        # Find the appropriate mesh edges and make them sharp (i.e. not smooth)
        edges = set()
        # merge = set()
        for edge in bm.edges:
            v0 = edge.verts[0]
            v1 = edge.verts[1]
            i0 = v0.index
            i1 = v1.index
            if (i0, i1) in edge_indices:
                edges.add(edge)

        bmesh.ops.split_edges(bm, edges=list(edges))


def __process_bmesh_faces(mesh, geometry_data, color_code):
    bm = bmesh.new()

    for face_data in geometry_data.face_data:
        verts = [bm.verts.new(vertex) for vertex in face_data.vertices]
        face = bm.faces.new(verts)

        color_code = helpers.determine_color(color_code, face_data.color_code)

        part_slopes = special_bricks.get_part_slopes(geometry_data.file.name)
        material = BlenderMaterials.get_material(
            color_code=color_code,
            bfc_certified=geometry_data.bfc_certified,
            part_slopes=part_slopes,
            texmap=face_data.texmap,
            pe_texmaps=face_data.pe_texmaps,
        )

        material_index = mesh.materials.find(material.name)
        if material_index == -1:
            # mesh.materials.append(None) #add blank slot
            mesh.materials.append(material)
            material_index = mesh.materials.find(material.name)

        face.material_index = material_index
        face.smooth = ImportOptions.shade_smooth

        if face_data.texmap is not None:
            face_data.texmap.uv_unwrap_face(bm, face)

        for pe_texmap in face_data.pe_texmaps:
            pe_texmap.uv_unwrap_face(bm, face)

    return bm


def __clean_bmesh(bm):
    if ImportOptions.remove_doubles:
        bmesh.ops.remove_doubles(bm, verts=bm.verts[:], dist=ImportOptions.merge_distance)

    # recalculate_normals completely overwrites any bfc processing
    if ImportOptions.recalculate_normals:
        bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])


def __process_mesh_sharp_edges(mesh, geometry_data):
    if ImportOptions.smooth_type_value() == "edge_split" or ImportOptions.use_freestyle_edges or ImportOptions.bevel_edges:
        # If we need bevel edges, get a reference to the attribute data
        # so we can assign bevel weights by index.
        bevel_attr_data = __ensure_bevel_weight(mesh)

        # Build lists of flags/values in one pass
        sharp_flags = []
        freestyle_flags = [] if bpy.app.version < (4, 3) else None
        bevel_weights = [] if bpy.app.version < (4, 3) else None
        attr_weights = [] if bevel_attr_data else None

        __process_edges(mesh, geometry_data, sharp_flags, freestyle_flags, bevel_weights, attr_weights)
        __set_edge_foreach_set(mesh, sharp_flags, freestyle_flags, bevel_weights, attr_weights, bevel_attr_data)


def __ensure_bevel_weight(mesh):
    bevel_attr_data = None
    if bpy.app.version < (4, 3):
        pass
    else:
        if "bevel_weight_edge" not in mesh.attributes:
            mesh.attributes.new(name="bevel_weight_edge", type='FLOAT', domain='EDGE')
        bevel_attr_data = mesh.attributes["bevel_weight_edge"]
    return bevel_attr_data


def __process_edges(mesh, geometry_data, sharp_flags, freestyle_flags, bevel_weights, attr_weights):
    edge_indices = __get_edge_indices(mesh.vertices, geometry_data)
    for edge in mesh.edges:
        __process_edge(edge, edge_indices, sharp_flags, freestyle_flags, bevel_weights, attr_weights)


def __is_special(edge, edge_indices):
    v0, v1 = edge.vertices[0], edge.vertices[1]
    is_special = (v0, v1) in edge_indices
    return is_special


def __process_edge(edge, edge_indices, sharp_flags, freestyle_flags, bevel_weights, attr_weights):
    is_special = __is_special(edge, edge_indices)

    if ImportOptions.smooth_type_value() == "edge_split":
        sharp_flags.append(is_special)

    if ImportOptions.use_freestyle_edges:
        if freestyle_flags:
            freestyle_flags.append(is_special)

    if ImportOptions.bevel_edges:
        weight = ImportOptions.bevel_weight if is_special else 0.0
        if bevel_weights:
            bevel_weights.append(weight)
        elif attr_weights:
            attr_weights.append(weight)


# Bulk set the properties
def __set_edge_foreach_set(mesh, sharp_flags, freestyle_flags, bevel_weights, attr_weights, bevel_attr_data):
    if sharp_flags:
        mesh.edges.foreach_set("use_edge_sharp", sharp_flags)
    if freestyle_flags:
        mesh.edges.foreach_set("use_freestyle_mark", freestyle_flags)
    if bevel_weights:
        mesh.edges.foreach_set("bevel_weight", bevel_weights)
    if attr_weights:
        bevel_attr_data.data.foreach_set("value", attr_weights)


def __process_mesh(mesh):
    if bpy.app.version < (4, 1):
        if ImportOptions.smooth_type_value() == "auto_smooth" or ImportOptions.smooth_type_value() == "bmesh_split":
            mesh.use_auto_smooth = ImportOptions.shade_smooth
            mesh.auto_smooth_angle = matrices.auto_smooth_angle
    # scale here so edges can be marked sharp
    __scale_mesh(mesh)


def __scale_mesh(mesh):
    if ImportOptions.scale_strategy_value() == "mesh":
        aa = matrices.import_scale_matrix
        mesh.transform(aa)
