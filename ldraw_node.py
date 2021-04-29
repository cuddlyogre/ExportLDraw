import os
import bpy
import math

from . import strings
from . import options
from . import matrices
from .ldraw_geometry import LDrawGeometry
from .face_info import FaceInfo
from . import blender_mesh


def reset_caches():
    global part_count
    global current_step
    global last_frame
    global face_info_cache
    global geometry_cache
    global top_collection
    global top_empty
    global gap_scale_empty
    global collection_id_map
    global next_collection
    global end_next_collection

    part_count = 0
    current_step = 0
    last_frame = 0
    face_info_cache = {}
    geometry_cache = {}
    top_collection = None
    top_empty = None
    gap_scale_empty = None
    collection_id_map = {}
    next_collection = None
    end_next_collection = False

    if options.meta_step:
        set_step()


def set_step():
    start_frame = options.starting_step_frame
    frame_length = options.frames_per_step
    global last_frame
    last_frame = (start_frame + frame_length) + (frame_length * current_step)
    if options.set_timelime_markers:
        bpy.context.scene.timeline_markers.new("STEP", frame=last_frame)


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
    if options.instancing:
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


def create_object(mesh, parent_matrix, matrix):
    obj = do_create_object(mesh)

    if top_empty is None:
        obj.matrix_world = matrices.scaled_matrix(options.import_scale) @ matrices.rotation @ parent_matrix @ matrix
        if options.make_gaps and options.gap_target == "object":
            obj.matrix_world = obj.matrix_world @ matrices.scaled_matrix(options.gap_scale)
    else:
        obj.matrix_world = parent_matrix @ matrix

        if options.make_gaps and options.gap_target == "object":
            if options.gap_scale_strategy == "object":
                obj.matrix_world = obj.matrix_world @ matrices.scaled_matrix(options.gap_scale)
            elif options.gap_scale_strategy == "constraint":
                global gap_scale_empty
                if gap_scale_empty is None and top_collection is not None:
                    gap_scale_empty = bpy.data.objects.new("gap_scale", None)
                    gap_scale_empty.matrix_world = gap_scale_empty.matrix_world @ matrices.scaled_matrix(options.gap_scale)
                    top_collection.objects.link(gap_scale_empty)
                copy_constraint = obj.constraints.new("COPY_SCALE")
                copy_constraint.target = gap_scale_empty
                copy_constraint.target.parent = top_empty

        obj.parent = top_empty  # must be after matrix_world set or else transform is incorrect

    # https://docs.blender.org/api/current/bpy.types.bpy_struct.html#bpy.types.bpy_struct.keyframe_insert
    # https://docs.blender.org/api/current/bpy.types.Scene.html?highlight=frame_set#bpy.types.Scene.frame_set
    # https://docs.blender.org/api/current/bpy.types.Object.html?highlight=rotation_quaternion#bpy.types.Object.rotation_quaternion
    if options.meta_step:
        bpy.context.scene.frame_set(options.starting_step_frame)
        obj.hide_viewport = True
        obj.hide_render = True
        obj.keyframe_insert(data_path="hide_render")
        obj.keyframe_insert(data_path="hide_viewport")

        bpy.context.scene.frame_set(last_frame)
        obj.hide_viewport = False
        obj.hide_render = False
        obj.keyframe_insert(data_path="hide_render")
        obj.keyframe_insert(data_path="hide_viewport")

    if options.smooth_type == "edge_split":
        edge_modifier = obj.modifiers.new("Edge Split", type='EDGE_SPLIT')
        edge_modifier.use_edge_angle = True
        edge_modifier.split_angle = math.radians(89.9)  # 1.56905 - 89.9 so 90 degrees and up are affected
        edge_modifier.use_edge_sharp = True

    if options.bevel_edges:
        bevel_modifier = obj.modifiers.new("Bevel", type='BEVEL')
        bevel_modifier.width = 0.10
        bevel_modifier.segments = 4
        bevel_modifier.profile = 0.5
        bevel_modifier.limit_method = "WEIGHT"
        bevel_modifier.use_clamp_overlap = True

    return obj


