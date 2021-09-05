import math
import os
import uuid
import re

import bmesh
import bpy
import mathutils

from . import blender_materials
from . import import_options
from . import ldraw_colors
from . import matrices
from . import special_bricks
from . import strings
from .geometry_data import GeometryData
from . import texmap

part_count = 0
current_step = 0
current_frame = 0
geometry_data_cache = {}
top_collection = None
top_empty = None
gap_scale_empty = None
collection_id_map = {}
next_collection = None
end_next_collection = False
key_map = {}


def reset_caches():
    global part_count
    global current_step
    global current_frame
    global geometry_data_cache
    global top_collection
    global top_empty
    global gap_scale_empty
    global collection_id_map
    global next_collection
    global end_next_collection
    global key_map

    part_count = 0
    current_step = 0
    current_frame = 0
    geometry_data_cache = {}
    top_collection = None
    top_empty = None
    gap_scale_empty = None
    collection_id_map = {}
    next_collection = None
    end_next_collection = False
    key_map = {}

    if import_options.meta_step:
        set_step()


def set_step():
    global current_step
    global current_frame

    first_frame = (import_options.starting_step_frame + import_options.frames_per_step)
    current_step_frame = (import_options.frames_per_step * current_step)
    current_frame = first_frame + current_step_frame
    current_step += 1
    if import_options.set_timelime_markers:
        bpy.context.scene.timeline_markers.new("STEP", frame=current_frame)


def create_meta_group(collection_name, parent_collection):
    if collection_name not in bpy.data.collections:
        bpy.data.collections.new(collection_name)
    collection = bpy.data.collections[collection_name]
    if parent_collection is None:
        parent_collection = bpy.context.scene.collection
    if collection.name not in parent_collection.children:
        parent_collection.children.link(collection)
    return collection


# obj.show_name = True
def do_create_object(mesh):
    if import_options.instancing:
        if mesh.name not in bpy.data.objects:
            bpy.data.objects.new(mesh.name, mesh)
        instanced_obj = bpy.data.objects[mesh.name]

        collection_name = 'Parts'
        if collection_name not in bpy.data.collections:
            parts_collection = bpy.data.collections.new(collection_name)
            bpy.context.scene.collection.children.link(parts_collection)
            parts_collection.hide_viewport = True
            parts_collection.hide_render = True
        parts_collection = bpy.data.collections[collection_name]

        collection_name = mesh.name
        if collection_name not in bpy.data.collections:
            part_collection = bpy.data.collections.new(collection_name)
            parts_collection.children.link(part_collection)
        part_collection = bpy.data.collections[collection_name]

        if instanced_obj.name not in part_collection.objects:
            part_collection.objects.link(instanced_obj)

        obj = bpy.data.objects.new(mesh.name, None)
        obj.instance_type = 'COLLECTION'
        obj.instance_collection = part_collection
    else:
        obj = bpy.data.objects.new(mesh.name, mesh)
    return obj


def process_object(obj, matrix):
    if top_empty is None:
        set_object_matrix(obj, matrix)
    else:
        set_parented_object_matrix(obj, matrix)

    if import_options.meta_step:
        handle_meta_step(obj)


# https://docs.blender.org/api/current/bpy.types.bpy_struct.html#bpy.types.bpy_struct.keyframe_insert
# https://docs.blender.org/api/current/bpy.types.Scene.html?highlight=frame_set#bpy.types.Scene.frame_set
# https://docs.blender.org/api/current/bpy.types.Object.html?highlight=rotation_quaternion#bpy.types.Object.rotation_quaternion
def handle_meta_step(obj):
    bpy.context.scene.frame_set(import_options.starting_step_frame)
    obj.hide_viewport = True
    obj.hide_render = True
    obj.keyframe_insert(data_path="hide_render")
    obj.keyframe_insert(data_path="hide_viewport")
    bpy.context.scene.frame_set(current_frame)
    obj.hide_viewport = False
    obj.hide_render = False
    obj.keyframe_insert(data_path="hide_render")
    obj.keyframe_insert(data_path="hide_viewport")


