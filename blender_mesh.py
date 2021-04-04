import bpy
import math
import mathutils
import bmesh

from . import strings
from . import options
from . import matrices

from . import blender_materials
from . import ldraw_colors
from . import special_bricks


def get_mesh(key, filename, geometry):
    if key not in bpy.data.meshes:
        # TOOO: return list of polygon data with faceinfo so that create_mesh, apply_materials, bmesh_ops, and apply_slope_materials can be combined
        mesh = create_mesh(key, geometry)

        # apply materials to mesh
        # then mesh cleanup
        # then apply slope materials
        # this order is important because bmesh_ops causes
        # mesh.polygons to get out of sync geometry.face_info
        # which causes materials and slope materials to be applied incorrectly
        apply_materials(mesh, geometry)
        bmesh_ops(mesh, geometry)
        apply_slope_materials(mesh, filename)

        if options.smooth_type == "auto_smooth":
            mesh.use_auto_smooth = options.shade_smooth
            auto_smooth_angle = 89.9  # 1.56905 - 89.9 so 90 degrees and up are affected
            auto_smooth_angle = 51.1
            mesh.auto_smooth_angle = math.radians(auto_smooth_angle)

        if options.make_gaps and options.gap_target == "mesh":
            mesh.transform(matrices.scaled_matrix(options.gap_scale))

        mesh[strings.ldraw_filename_key] = filename
        mesh.validate()
        mesh.update(calc_edges=True)
    mesh = bpy.data.meshes[key]
    return mesh


def create_mesh(key, geometry):
    return do_create_mesh(key, geometry.vertices, geometry.vert_counts)


# https://youtu.be/cQ0qtcSymDI?t=356
# https://www.youtube.com/watch?v=cQ0qtcSymDI&t=0s
# https://www.blenderguru.com/articles/cycles-input-encyclopedia
# https://blenderscripting.blogspot.com/2011/05/blender-25-python-moving-object-origin.html
# https://blenderartists.org/t/how-to-set-origin-to-center/687111
# https://blenderartists.org/t/modifying-object-origin-with-python/507305/3
# https://blender.stackexchange.com/questions/414/how-to-use-bmesh-to-add-verts-faces-and-edges-to-existing-geometry
# https://devtalk.blender.org/t/bmesh-adding-new-verts/11108/2
# f1 = Vector((rand(-5, 5),rand(-5, 5),rand(-5, 5)))
# f2 = Vector((rand(-5, 5),rand(-5, 5),rand(-5, 5)))
# f3 = Vector((rand(-5, 5),rand(-5, 5),rand(-5, 5)))
# f = [f1, f2, f3]
# for f in enumerate(faces):
#     this_vert = bm.verts.new(f)
# used_indexes = list(indexes.values())
# bigger = []
# smaller = []
# remaining = (collections.Counter(bigger) - collections.Counter(smaller)).elements()
# unused_indexes = list(remaining)
# print(list(indexes.values()))
# print(len(used_vertices))
# if index is not referenced in vertices. remove from vertices
def do_create_mesh(key, geometry_vertices, geometry_vert_counts):
    if not options.remove_doubles or options.remove_doubles_strategy == "bmesh_ops":
        vertices, edges, faces = easy_get_mesh_data(geometry_vertices, geometry_vert_counts)
    else:
        vertices, edges, faces = hard_get_mesh_data(geometry_vertices, geometry_vert_counts)

    mesh = bpy.data.meshes.new(key)
    mesh.from_pydata(vertices, edges, faces)

    if options.bevel_edges:
        mesh.use_customdata_edge_bevel = True

    return mesh


# TODO: add index handling from hard_do_create_mesh
def easy_get_mesh_data(geometry_vertices, geometry_vert_counts):
    vertices = []
    edges = []
    faces = []

    # makes indexes sequential
    face_index = 0
    for f in geometry_vert_counts:
        new_face = []
        for _ in range(f):
            new_face.append(face_index)
            face_index += 1
        faces.append(new_face)

    vertices = [v.to_tuple() for v in geometry_vertices]

    return vertices, edges, faces