class LDrawNode:
    def __init__(self, file, color_code="16", matrix=matrices.identity):
        self.file = file
        self.color_code = color_code
        self.matrix = matrix
        self.top = False
        self.meta_command = None
        self.meta_args = {}

    def load(self, parent_matrix=matrices.identity, parent_color_code="16", geometry=None, is_stud=False, is_edge_logo=False, parent_collection=None):
        global part_count
        global current_step
        global top_collection
        global top_empty
        global next_collection
        global end_next_collection

        if self.file is None:
            if self.meta_command == "step":
                current_step += 1
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
                if options.set_timelime_markers:
                    bpy.context.scene.timeline_markers.new("SAVE", frame=last_frame)
            elif self.meta_command == "clear":
                if options.set_timelime_markers:
                    bpy.context.scene.timeline_markers.new("CLEAR", frame=last_frame)
                if top_collection is not None:
                    for ob in top_collection.all_objects:
                        bpy.context.scene.frame_set(last_frame)
                        ob.hide_viewport = True
                        ob.hide_render = True
                        ob.keyframe_insert(data_path="hide_render")
                        ob.keyframe_insert(data_path="hide_viewport")
            return

        if options.no_studs and self.file.is_like_stud():
            return

        if self.color_code != "16":
            parent_color_code = self.color_code

        key = []
        key.append(self.file.name)
        key.append(parent_color_code)
        if parent_color_code == "24":
            key.append("edge")
        key = "_".join([k.lower() for k in key])[0:63]

        is_model = self.file.is_like_model()
        is_shortcut = self.file.is_shortcut()
        is_part = self.file.is_part()
        is_subpart = self.file.is_subpart()

        matrix = parent_matrix @ self.matrix
        file_collection = parent_collection

        if is_model:
            collection_name = os.path.basename(self.file.filename)
            file_collection = bpy.data.collections.new(collection_name)
            if parent_collection is not None:
                parent_collection.children.link(file_collection)

            if top_collection is None:
                top_collection = file_collection
                if options.parent_to_empty and top_empty is None:
                    top_empty = bpy.data.objects.new(top_collection.name, None)
                    top_empty.matrix_world = top_empty.matrix_world @ matrices.rotation @ matrices.scaled_matrix(options.import_scale)
                    if top_collection is not None:
                        top_collection.objects.link(top_empty)
        elif geometry is None:  # top-level part
            geometry = LDrawGeometry()
            matrix = matrices.identity
            self.top = True
            part_count += 1

        if options.meta_group and next_collection is not None:
            file_collection = next_collection
            if end_next_collection:
                next_collection = None

        if options.debug_text:
            print("===========")
            if is_model:
                print("is_model")
            if is_part:
                print("is_part")
            elif is_shortcut:
                print("is_shortcut")
            elif is_subpart:
                print("is_subpart")
            print(self.file.name)
            print("===========")

        # if it's a part and already in the cache, reuse it
        # meta commands are not in self.top files which is how they are counted
        if self.top and key in geometry_cache:
            geometry = geometry_cache[key]
        else:
            if geometry is not None:
                if self.file.is_stud():
                    is_stud = True

                if self.file.is_edge_logo():
                    is_edge_logo = True

                if key not in face_info_cache:
                    new_face_info = []
                    for face_info in self.file.geometry.face_info:
                        copy = FaceInfo(color_code=parent_color_code, grain_slope_allowed=not is_stud)
                        if parent_color_code == "24":
                            copy.use_edge_color = True
                        if face_info.color_code != "16":
                            copy.color_code = face_info.color_code
                        copy.texmap = face_info.texmap
                        new_face_info.append(copy)
                    face_info_cache[key] = new_face_info
                new_face_info = face_info_cache[key]
                geometry.face_info.extend(new_face_info)

                vertices = [(matrix @ v).to_tuple() for v in self.file.geometry.vertices]
                geometry.vertices.extend(vertices)
                for vert_count in self.file.geometry.vert_counts:
                    new_face = []
                    for _ in range(vert_count):
                        new_face.append(geometry.face_count)
                        geometry.face_count += 1
                    geometry.faces.append(new_face)

                if (not is_edge_logo) or (is_edge_logo and options.display_logo):
                    vertices = [(matrix @ v).to_tuple() for v in self.file.geometry.edge_vertices]
                    geometry.edge_vertices.extend(vertices)
                    for vert_count in self.file.geometry.edge_vert_counts:
                        new_face = []
                        for _ in range(vert_count):
                            new_face.append(geometry.edge_count)
                            geometry.edge_count += 1
                        geometry.edges.append(new_face)

            for child_node in self.file.child_nodes:
                child_node.load(parent_matrix=matrix,
                                parent_color_code=parent_color_code,
                                geometry=geometry,
                                is_stud=is_stud,
                                is_edge_logo=is_edge_logo,
                                parent_collection=file_collection)

            if self.top:
                geometry_cache[key] = geometry

        if self.top:
            mesh = blender_mesh.get_mesh(key, self.file.name, geometry)

            obj = create_object(mesh, parent_matrix, self.matrix)
            obj[strings.ldraw_filename_key] = self.file.name

            if file_collection is not None:
                file_collection.objects.link(obj)
            else:
                bpy.context.scene.collection.objects.link(obj)

            if options.import_edges:
                edge_mesh = blender_mesh.get_edge_mesh(key, self.file.name, geometry)

                if options.grease_pencil_edges:
                    gp_mesh = blender_mesh.get_gp_mesh(key, edge_mesh)

                    gp_object = bpy.data.objects.new(key, gp_mesh)
                    gp_object.matrix_world = parent_matrix @ self.matrix
                    gp_object.active_material_index = len(gp_mesh.materials)

                    collection_name = "Grease Pencil Edges"
                    if collection_name not in bpy.data.collections:
                        collection = bpy.data.collections.new(collection_name)
                        bpy.context.scene.collection.children.link(collection)
                    collection = bpy.context.scene.collection.children[collection_name]
                    collection.objects.link(gp_object)