def set_parented_object_matrix(obj, matrix):
    matrix_world = matrices.identity @ matrices.rotation @ matrices.scaled_matrix(import_options.import_scale)
    top_empty.matrix_world = matrix_world
    obj.matrix_world = matrix

    if import_options.make_gaps and import_options.gap_target == "object":
        if import_options.gap_scale_strategy == "object":
            matrix_world = obj.matrix_world @ matrices.scaled_matrix(import_options.gap_scale)
            obj.matrix_world = matrix_world
        elif import_options.gap_scale_strategy == "constraint":
            global gap_scale_empty
            if gap_scale_empty is None and top_collection is not None:
                gap_scale_empty = bpy.data.objects.new("gap_scale", None)
                matrix_world = gap_scale_empty.matrix_world @ matrices.scaled_matrix(import_options.gap_scale)
                gap_scale_empty.matrix_world = matrix_world
                top_collection.objects.link(gap_scale_empty)
            copy_scale_constraint = obj.constraints.new("COPY_SCALE")
            copy_scale_constraint.target = gap_scale_empty
            copy_scale_constraint.target.parent = top_empty

    obj.parent = top_empty  # must be after matrix_world set or else transform is incorrect


def set_object_matrix(obj, matrix):
    matrix_world = matrices.identity @ matrices.rotation @ matrices.scaled_matrix(import_options.import_scale)
    matrix_world = matrix_world @ matrix

    if import_options.make_gaps and import_options.gap_target == "object":
        matrix_world = matrix_world @ matrices.scaled_matrix(import_options.gap_scale)

    obj.matrix_world = matrix_world


def process_face(file, bm, mesh, face, color_code, texmap):
    face.smooth = import_options.shade_smooth
    color = ldraw_colors.get_color(color_code)
    part_slopes = special_bricks.get_part_slopes(file.name)

    material = blender_materials.get_material(color, part_slopes=part_slopes, texmap=texmap)
    if material is not None:
        # https://blender.stackexchange.com/questions/23905/select-faces-depending-on-material
        if material.name not in mesh.materials:
            mesh.materials.append(material)
        face.material_index = mesh.materials.find(material.name)

    if texmap is not None:
        texmap.uv_unwrap_face(bm, face)


def bmesh_ops(mesh):
    bm = bmesh.new()
    bm.from_mesh(mesh)

    bm.faces.ensure_lookup_table()
    bm.verts.ensure_lookup_table()
    bm.edges.ensure_lookup_table()

    if import_options.remove_doubles:
        bmesh.ops.remove_doubles(bm, verts=bm.verts[:], dist=import_options.merge_distance)

    if import_options.recalculate_normals:
        bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])

    bm.to_mesh(mesh)
    bm.clear()
    bm.free()


def get_gp_mesh(key, mesh, color_code):
    gp_key = f"gp_{key}"
    if gp_key not in bpy.data.grease_pencils:
        gp_mesh = bpy.data.grease_pencils.new(gp_key)

        gp_mesh.pixel_factor = 5.0
        gp_mesh.stroke_depth_order = "3D"

        gp_layer = gp_mesh.layers.new("gpl")
        gp_layer.line_change = 2

        gp_frame = gp_layer.frames.new(1)
        # gp_layer.active_frame = gp_frame

        for e in mesh.edges:
            gp_stroke = gp_frame.strokes.new()
            gp_stroke.material_index = 0
            gp_stroke.line_width = 10.0
            for v in e.vertices:
                i = len(gp_stroke.points)
                gp_stroke.points.add(1)
                gp_point = gp_stroke.points[i]
                gp_point.co = mesh.vertices[v].co

        apply_gp_materials(gp_mesh, color_code)
    gp_mesh = bpy.data.grease_pencils[gp_key]
    return gp_mesh


# https://blender.stackexchange.com/a/166492
def apply_gp_materials(gp_mesh, color_code):
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
        material.grease_pencil.color = material.diffuse_color
    material = bpy.data.materials[material_name]
    gp_mesh.materials.append(material)