# apply_materials
# len(geometry_vert_counts) always matches len(faces)
# len(faces) do not always match len(mesh.polygons)
# print(len(geometry_vert_counts))
# print(len(faces))
# print(len(mesh.polygons))
# if you validate here, the polygon count changes,
# which causes polygon count and geometry.face_info count to get out of sync, causing missing face colors
# mesh.validate()
# mesh.update(calc_edges=True)
# print(len(mesh.polygons))
# slower than bmesh.ops.remove_doubles but necessary if importing to a system without a remove doubles function
def hard_get_mesh_data(geometry_vertices, geometry_vert_counts):
    vertices = []
    edges = []
    faces = []

    # https://docs.blender.org/api/blender_python_api_current/mathutils.kdtree.html
    # Create kd tree for fast "find nearest points" calculation
    # kd = mathutils.kdtree.KDTree(len(geometry_vertices))
    # for i, v in enumerate(geometry_vertices):
    #     kd.insert(v.co, i)
    # kd.balance()

    # kd.find_range(geometry.edge_vertices[i + 0], options.merge_distance)
    # kd.find(geometry.edge_vertices[i + 0], options.merge_distance)

    # determine indexes to prevent doubles
    face_index = 0
    indexes = {}
    for vert_count in geometry_vert_counts:
        new_face = []
        for _ in range(vert_count):
            v = geometry_vertices[face_index]
            r = 1
            vv = mathutils.Vector((round(v.x, r), round(v.y, r), round(v.z, r)))
            vv = v
            if vv not in vertices:
                vertices.append(vv)

            k = ",".join([str(vv.x), str(vv.y), str(vv.z)])
            k = str(vv[:])
            if k not in indexes:
                indexes[k] = vertices.index(vv)
            index = indexes[k]
            new_face.append(index)

            face_index += 1

        faces.append(new_face)

    vertices = [v.to_tuple() for v in vertices]

    return vertices, edges, faces


# https://blender.stackexchange.com/a/91687
# for f in bm.faces:
#     f.smooth = True
# mesh = context.object.data
# for f in mesh.polygons:
#     f.use_smooth = True
# values = [True] * len(mesh.polygons)
# mesh.polygons.foreach_set("use_smooth", values)
# bpy.context.object.active_material.use_backface_culling = True
# bpy.context.object.active_material.use_screen_refraction = True
def apply_materials(mesh, geometry):
    for i, polygon in enumerate(mesh.polygons):
        face_info = geometry.face_info[i]

        color_code = face_info.color_code
        color = ldraw_colors.get_color(color_code)
        use_edge_color = face_info.use_edge_color
        texmap = face_info.texmap
        material = blender_materials.get_material(color, use_edge_color=use_edge_color, texmap=texmap)
        if material is None:
            continue

        # TODO: UV PROJECT HERE

        if material.name not in mesh.materials:
            mesh.materials.append(material)
        polygon.material_index = mesh.materials.find(material.name)
        polygon.use_smooth = options.shade_smooth


def bmesh_ops(mesh, geometry):
    bm = bmesh.new()
    bm.from_mesh(mesh)
    bm.faces.ensure_lookup_table()
    bm.verts.ensure_lookup_table()
    bm.edges.ensure_lookup_table()

    if options.remove_doubles and options.remove_doubles_strategy == "bmesh_ops":
        bmesh.ops.remove_doubles(bm, verts=bm.verts[:], dist=options.merge_distance)

    if options.recalculate_normals:
        bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])

    handle_edges(bm, geometry)

    bm.to_mesh(mesh)
    bm.clear()
    bm.free()


def apply_slope_materials(mesh, filename):
    if not special_bricks.is_slope_part(filename):
        return

    if len(mesh.materials) < 1:
        return

    for polygon in mesh.polygons:
        face_material = mesh.materials[polygon.material_index]

        if strings.ldraw_color_code_key not in face_material:
            continue

        color_code = str(face_material[strings.ldraw_color_code_key])
        color = ldraw_colors.get_color(color_code)

        is_slope_material = special_bricks.is_slope_face(filename, polygon)
        material = blender_materials.get_material(color, is_slope_material=is_slope_material)
        if material is None:
            continue

        if material.name not in mesh.materials:
            mesh.materials.append(material)
        polygon.material_index = mesh.materials.find(material.name)


