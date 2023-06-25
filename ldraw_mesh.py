import bpy
import bmesh
import mathutils

from . import special_bricks
from . import strings
from .blender_materials import BlenderMaterials
from .import_options import ImportOptions
from . import helpers
from . import matrices


def get_mesh(key):
    return bpy.data.meshes.get(key)


def create_mesh(ldraw_node, key, geometry_data):
    mesh = get_mesh(key)
    if mesh is None:
        mesh = bpy.data.meshes.new(key)
        mesh.name = key
        mesh[strings.ldraw_filename_key] = ldraw_node.file.name

        __process_bmesh(ldraw_node, mesh, geometry_data)
        __process_mesh_edges(ldraw_node, key, geometry_data)
        __process_mesh_sharp_edges(mesh, geometry_data)
        __process_mesh(mesh)

    return mesh


# https://b3d.interplanety.org/en/how-to-get-global-vertex-coordinates/
# https://blender.stackexchange.com/questions/50160/scripting-low-level-join-meshes-elements-hopefully-with-bmesh
# https://blender.stackexchange.com/questions/188039/how-to-join-only-two-objects-to-create-a-new-object-using-python
# https://blender.stackexchange.com/questions/23905/select-faces-depending-on-material
def __process_bmesh(ldraw_node, mesh, geometry_data):
    bm = __process_bmesh_faces(ldraw_node, geometry_data, mesh)
    helpers.ensure_bmesh(bm)
    __clean_bmesh(bm)
    __process_bmesh_edges(bm, geometry_data)
    helpers.finish_bmesh(bm, mesh)
    helpers.finish_mesh(mesh)


# bpy.context.object.data.edges[6].use_edge_sharp = True
# Create kd tree for fast "find nearest points" calculation
# https://docs.blender.org/api/blender_python_api_current/mathutils.kdtree.html
# https://docs.scipy.org/doc/scipy/reference/generated/scipy.spatial.KDTree.html
def __get_edge_indices(verts, geometry_data):
    kd = mathutils.kdtree.KDTree(len(verts))
    for i, v in enumerate(verts):
        kd.insert(v.co, i)
    kd.balance()

    # increase the distance to look for edges to merge
    # merge line type 2 edges at a greater distance than mesh edges
    # the rounded part in the seat of 4079.dat has a gap just wide
    # enough that 2x isn't enough
    distance = ImportOptions.merge_distance
    distance = ImportOptions.merge_distance * 2.1

    edge_indices = set()

    for edge_data in geometry_data.edge_data:
        edge_verts = []
        # for vertex in edge_data.vertices[0:2]:  # in case line_data is being used since it has 4 verts
        for vertex in edge_data.vertices:
            edge_verts.append(vertex)

        edges0 = [index for (co, index, dist) in kd.find_range(edge_verts[0], distance)]
        edges1 = [index for (co, index, dist) in kd.find_range(edge_verts[1], distance)]
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


def __process_bmesh_faces(ldraw_node, geometry_data, mesh):
    bm = bmesh.new()

    for face_data in geometry_data.face_data:
        verts = [bm.verts.new(vertex) for vertex in face_data.vertices]
        face = bm.faces.new(verts)

        part_slopes = special_bricks.get_part_slopes(ldraw_node.file.name)
        parts_cloth = special_bricks.get_parts_cloth(ldraw_node.file.name)
        material = BlenderMaterials.get_material(
            color_code=face_data.color_code,
            part_slopes=part_slopes,
            parts_cloth=parts_cloth,
            texmap=face_data.texmap,
            pe_texmap=face_data.pe_texmap,
            use_backface_culling=ldraw_node.bfc_certified
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

        if face_data.pe_texmap is not None:
            face_data.pe_texmap.uv_unwrap_face(bm, face)

    return bm


def __clean_bmesh(bm):
    if ImportOptions.remove_doubles:
        bmesh.ops.remove_doubles(bm, verts=bm.verts[:], dist=ImportOptions.merge_distance)

    # recalculate_normals completely overwrites any bfc processing
    if ImportOptions.recalculate_normals:
        bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])


# for edge_data in geometry_data.line_data:
# for vertex in edge_data.vertices[0:2]:  # in case line_data is being used since it has 4 verts
def __process_mesh_edges(ldraw_node, key, geometry_data):
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

    __create_edge_mesh(ldraw_node, key, e_edges, e_faces, e_verts)


def __process_mesh_sharp_edges(mesh, geometry_data):
    if ImportOptions.smooth_type_value() == "edge_split" or ImportOptions.use_freestyle_edges or ImportOptions.bevel_edges:
        edge_indices = __get_edge_indices(mesh.vertices, geometry_data)

        for edge in mesh.edges:
            v0 = edge.vertices[0]
            v1 = edge.vertices[1]
            if (v0, v1) in edge_indices:
                if ImportOptions.smooth_type_value() == "edge_split":
                    edge.use_edge_sharp = True
                if ImportOptions.use_freestyle_edges:
                    edge.use_freestyle_mark = True
                if ImportOptions.bevel_edges:
                    edge.bevel_weight = ImportOptions.bevel_weight


def __process_mesh(mesh):
    if ImportOptions.smooth_type_value() == "auto_smooth" or ImportOptions.smooth_type_value() == "bmesh_split":
        mesh.use_auto_smooth = ImportOptions.shade_smooth
        mesh.auto_smooth_angle = matrices.auto_smooth_angle

    if ImportOptions.make_gaps and ImportOptions.gap_target_value() == "mesh":
        mesh.transform(matrices.gap_scale_matrix)


def __create_edge_mesh(ldraw_node, key, e_edges, e_faces, e_verts):
    if ImportOptions.import_edges:
        edge_key = f"e_{key}"
        edge_mesh = bpy.data.meshes.new(edge_key)
        edge_mesh.name = edge_key
        edge_mesh[strings.ldraw_filename_key] = ldraw_node.file.name

        edge_mesh.from_pydata(e_verts, e_edges, e_faces)
        helpers.finish_mesh(edge_mesh)

        if ImportOptions.make_gaps and ImportOptions.gap_target_value() == "mesh":
            edge_mesh.transform(matrices.gap_scale_matrix)