class LDrawNode:
    """
    All of the data that makes up a part.
    """

    def __init__(self, file):
        self.file = file
        self.color_code = "16"
        self.matrix = matrices.identity
        self.top = False
        self.meta_command = None
        self.meta_args = {}

    def load(self, parent_matrix=matrices.identity, color_code="16", geometry_data=None, is_edge_logo=False, parent_collection=None):
        global part_count
        global top_collection
        global top_empty
        global next_collection
        global end_next_collection

        # these meta commands affect the scene
        if self.file is None:
            if self.meta_command == "step":
                set_step()
            elif self.meta_command == "group_begin":
                create_meta_group(self.meta_args["name"], parent_collection)
                end_next_collection = False
                if self.meta_args["name"] in bpy.data.collections:
                    next_collection = bpy.data.collections[self.meta_args["name"]]
            elif self.meta_command == "group_end":
                end_next_collection = True
            elif self.meta_command == "group_def":
                if self.meta_args["id"] not in collection_id_map:
                    collection_id_map[self.meta_args["id"]] = self.meta_args["name"]
                create_meta_group(self.meta_args["name"], parent_collection)
            elif self.meta_command == "group_nxt":
                if self.meta_args["id"] in collection_id_map:
                    key = collection_id_map[self.meta_args["id"]]
                    if key in bpy.data.collections:
                        next_collection = bpy.data.collections[key]
                end_next_collection = True
            elif self.meta_command == "save":
                if import_options.set_timelime_markers:
                    bpy.context.scene.timeline_markers.new("SAVE", frame=current_frame)
            elif self.meta_command == "clear":
                if import_options.set_timelime_markers:
                    bpy.context.scene.timeline_markers.new("CLEAR", frame=current_frame)
                if top_collection is not None:
                    for ob in top_collection.all_objects:
                        bpy.context.scene.frame_set(current_frame)
                        ob.hide_viewport = True
                        ob.hide_render = True
                        ob.keyframe_insert(data_path="hide_render")
                        ob.keyframe_insert(data_path="hide_viewport")
            return

        if import_options.no_studs and self.file.is_like_stud():
            return

        # set the working color code to this file's
        # color code if it isn't color code 16
        if self.color_code != "16":
            color_code = self.color_code

        is_model = self.file.is_like_model()
        is_shortcut = self.file.is_shortcut()
        is_part = self.file.is_part()
        is_subpart = self.file.is_subpart()

        matrix = parent_matrix @ self.matrix
        collection = parent_collection

        if is_model:
            collection_name = os.path.basename(self.file.name)
            collection = bpy.data.collections.new(collection_name)
            if parent_collection is not None:
                parent_collection.children.link(collection)

            if top_collection is None:
                top_collection = collection
                if import_options.parent_to_empty and top_empty is None:
                    top_empty = bpy.data.objects.new(top_collection.name, None)
                    if top_collection is not None:
                        top_collection.objects.link(top_empty)
        elif geometry_data is None:  # top-level part
            geometry_data = GeometryData()
            matrix = matrices.identity
            self.top = True
            part_count += 1
            texmap.reset_caches()  # or else the previous part's texmap is applied to this part

        if import_options.meta_group and next_collection is not None:
            collection = next_collection
            if end_next_collection:
                next_collection = None

        _key = []
        _key.append(self.file.name)
        _key.append(color_code)
        _key.append(hash(matrix.freeze()))
        _key = "_".join([str(k).lower() for k in _key])
        _key = re.sub(r"[^a-z0-9._]", "-", _key)

        if _key not in key_map:
            key_map[_key] = str(uuid.uuid4())
        key = key_map[_key]

        # if it's a part and geometry already in the geometry_cache, reuse it
        # meta commands are not in self.top files which is how they are counted
        # missing minifig arms if "if key not in bpy.data.meshes:"
        # with "self.top and" removed, it is faster but if the top level part is
        # used as a transformed subpart, it may render incorrectly
        if key in geometry_data_cache:
            geometry_data = geometry_data_cache[key]
        else:
            if geometry_data is not None:
                if self.file.is_edge_logo():
                    is_edge_logo = True

                if (not is_edge_logo) or (is_edge_logo and import_options.display_logo):
                    geometry_data.add_edge_data(matrix, color_code, self.file.geometry)

                geometry_data.add_face_data(matrix, color_code, self.file.geometry)

            for child_node in self.file.child_nodes:
                child_node.load(
                    geometry_data=geometry_data,
                    parent_matrix=matrix,
                    color_code=color_code,
                    parent_collection=collection,
                    is_edge_logo=is_edge_logo,
                )

            # without "if self.top:"
            # 10030-1 - Imperial Star Destroyer - UCS.mpd top back of the bridge - 3794a.dat renders incorrectly
            if self.top:
                geometry_data_cache[key] = geometry_data

        if self.top:
            matrix = parent_matrix @ self.matrix
            scaled_matrix = matrices.scaled_matrix(import_options.gap_scale)

            e_key = f"e_{key}"
            gp_key = f"gp_{key}"

            if key not in bpy.data.meshes:
                bm = bmesh.new()

                mesh = bpy.data.meshes.new(key)
                mesh.name = key
                mesh[strings.ldraw_filename_key] = self.file.name

                # FIXME: 31313 - Mindstorms EV3 - Spike3r.mpd - "31313 - 13710ac01.dat"
                # FIXME: if not treat_shortcut_as_model, texmap uvs may be incorrect, caused by unexpected part transform?
                # FIXME: move uv unwrap to after obj[strings.ldraw_filename_key] = self.file.name
                for fd in geometry_data.face_data:
                    for fi in fd.face_infos:
                        verts = []
                        for vertex in fi.vertices:
                            vert = fd.matrix @ vertex
                            bm_vert = bm.verts.new(vert)
                            verts.append(bm_vert)
                        face = bm.faces.new(verts)

                        color_code = fd.color_code
                        if fi.color_code != "16":
                            color_code = fi.color_code

                        process_face(self.file, bm, mesh, face, color_code, fi.texmap)

                bm.faces.ensure_lookup_table()
                bm.verts.ensure_lookup_table()
                bm.edges.ensure_lookup_table()

                if import_options.remove_doubles:
                    # if vertices in sharp edge collection, do not add to merge collection
                    bmesh.ops.remove_doubles(bm, verts=bm.verts[:], dist=import_options.merge_distance)

                if import_options.recalculate_normals:
                    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])

                # bpy.context.object.data.edges[6].use_edge_sharp = True
                # Create kd tree for fast "find nearest points" calculation
                # https://docs.blender.org/api/blender_python_api_current/mathutils.kdtree.html
                vertices = bm.verts
                kd = mathutils.kdtree.KDTree(len(vertices))
                for i, v in enumerate(vertices):
                    kd.insert(v.co, i)
                kd.balance()

                # increase the distance to look for edges to merge
                # merge line type 2 edges at a greater distance than mesh edges
                distance = import_options.merge_distance * 2
                distance = import_options.merge_distance

                edge_mesh = bpy.data.meshes.new(e_key)
                edge_mesh.name = e_key
                edge_mesh[strings.ldraw_filename_key] = self.file.name

                e_verts = []
                e_edges = []
                e_faces = []
                i = 0
                # Create edge_indices dictionary, which is the list of edges as pairs of indices into our verts array
                edge_indices = set()
                for ed in geometry_data.edge_data:
                    for fi in ed.face_infos:
                        edge_verts = []
                        face_indices = []
                        for vertex in fi.vertices:
                            vert = ed.matrix @ vertex
                            e_verts.append(vert)
                            edge_verts.append(vert)
                            face_indices.append(i)
                            i += 1

                        edges0 = [index for (co, index, dist) in kd.find_range(edge_verts[0], distance)]
                        edges1 = [index for (co, index, dist) in kd.find_range(edge_verts[1], distance)]
                        for e0 in edges0:
                            for e1 in edges1:
                                edge_indices.add((e0, e1))
                                edge_indices.add((e1, e0))

                        e_faces.append(face_indices)

                edge_mesh.from_pydata(e_verts, e_edges, e_faces)
                edge_mesh.update()
                edge_mesh.validate()

                # # Find the appropriate mesh edges and make them sharp (i.e. not smooth)
                # merge = set()
                # for edge in bm.edges:
                #     v0 = edge.verts[0].index
                #     v1 = edge.verts[1].index
                #     if (v0, v1) in edge_indices:
                #         merge.add(edge.verts[0])
                #         merge.add(edge.verts[1])
                #
                #         # Make edge sharp
                #         edge.smooth = False
                #
                # # if it was detected as a edge, the merge those vertices
                # bmesh.ops.remove_doubles(bm, verts=list(merge), dist=distance)

                bm.to_mesh(mesh)
                bm.clear()
                bm.free()

                mesh.update()
                mesh.validate()

                for edge in mesh.edges:
                    v0 = edge.vertices[0]
                    v1 = edge.vertices[1]
                    if (v0, v1) in edge_indices:
                        edge.use_edge_sharp = True
                        edge.use_freestyle_mark = True

                if import_options.smooth_type == "auto_smooth":
                    mesh.use_auto_smooth = import_options.shade_smooth
                    auto_smooth_angle = 89.9  # 1.56905 - 89.9 so 90 degrees and up are affected
                    auto_smooth_angle = 51.1
                    auto_smooth_angle = 31
                    auto_smooth_angle = 44.97
                    mesh.auto_smooth_angle = math.radians(auto_smooth_angle)

                if import_options.make_gaps and import_options.gap_target == "mesh":
                    mesh.transform(scaled_matrix)
                    edge_mesh.transform(scaled_matrix)

            mesh = bpy.data.meshes[key]

            obj = do_create_object(mesh)
            obj[strings.ldraw_filename_key] = self.file.name
            process_object(obj, matrix)

            if import_options.smooth_type == "edge_split":
                edge_modifier = obj.modifiers.new("Edge Split", type='EDGE_SPLIT')
                edge_modifier.use_edge_angle = True
                edge_modifier.split_angle = math.radians(89.9)
                edge_modifier.use_edge_sharp = True

            # https://b3d.interplanety.org/en/how-to-get-global-vertex-coordinates/
            if collection is not None:
                collection.objects.link(obj)
            else:
                bpy.context.scene.collection.objects.link(obj)

            if import_options.import_edges or import_options.grease_pencil_edges:
                if e_key in bpy.data.meshes:
                    edge_mesh = bpy.data.meshes[e_key]

                    if import_options.import_edges:
                        edge_obj = do_create_object(edge_mesh)
                        process_object(edge_obj, matrix)
                        edge_obj.parent = obj
                        edge_obj.matrix_world = obj.matrix_world
                        edge_obj[strings.ldraw_filename_key] = f"{self.file.name}_edges"

                    if collection is not None:
                        collection.objects.link(edge_obj)
                    else:
                        bpy.context.scene.collection.objects.link(edge_obj)

            #     if import_options.grease_pencil_edges:
            #         if gp_key not in bpy.data.grease_pencils:
            #             gp_mesh = bpy.data.grease_pencils.new(gp_key)
            #             gp_mesh.name = gp_key
            #             gp_mesh.pixel_factor = 5.0
            #             gp_mesh.stroke_depth_order = "3D"
            #
            #             gp_layer = gp_mesh.layers.new("gpl")
            #             gp_layer.line_change = 2
            #
            #             gp_frame = gp_layer.frames.new(1)
            #             # gp_layer.active_frame = gp_frame
            #
            #             for e in edge_mesh.edges:
            #                 gp_stroke = gp_frame.strokes.new()
            #                 gp_stroke.material_index = 0
            #                 gp_stroke.line_width = 10.0
            #                 for v in e.vertices:
            #                     i = len(gp_stroke.points)
            #                     gp_stroke.points.add(1)
            #                     gp_point = gp_stroke.points[i]
            #                     gp_point.co = edge_mesh.vertices[v].co
            #
            #             apply_gp_materials(gp_mesh, self.color_code)
            #
            #             bpy.data.grease_pencils[gp_key] = gp_mesh
            #         gp_mesh = bpy.data.grease_pencils[gp_key]
            #
            #         gp_obj = bpy.data.objects.new(gp_key, gp_mesh)
            #         process_object(gp_obj, matrix)
            #         gp_obj.parent = obj
            #         gp_obj.matrix_world = obj.matrix_world
            #         gp_obj.active_material_index = len(gp_mesh.materials)
            #
            #         name = "Grease Pencil Edges"
            #         if name not in bpy.data.collections:
            #             collection = bpy.data.collections.new(name)
            #             bpy.context.scene.collection.children.link(collection)
            #         collection = bpy.context.scene.collection.children[name]
            #         collection.objects.link(gp_obj)