def handle_edges(bm, geometry):
    # Create kd tree for fast "find nearest points" calculation
    kd = mathutils.kdtree.KDTree(len(bm.verts))
    for i, v in enumerate(bm.verts):
        kd.insert(v.co, i)
    kd.balance()

    # Create edge_indices dictionary, which is the list of edges as pairs of indices into our verts array
    edge_indices = {}
    for i in range(0, len(geometry.edge_vertices), 2):
        edges0 = [index for (co, index, dist) in kd.find_range(geometry.edge_vertices[i + 0], options.merge_distance)]
        edges1 = [index for (co, index, dist) in kd.find_range(geometry.edge_vertices[i + 1], options.merge_distance)]
        for e0 in edges0:
            for e1 in edges1:
                edge_indices[(e0, e1)] = True
                edge_indices[(e1, e0)] = True

    # Find layer for bevel weights
    bevel_weight_layer = None
    if options.bevel_edges:
        if 'BevelWeight' in bm.edges.layers.bevel_weight:
            bevel_weight_layer = bm.edges.layers.bevel_weight["BevelWeight"]

    # Find the appropriate mesh edges and make them sharp (i.e. not smooth)
    for edge_vertex in bm.edges:
        v0 = edge_vertex.verts[0].index
        v1 = edge_vertex.verts[1].index
        if (v0, v1) in edge_indices:
            # Make edge sharp
            edge_vertex.smooth = False

            # Add bevel weight
            if bevel_weight_layer is not None:
                bevel_wight = 1.0
                edge_vertex[bevel_weight_layer] = bevel_wight


def get_edge_mesh(key, filename, geometry):
    e_key = f"e_{key}"
    if e_key not in bpy.data.meshes:
        edge_mesh = create_edge_mesh(e_key, geometry)
        edge_mesh[strings.ldraw_edge_key] = filename
        if options.make_gaps and options.gap_target == "mesh":
            edge_mesh.transform(matrices.scaled_matrix(options.gap_scale))
    edge_mesh = bpy.data.meshes[e_key]
    return edge_mesh


def create_edge_mesh(key, geometry):
    return do_create_mesh(key, geometry.edge_vertices, geometry.edge_vert_counts)


def get_gp_mesh(key, mesh):
    gp_key = f"gp_{key}"
    if gp_key not in bpy.data.grease_pencils:
        gp_mesh = bpy.data.grease_pencils.new(gp_key)

        gp_mesh.pixel_factor = 5.0
        gp_mesh.stroke_depth_order = "3D"

        gp_layer = gp_mesh.layers.new("gpl")
        gp_frame = gp_layer.frames.new(1)
        gp_layer.active_frame = gp_frame

        for e in mesh.edge_vert_counts:
            gp_stroke = gp_frame.strokes.new()
            gp_stroke.material_index = 0
            gp_stroke.line_width = 10.0
            for v in e.vertices:
                i = len(gp_stroke.points)
                gp_stroke.points.add(1)
                gp_point = gp_stroke.points[i]
                gp_point.co = mesh.vertices[v].co

        apply_gp_materials(gp_mesh)
    gp_mesh = bpy.data.grease_pencils[gp_key]
    return gp_mesh


# https://blender.stackexchange.com/a/166492
def apply_gp_materials(gp_mesh):
    color_code = "0"
    color = ldraw_colors.get_color(color_code)

    use_edge_color = True
    base_material = blender_materials.get_material(color, use_edge_color=use_edge_color)
    if base_material is None:
        return

    material_name = f"gp_{base_material.name}"
    if material_name not in bpy.data.materials:
        material = base_material.copy()
        material.name = material_name
        bpy.data.materials.create_gpencil_data(material)  # https://developer.blender.org/T67102
    material = bpy.data.materials[material_name]
    gp_mesh.materials.append(material)
