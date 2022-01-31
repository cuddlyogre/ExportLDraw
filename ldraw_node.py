import math
import os
import uuid

import bpy
import bmesh
import mathutils

from .blender_materials import BlenderMaterials
from .import_options import ImportOptions
from .ldraw_colors import LDrawColor
from .texmap import TexMap
from .geometry_data import GeometryData
from . import special_bricks
from . import strings


class LDrawNode:
    """
    All of the data that makes up a part.
    """

    part_count = 0
    top_collection = None
    current_frame = 0
    top_empty = None

    __groups_collection = None
    __gap_scale_empty = None
    __next_collections = []
    __next_collection = None
    __end_next_collection = False
    __current_step = 0
    __current_step_group = None
    __geometry_data_cache = {}
    __collection_id_map = {}
    __key_map = {}

    __auto_smooth_angle = 31
    __auto_smooth_angle = 44.97
    __auto_smooth_angle = 51.1
    __auto_smooth_angle = 89.9  # 1.56905 - 89.9 so 90 degrees and up are affected
    __auto_smooth_angle = math.radians(__auto_smooth_angle)

    __identity = mathutils.Matrix.Identity(4).freeze()
    __rotation = mathutils.Matrix.Rotation(math.radians(-90), 4, 'X').freeze()
    __import_scale_matrix = mathutils.Matrix.Scale(ImportOptions.import_scale, 4).freeze()
    __gap_scale_matrix = mathutils.Matrix.Scale(ImportOptions.gap_scale, 4).freeze()

    @classmethod
    def reset_caches(cls):
        cls.part_count = 0
        cls.top_collection = None
        cls.current_frame = 0
        cls.top_empty = None

        cls.__groups_collection = None
        cls.__gap_scale_empty = None
        cls.__next_collections = []
        cls.__next_collection = None
        cls.__end_next_collection = False
        cls.__current_step = 0
        cls.__current_step_group = None
        cls.__geometry_data_cache = {}
        cls.__collection_id_map = {}
        cls.__key_map = {}

        cls.__set_step()

    def __init__(self):
        self.is_root = False
        self.file = None
        self.line = ""
        self.color_code = "16"
        self.matrix = self.__identity
        self.meta_command = None
        self.meta_args = {}

    def load(self, parent_matrix=None, color_code="16", geometry_data=None, parent_collection=None, is_edge_logo=False):
        if parent_matrix is None:
            parent_matrix = self.__identity

        self.__create_groups_collection()

        if self.__meta_commands():
            return

        # set the working color code to this file's
        # color code if it isn't color code 16
        if self.color_code != "16":
            color_code = self.color_code

        if self.file.is_edge_logo():
            is_edge_logo = True

        top = False
        matrix = parent_matrix @ self.matrix
        collection = parent_collection

        # if top_collection is none then this is the beginning of the import, so collection/parent_collection will be none
        if LDrawNode.top_collection is None:
            collection = self.__create_file_collection(bpy.context.scene.collection)
            LDrawNode.top_collection = collection

        if self.file.is_model():
            # if parent_collection is not None, this is a nested model
            if parent_collection is not None:
                collection = self.__create_file_collection(parent_collection)
        elif self.file.is_shortcut():
            # TODO: instead of adding to group, parent to empty
            pass
        elif geometry_data is None:  # top-level part
            geometry_data = GeometryData()
            matrix = self.__identity
            top = True
            LDrawNode.part_count += 1

        key = self.__build_key(self.file.name, color_code, matrix)

        if key in LDrawNode.__geometry_data_cache:
            geometry_data = LDrawNode.__geometry_data_cache[key]
        else:
            if geometry_data is not None:
                if (not is_edge_logo) or (is_edge_logo and ImportOptions.display_logo):
                    geometry_data.add_edge_data(matrix, color_code, self.file.geometry)
                geometry_data.add_face_data(matrix, color_code, self.file.geometry)
                geometry_data.add_line_data(matrix, color_code, self.file.geometry)

            for child_node in self.file.child_nodes:
                child_node.load(
                    parent_matrix=matrix,
                    color_code=color_code,
                    geometry_data=geometry_data,
                    parent_collection=collection,
                    is_edge_logo=is_edge_logo,
                )

                self.__meta_root_group_nxt(child_node)

            # without "if top:"
            # 10030-1 - Imperial Star Destroyer - UCS.mpd top back of the bridge - 3794a.dat renders incorrectly
            if top:
                LDrawNode.__geometry_data_cache[key] = geometry_data

        # TODO: use ldraw_color_code mesh attribute and materials to allow for the same mesh data with different colors
        if not top:
            return

        mesh = bpy.data.meshes.get(key)
        if mesh is None:
            mesh = self.create_mesh(key, geometry_data)

        obj = self.__process_top_object(mesh, parent_matrix, color_code, collection)
        self.__process_top_edges(key, obj, color_code, collection)

        TexMap.reset_caches()  # or else the previous part's texmap is applied to this part

        return self

    @staticmethod
    def __build_key(filename, color_code, matrix):
        _key = []
        _key.append(filename)
        _key.append(color_code)
        _key.append(hash(matrix.freeze()))
        _key = "_".join([str(k).lower() for k in _key])

        if _key not in LDrawNode.__key_map:
            LDrawNode.__key_map[_key] = str(uuid.uuid4())
        key = LDrawNode.__key_map[_key]
        return key

    def create_mesh(self, key, geometry_data):
        bm = bmesh.new()
        mesh = bpy.data.meshes.new(key)
        mesh.name = key
        mesh[strings.ldraw_filename_key] = self.file.name
        self.__process_bmesh(bm, mesh, geometry_data)
        self.__process_bmesh_edges(key, bm, geometry_data)
        bm.to_mesh(mesh)
        bm.clear()
        bm.free()
        mesh.update()
        mesh.validate()
        self.__process_mesh(mesh)
        return mesh

    @classmethod
    def __create_groups_collection(cls):
        if ImportOptions.meta_group:
            collection_name = 'Groups'
            if collection_name not in bpy.data.collections:
                c = bpy.data.collections.new(collection_name)
                bpy.context.scene.collection.children.link(c)
            cls.__groups_collection = bpy.data.collections[collection_name]

    def __create_file_collection(self, host_collection):
        collection_name = os.path.basename(self.file.name[:63])
        if collection_name not in bpy.data.collections:
            bpy.data.collections.new(collection_name)
        collection = bpy.data.collections[collection_name]
        if collection.name not in host_collection.children:
            host_collection.children.link(collection)
        return collection

    # https://b3d.interplanety.org/en/how-to-get-global-vertex-coordinates/
    # https://blender.stackexchange.com/questions/50160/scripting-low-level-join-meshes-elements-hopefully-with-bmesh
    # https://blender.stackexchange.com/questions/188039/how-to-join-only-two-objects-to-create-a-new-object-using-python
    # https://blender.stackexchange.com/questions/23905/select-faces-depending-on-material
    # FIXME: 31313 - Mindstorms EV3 - Spike3r.mpd - "31313 - 13710ac01.dat"
    # FIXME: if not treat_shortcut_as_model, texmap uvs may be incorrect, caused by unexpected part transform?
    # FIXME: move uv unwrap to after obj[strings.ldraw_filename_key] = self.file.name
    def __process_bmesh(self, bm, mesh, geometry_data):
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

                self.__process_bmesh_face(bm, mesh, face, color_code, fi.texmap)
        bm.faces.ensure_lookup_table()
        bm.verts.ensure_lookup_table()
        bm.edges.ensure_lookup_table()

        self.__clean_bmesh(bm)

    def __process_bmesh_face(self, bm, mesh, face, color_code, texmap):
        face.smooth = ImportOptions.shade_smooth

        part_slopes = special_bricks.get_part_slopes(self.file.name)
        material = BlenderMaterials.get_material(color_code, part_slopes=part_slopes, texmap=texmap)
        if material.name not in mesh.materials:
            mesh.materials.append(material)
        face.material_index = mesh.materials.find(material.name)

        if texmap is not None:
            texmap.uv_unwrap_face(bm, face)

    @staticmethod
    def __clean_bmesh(bm):
        if ImportOptions.remove_doubles:
            # TODO: if vertices in sharp edge collection, do not add to merge collection
            bmesh.ops.remove_doubles(bm, verts=bm.verts[:], dist=ImportOptions.merge_distance)

        if ImportOptions.recalculate_normals:
            bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])

    # bpy.context.object.data.edges[6].use_edge_sharp = True
    # Create kd tree for fast "find nearest points" calculation
    # https://docs.blender.org/api/blender_python_api_current/mathutils.kdtree.html
    @staticmethod
    def __build_kd(bm):
        kd = mathutils.kdtree.KDTree(len(bm.verts))
        for i, v in enumerate(bm.verts):
            kd.insert(v.co, i)
        kd.balance()
        return kd

    @classmethod
    def __process_bmesh_edges(cls, key, bm, geometry_data):
        kd = cls.__build_kd(bm)

        # increase the distance to look for edges to merge
        # merge line type 2 edges at a greater distance than mesh edges
        distance = ImportOptions.merge_distance
        distance = ImportOptions.merge_distance * 2

        e_edges, e_faces, e_verts, edge_indices = cls.__build_edge_data(geometry_data, kd, distance)
        cls.__create_edge_mesh(key, e_edges, e_faces, e_verts)
        cls.__remove_bmesh_doubles(bm, edge_indices, distance)

    @staticmethod
    def __build_edge_data(geometry_data, kd, distance):
        e_verts = []
        e_edges = []
        e_faces = []

        # Create edge_indices dictionary, which is the list of edges as pairs of indices into our verts array
        edge_indices = set()

        i = 0
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
                e_faces.append(face_indices)

                if ImportOptions.remove_doubles:
                    edges0 = [index for (co, index, dist) in kd.find_range(edge_verts[0], distance)]
                    edges1 = [index for (co, index, dist) in kd.find_range(edge_verts[1], distance)]
                    for e0 in edges0:
                        for e1 in edges1:
                            edge_indices.add((e0, e1))
                            edge_indices.add((e1, e0))

        return e_edges, e_faces, e_verts, edge_indices

    @staticmethod
    def __remove_bmesh_doubles(bm, edge_indices, distance):
        if ImportOptions.remove_doubles:
            # Find the appropriate mesh edges and make them sharp (i.e. not smooth)
            merge = set()
            for edge in bm.edges:
                v0 = edge.verts[0].index
                v1 = edge.verts[1].index
                if (v0, v1) in edge_indices:
                    merge.add(edge.verts[0])
                    merge.add(edge.verts[1])
                    edge.smooth = False

            # if it was detected as an edge, then merge those vertices
            bmesh.ops.remove_doubles(bm, verts=list(merge), dist=distance)

    @classmethod
    def __process_mesh(cls, mesh):
        if ImportOptions.use_freestyle_edges:
            for edge in mesh.edges:
                if edge.use_edge_sharp:
                    edge.use_freestyle_mark = True

        if ImportOptions.smooth_type == "auto_smooth":
            mesh.use_auto_smooth = ImportOptions.shade_smooth
            mesh.auto_smooth_angle = cls.__auto_smooth_angle

        if ImportOptions.make_gaps and ImportOptions.gap_target == "mesh":
            mesh.transform(cls.__gap_scale_matrix)

    def __process_top_object(self, mesh, parent_matrix, color_code, collection):
        obj = self.__do_create_object(mesh)
        obj[strings.ldraw_filename_key] = self.file.name
        obj[strings.ldraw_color_code_key] = color_code

        # bpy.context.space_data.shading.color_type = 'MATERIAL'
        # bpy.context.space_data.shading.color_type = 'OBJECT'
        # Shading > Color > Object to see object colors
        color = LDrawColor.get_color(color_code)
        obj.color = color.color_a

        self.__process_top_object_matrix(obj, parent_matrix)
        self.__process_top_object_gap(obj)
        self.__process_top_object_edges(obj)

        self.__meta_step(obj)

        self.__link_obj_to_collection(obj, collection)
        return obj

    def __process_top_object_matrix(self, obj, parent_matrix):
        matrix = parent_matrix @ self.matrix
        transform_matrix = LDrawNode.__identity @ LDrawNode.__rotation @ LDrawNode.__import_scale_matrix
        if ImportOptions.parent_to_empty:
            if LDrawNode.top_empty is None:
                LDrawNode.top_empty = bpy.data.objects.new(LDrawNode.top_collection.name, None)
                LDrawNode.top_collection.objects.link(LDrawNode.top_empty)

            LDrawNode.top_empty.matrix_world = transform_matrix
            obj.matrix_world = matrix
            obj.parent = LDrawNode.top_empty  # must be after matrix_world set or else transform is incorrect
        else:
            matrix_world = transform_matrix @ matrix
            obj.matrix_world = matrix_world

    @classmethod
    def __process_top_object_gap(cls, obj):
        if ImportOptions.make_gaps and ImportOptions.gap_target == "object":
            if ImportOptions.gap_scale_strategy == "object":
                matrix_world = obj.matrix_world @ cls.__gap_scale_matrix
                obj.matrix_world = matrix_world
            elif ImportOptions.gap_scale_strategy == "constraint":
                if cls.__gap_scale_empty is None:
                    cls.__gap_scale_empty = bpy.data.objects.new("gap_scale", None)
                    cls.__gap_scale_empty.use_fake_user = True
                    matrix_world = cls.__gap_scale_empty.matrix_world @ cls.__gap_scale_matrix
                    cls.__gap_scale_empty.matrix_world = matrix_world
                    cls.top_collection.objects.link(cls.__gap_scale_empty)
                copy_scale_constraint = obj.constraints.new("COPY_SCALE")
                copy_scale_constraint.target = cls.__gap_scale_empty
                copy_scale_constraint.target.parent = cls.top_empty

    @classmethod
    def __process_top_object_edges(cls, obj):
        if ImportOptions.smooth_type == "edge_split":
            edge_modifier = obj.modifiers.new("Edge Split", type='EDGE_SPLIT')
            edge_modifier.use_edge_sharp = True
            # need this or else items like the back blue window stripes in 10252-1 - Volkswagen Beetle.mpd aren't shaded properly
            edge_modifier.use_edge_angle = True
            edge_modifier.split_angle = cls.__auto_smooth_angle

    @classmethod
    def __create_edge_mesh(cls, key, e_edges, e_faces, e_verts):
        if ImportOptions.import_edges:
            edge_key = f"e_{key}"
            edge_mesh = bpy.data.meshes.new(edge_key)
            edge_mesh.name = edge_key
            edge_mesh.from_pydata(e_verts, e_edges, e_faces)
            edge_mesh.update()
            edge_mesh.validate()

            if ImportOptions.make_gaps and ImportOptions.gap_target == "mesh":
                edge_mesh.transform(cls.__gap_scale_matrix)

    def __process_top_edges(self, key, obj, color_code, collection):
        if ImportOptions.import_edges:
            edge_key = f"e_{key}"
            edge_mesh = bpy.data.meshes[edge_key]
            edge_obj = self.__do_create_object(edge_mesh)
            edge_obj[strings.ldraw_filename_key] = f"{self.file.name}_edges"
            edge_obj[strings.ldraw_color_code_key] = color_code

            color = LDrawColor.get_color(color_code)
            edge_obj.color = color.edge_color_d

            self.__meta_step(edge_obj)

            self.__link_obj_to_collection(edge_obj, collection)

            edge_obj.parent = obj
            edge_obj.matrix_world = obj.matrix_world

    # obj.show_name = True
    @staticmethod
    def __do_create_object(mesh):
        if ImportOptions.instancing:
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

    @classmethod
    def __link_obj_to_collection(cls, obj, collection):
        if obj.name not in collection:
            collection.objects.link(obj)

        if cls.__current_step_group is not None:
            cls.__current_step_group.objects.link(obj)

        if ImportOptions.meta_group:
            if cls.__next_collection is not None:
                cls.__next_collection.objects.link(obj)
            else:
                collection_name = 'Ungrouped'
                if collection_name not in bpy.data.collections:
                    c = bpy.data.collections.new(collection_name)
                    cls.__groups_collection.children.link(c)
                ungrouped_collection = bpy.data.collections[collection_name]
                ungrouped_collection.objects.link(obj)

    @classmethod
    def __set_step(cls):
        if not ImportOptions.meta_step:
            return

        first_frame = (ImportOptions.starting_step_frame + ImportOptions.frames_per_step)
        current_step_frame = (ImportOptions.frames_per_step * cls.__current_step)
        cls.current_frame = first_frame + current_step_frame
        cls.__current_step += 1

        if ImportOptions.set_timeline_markers:
            bpy.context.scene.timeline_markers.new("STEP", frame=cls.current_frame)

        if ImportOptions.meta_step_groups:
            collection_name = f"Steps"
            if collection_name not in bpy.data.collections:
                c = bpy.data.collections.new(collection_name)
                bpy.context.scene.collection.children.link(c)
            steps_collection = bpy.data.collections[collection_name]

            collection_name = f"Step {str(cls.__current_step)}"
            if collection_name not in bpy.data.collections:
                c = bpy.data.collections.new(collection_name)
                steps_collection.children.link(c)
            cls.__current_step_group = bpy.data.collections[collection_name]

    def __meta_commands(self):
        if self.file is not None:
            return False

        if self.meta_command == "step":
            self.__set_step()
        elif self.meta_command == "save":
            self.__meta_save()
        elif self.meta_command == "clear":
            self.__meta_clear()
        elif self.meta_command == "print":
            self.__meta_print()
        elif self.meta_command.startswith("group"):
            if ImportOptions.meta_group:
                if self.meta_command == "group_def":
                    self.__meta_group_def()
                elif self.meta_command == "group_nxt":
                    self.__meta_group_nxt()
                elif self.meta_command == "group_begin":
                    self.__meta_group_begin()
                elif self.meta_command == "group_end":
                    self.__meta_group_end()
        return True

    # https://docs.blender.org/api/current/bpy.types.bpy_struct.html#bpy.types.bpy_struct.keyframe_insert
    # https://docs.blender.org/api/current/bpy.types.Scene.html?highlight=frame_set#bpy.types.Scene.frame_set
    # https://docs.blender.org/api/current/bpy.types.Object.html?highlight=rotation_quaternion#bpy.types.Object.rotation_quaternion
    @classmethod
    def __meta_step(cls, obj):
        if ImportOptions.meta_step:
            bpy.context.scene.frame_set(ImportOptions.starting_step_frame)
            obj.hide_viewport = True
            obj.hide_render = True
            obj.keyframe_insert(data_path="hide_render")
            obj.keyframe_insert(data_path="hide_viewport")
            bpy.context.scene.frame_set(cls.current_frame)
            obj.hide_viewport = False
            obj.hide_render = False
            obj.keyframe_insert(data_path="hide_render")
            obj.keyframe_insert(data_path="hide_viewport")

    @staticmethod
    def __meta_save():
        if ImportOptions.meta_save:
            if ImportOptions.set_timeline_markers:
                bpy.context.scene.timeline_markers.new("SAVE", frame=LDrawNode.current_frame)

    @staticmethod
    def __meta_clear():
        if ImportOptions.meta_clear:
            if ImportOptions.set_timeline_markers:
                bpy.context.scene.timeline_markers.new("CLEAR", frame=LDrawNode.current_frame)
            if LDrawNode.top_collection is not None:
                for ob in LDrawNode.top_collection.all_objects:
                    bpy.context.scene.frame_set(LDrawNode.current_frame)
                    ob.hide_viewport = True
                    ob.hide_render = True
                    ob.keyframe_insert(data_path="hide_render")
                    ob.keyframe_insert(data_path="hide_viewport")

    def __meta_print(self):
        if ImportOptions.meta_print_write:
            print(self.meta_args["message"])

    def __meta_group_def(self):
        collection_name = self.meta_args["name"]
        LDrawNode.__collection_id_map[self.meta_args["id"]] = collection_name
        if collection_name not in bpy.data.collections:
            c = bpy.data.collections.new(collection_name)
            LDrawNode.__groups_collection.children.link(c)

    def __meta_group_nxt(self):
        if self.meta_args["id"] in LDrawNode.__collection_id_map:
            collection_name = LDrawNode.__collection_id_map[self.meta_args["id"]]
            if collection_name in bpy.data.collections:
                LDrawNode.__next_collection = bpy.data.collections[collection_name]
        LDrawNode.__end_next_collection = True

    def __meta_root_group_nxt(self, child_node):
        if ImportOptions.meta_group:
            if self.is_root:
                if child_node.meta_command not in ["group_nxt"]:
                    if LDrawNode.__end_next_collection:
                        LDrawNode.__next_collection = None

    def __meta_group_begin(self):
        if LDrawNode.__next_collection is not None:
            LDrawNode.__next_collections.append(LDrawNode.__next_collection)
        collection_name = self.meta_args["name"]
        if collection_name not in bpy.data.collections:
            c = bpy.data.collections.new(collection_name)
            LDrawNode.__groups_collection.children.link(c)
        LDrawNode.__next_collection = bpy.data.collections[collection_name]
        if len(LDrawNode.__next_collections) > 0:
            LDrawNode.__next_collections[-1].children.link(LDrawNode.__next_collection)

    def __meta_group_end(self):
        if len(LDrawNode.__next_collections) > 0:
            LDrawNode.__next_collection = LDrawNode.__next_collections.pop()
        else:
            LDrawNode.__next_collection = None
