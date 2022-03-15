import math
import uuid

import bpy
import bmesh
import mathutils

from . import group
from . import special_bricks
from . import strings
from .blender_materials import BlenderMaterials
from .geometry_data import GeometryData
from .import_options import ImportOptions
from .ldraw_colors import LDrawColor
from .texmap import TexMap
from . import helpers
from . import ldraw_props
from .ldraw_camera import LDrawCamera
from .pe_texmap import PETexInfo, PETexmap


class LDrawNode:
    """
    All of the data that makes up a part.
    """

    part_count = 0
    top_collection = None
    current_frame = 0
    top_empty = None
    cameras = []

    __groups_collection = None
    __gap_scale_empty = None
    __next_collections = []
    __next_collection = None
    __end_next_collection = False
    __current_step = 0
    __current_step_group = None
    __collection_id_map = {}
    __key_map = {}

    __auto_smooth_angle = 31
    __auto_smooth_angle = 44.97
    __auto_smooth_angle = 51.1
    __auto_smooth_angle = 89.9  # 1.56905 - 89.9 so 90 degrees and up are affected
    __auto_smooth_angle = math.radians(__auto_smooth_angle)

    __identity = mathutils.Matrix.Identity(4).freeze()
    # https://www.ldraw.org/article/218.html#coords
    # LDraw uses a right-handed co-ordinate system where -Y is "up".
    # https://en.wikibooks.org/wiki/Blender_3D:_Noob_to_Pro/Understanding_Coordinates
    # Blender uses a right-handed co-ordinate system where +Z is "up"
    __rotation = mathutils.Matrix.Rotation(math.radians(-90), 4, 'X').freeze()  # rotate -90 degrees on X axis to make -Y up
    __import_scale_matrix = mathutils.Matrix.Scale(ImportOptions.import_scale, 4).freeze()
    __gap_scale_matrix = mathutils.Matrix.Scale(ImportOptions.gap_scale, 4).freeze()

    @classmethod
    def reset_caches(cls):
        cls.part_count = 0
        cls.top_collection = None
        cls.current_frame = 0
        cls.top_empty = None
        cls.cameras = []

        cls.__groups_collection = None
        cls.__gap_scale_empty = None
        cls.__next_collections = []
        cls.__next_collection = None
        cls.__end_next_collection = False
        cls.__current_step = 0
        cls.__current_step_group = None
        cls.__collection_id_map = {}
        cls.__key_map = {}

        cls.__set_step()

        cls.__create_groups_collection()

    def __init__(self):
        self.is_root = False
        self.file = None
        self.line = ""
        self.color_code = "16"
        self.matrix = self.__identity
        self.bfc_certified = None
        self.meta_command = None
        self.meta_args = {}

        self.camera = None

        self.texmap_start = False
        self.texmap_next = False
        self.texmap_fallback = False

        self.texmaps = []
        self.texmap = None

        self.current_pe_tex_path = None
        self.pe_tex_infos = {}
        self.pe_tex_info = None
        self.subfile_line_index = 0

    def load(self, color_code="16", parent_matrix=None, geometry_data=None, parent_collection=None, accum_cull=True, accum_invert=False, texmap=None, pe_tex_info=None):
        if self.file.is_edge_logo() and not ImportOptions.display_logo:
            return
        elif self.file.is_like_stud() and ImportOptions.no_studs:
            return

        if parent_matrix is None:
            parent_matrix = self.__identity

        self.texmap = texmap
        self.pe_tex_info = pe_tex_info

        top = False
        accum_matrix = parent_matrix @ self.matrix
        matrix = accum_matrix
        collection = parent_collection

        # if a file has geometry, treat it like a part
        # otherwise that geometry won't be rendered
        if self.file.is_like_model() and self.file.geometry.vert_count() == 0:
            # if parent_collection is not None, this is a nested model
            if parent_collection is not None:
                collection = group.get_filename_collection(self.file.name, parent_collection)
        elif geometry_data is None:  # top-level part
            LDrawNode.part_count += 1
            top = True
            matrix = self.__identity
            geometry_data = GeometryData()

        key = self.__build_key(self.file.name, color_code, accum_cull, accum_invert)

        mesh = bpy.data.meshes.get(key)
        if mesh is None:
            local_cull = True
            winding = "CCW"
            self.bfc_certified = self.file.is_like_model() or None
            invert_next = False

            for child_node in self.file.child_nodes:
                current_color = self.__determine_color(color_code, child_node.color_code)

                if child_node.meta_command == "bfc":
                    if not ImportOptions.meta_bfc:
                        continue

                    clean_line = child_node.line
                    _params = clean_line.split()

                    # https://www.ldraw.org/article/415.html#processing
                    if self.bfc_certified is None:
                        self.bfc_certified = True
                        if _params[2] == "NOCERTIFY":
                            self.bfc_certified = False

                    if "CERTIFY" in _params:
                        self.bfc_certified = True

                    if "NOCERTIFY" in _params:
                        self.bfc_certified = False

                    if "CLIP" in _params:
                        local_cull = True

                    if "NOCLIP" in _params:
                        local_cull = False

                    if "CCW" in _params:
                        if accum_invert:
                            winding = "CW"
                        else:
                            winding = "CCW"
                    if "CW" in _params:
                        if accum_invert:
                            winding = "CCW"
                        else:
                            winding = "CW"

                    if "INVERTNEXT" in _params:
                        invert_next = True

                    """
                    https://www.ldraw.org/article/415.html#rendering
                    If the rendering engine does not detect and adjust for reversed matrices, the winding of all polygons in
                    the subfile will be switched, causing the subfile to be rendered incorrectly.

                    The typical method of determining that an orientation matrix is reversed is to calculate the determinant of
                    the matrix. If the determinant is negative, then the matrix has been reversed.

                    The typical way to adjust for matrix reversals is to switch the expected winding of the polygon vertices.
                    That is, if the file specifies the winding as CW and the orientation matrix is reversed, the rendering
                    program would proceed as if the winding is CCW.

                    The INVERTNEXT option also reverses the winding of the polygons within the subpart or primitive.
                    If the matrix applied to the subpart or primitive has itself been reversed the INVERTNEXT processing
                    is done IN ADDITION TO the automatic inversion - the two effectively cancelling each other out.
                    """
                    if matrix.determinant() < 0:
                        if not invert_next:
                            if winding == "CW":
                                winding = "CCW"
                            else:
                                winding = "CW"

                    """
                    https://www.ldraw.org/article/415.html#rendering
                    Degenerate Matrices. Some orientation matrices do not allow calculation of a determinate.
                    This calculation is central to BFC processing. If an orientation matrix for a subfile is
                    degenerate, then culling will not be possible for that subfile.

                    https://math.stackexchange.com/a/792591
                    A singular matrix, also known as a degenerate matrix, is a square matrix whose determinate is zero.
                    https://www.algebrapracticeproblems.com/singular-degenerate-matrix/
                    A singular (or degenerate) matrix is a square matrix whose inverse matrix cannot be calculated.
                    Therefore, the determinant of a singular matrix is equal to 0.
                    """
                    if matrix.determinant() == 0:
                        self.bfc_certified = False

                elif child_node.meta_command == "step":
                    self.__set_step()
                elif child_node.meta_command == "save":
                    self.__meta_save()
                elif child_node.meta_command == "clear":
                    self.__meta_clear()
                elif child_node.meta_command == "print":
                    self.__meta_print(child_node)
                elif child_node.meta_command.startswith("group"):
                    self.__meta_group(child_node)
                elif child_node.meta_command == "leocad_camera":
                    self.__meta_leocad_camera(child_node, matrix)
                elif child_node.meta_command == "texmap":
                    self.__meta_texmap(child_node, matrix)
                elif child_node.meta_command == "pe_tex_path":
                    self.__meta_pe_tex_path(child_node)
                elif child_node.meta_command == "pe_tex_info":
                    self.__meta_pe_tex_info(child_node, matrix)
                elif child_node.meta_command == "pe_tex_next_shear":
                    """no idea"""
                elif not self.texmap_fallback:
                    if child_node.meta_command == "1":
                        # TODO: subfile.load() as if it were the file being imported, then merge that mesh into the accumulated mesh
                        if self.bfc_certified:
                            self.__meta_subfile(
                                child_node,
                                current_color,
                                matrix,
                                geometry_data,
                                collection,
                                (accum_cull and local_cull),
                                (accum_invert ^ invert_next),
                            )
                        else:
                            self.__meta_subfile(
                                child_node,
                                current_color,
                                matrix,
                                geometry_data,
                                collection,
                                False,
                                (accum_invert ^ invert_next),
                            )
                    elif child_node.meta_command == "2":
                        self.__meta_edge(
                            child_node,
                            current_color,
                            matrix,
                            geometry_data,
                        )
                    elif child_node.meta_command in ["3", "4"]:
                        if accum_cull and local_cull and self.bfc_certified:
                            self.__meta_face(
                                child_node,
                                current_color,
                                matrix,
                                geometry_data,
                                winding,
                            )
                        else:
                            self.__meta_face(
                                child_node,
                                current_color,
                                matrix,
                                geometry_data,
                                None,
                            )
                    elif child_node.meta_command == "5":
                        self.__meta_line(
                            child_node,
                            current_color,
                            matrix,
                            geometry_data,
                        )

                if self.texmap_next:
                    self.__set_texmap_end()

                if child_node.meta_command != "bfc":
                    invert_next = False
                elif "INVERTNEXT" not in child_node.meta_args:
                    invert_next = False

        if top:
            if mesh is None:
                mesh = self.__create_mesh(key, geometry_data)
            obj = self.__process_top_object(mesh, accum_matrix, color_code, collection)
            self.__process_top_edges(key, obj, color_code, collection)

    # set the working color code to this file's
    # color code if it isn't color code 16
    @staticmethod
    def __determine_color(parent_color_code, this_color_code):
        color_code = this_color_code
        if this_color_code == "16":
            color_code = parent_color_code
        return color_code

    @classmethod
    def __build_key(cls, filename, color_code, accum_cull, accum_invert):
        _key = (filename, color_code, accum_cull, accum_invert,)

        key = cls.__key_map.get(_key)
        if key is None:
            cls.__key_map[_key] = str(uuid.uuid4())
            key = cls.__key_map.get(_key)

        return key

    def __create_mesh(self, key, geometry_data):
        bm = bmesh.new()

        mesh = bpy.data.meshes.new(key)
        mesh.name = key
        mesh[strings.ldraw_filename_key] = self.file.name

        self.__process_bmesh(bm, mesh, geometry_data)
        self.__process_bmesh_edges(key, bm, geometry_data)

        helpers.finish_bmesh(bm, mesh)
        helpers.finish_mesh(mesh)

        self.__process_mesh(mesh)

        return mesh

    @classmethod
    def __create_groups_collection(cls):
        if ImportOptions.meta_group:
            collection_name = 'Groups'
            host_collection = bpy.context.scene.collection
            c = group.get_collection(collection_name, host_collection)
            cls.__groups_collection = c

    # https://b3d.interplanety.org/en/how-to-get-global-vertex-coordinates/
    # https://blender.stackexchange.com/questions/50160/scripting-low-level-join-meshes-elements-hopefully-with-bmesh
    # https://blender.stackexchange.com/questions/188039/how-to-join-only-two-objects-to-create-a-new-object-using-python
    # https://blender.stackexchange.com/questions/23905/select-faces-depending-on-material
    def __process_bmesh(self, bm, mesh, geometry_data):
        self.__process_bmesh_faces(geometry_data, bm, mesh)
        helpers.ensure_bmesh(bm)
        self.__clean_bmesh(bm)

    def __process_bmesh_faces(self, geometry_data, bm, mesh):
        for face_data in geometry_data.face_data:
            verts = [bm.verts.new(face_data.matrix @ vertex) for vertex in face_data.vertices]
            face = bm.faces.new(verts)

            part_slopes = special_bricks.get_part_slopes(self.file.name)
            material = BlenderMaterials.get_material(face_data.color_code, part_slopes=part_slopes, texmap=face_data.texmap, pe_texmap=face_data.pe_texmap, use_backface_culling=self.bfc_certified)
            if material.name not in mesh.materials:
                mesh.materials.append(material)

            face.smooth = ImportOptions.shade_smooth
            face.material_index = mesh.materials.find(material.name)

            if face_data.texmap is not None:
                face_data.texmap.uv_unwrap_face(bm, face)

            if face_data.pe_texmap is not None:
                face_data.pe_texmap.uv_unwrap_face(bm, face)

    @staticmethod
    def __clean_bmesh(bm):
        if ImportOptions.remove_doubles:
            # TODO: if vertices in sharp edge collection, do not add to merge collection
            bmesh.ops.remove_doubles(bm, verts=bm.verts[:], dist=ImportOptions.merge_distance)

        # recalculate_normals completely overwrites any bfc processing
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

    def __process_bmesh_edges(self, key, bm, geometry_data):
        kd = self.__build_kd(bm)

        # increase the distance to look for edges to merge
        # merge line type 2 edges at a greater distance than mesh edges
        # the rounded part in the seat of 4079.dat has a gap just wide
        # enough that 2x isn't enough
        distance = ImportOptions.merge_distance
        distance = ImportOptions.merge_distance * 2.1

        e_edges, e_faces, e_verts, edge_indices = self.__build_edge_data(geometry_data, kd, distance)
        self.__create_edge_mesh(key, e_edges, e_faces, e_verts)
        self.__remove_bmesh_doubles(bm, edge_indices, distance)

    @staticmethod
    def __build_edge_data(geometry_data, kd, distance):
        e_verts = []
        e_edges = []
        e_faces = []

        # Create edge_indices dictionary, which is the list of edges as pairs of indices into our verts array
        edge_indices = set()

        i = 0
        for edge_data in geometry_data.edge_data:
            edge_verts = []
            face_indices = []
            for vertex in edge_data.vertices:
                vert = edge_data.matrix @ vertex
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

    def __process_top_object(self, mesh, accum_matrix, color_code, collection):
        obj = bpy.data.objects.new(mesh.name, mesh)
        obj[strings.ldraw_filename_key] = self.file.name
        obj[strings.ldraw_color_code_key] = color_code

        # bpy.context.space_data.shading.color_type = 'MATERIAL'
        # bpy.context.space_data.shading.color_type = 'OBJECT'
        # Shading > Color > Object to see object colors
        color = LDrawColor.get_color(color_code)
        obj.color = color.color_a

        ldraw_props.set_props(self, obj, color_code)

        self.__process_top_object_matrix(obj, accum_matrix)
        self.__process_top_object_gap(obj)
        self.__process_top_object_edges(obj)

        self.__meta_step(obj)

        self.__link_obj_to_collection(collection, obj)
        return obj

    @staticmethod
    def __process_top_object_matrix(obj, accum_matrix):
        transform_matrix = LDrawNode.__rotation @ LDrawNode.__import_scale_matrix
        if ImportOptions.parent_to_empty:
            if LDrawNode.top_empty is None:
                LDrawNode.top_empty = bpy.data.objects.new(LDrawNode.top_collection.name, None)
                group.link_obj(LDrawNode.top_collection, LDrawNode.top_empty)

            LDrawNode.top_empty.matrix_world = transform_matrix
            obj.matrix_world = accum_matrix
            obj.parent = LDrawNode.top_empty  # must be after matrix_world set or else transform is incorrect
        else:
            matrix_world = transform_matrix @ accum_matrix
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
                    group.link_obj(cls.top_collection, cls.__gap_scale_empty)
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

    def __create_edge_mesh(self, key, e_edges, e_faces, e_verts):
        if ImportOptions.import_edges:
            edge_key = f"e_{key}"
            edge_mesh = bpy.data.meshes.new(edge_key)
            edge_mesh.name = edge_key
            edge_mesh[strings.ldraw_filename_key] = self.file.name

            edge_mesh.from_pydata(e_verts, e_edges, e_faces)
            helpers.finish_mesh(edge_mesh)

            if ImportOptions.make_gaps and ImportOptions.gap_target == "mesh":
                edge_mesh.transform(self.__gap_scale_matrix)

    def __process_top_edges(self, key, obj, color_code, collection):
        if ImportOptions.import_edges:
            edge_key = f"e_{key}"
            edge_mesh = bpy.data.meshes[edge_key]
            edge_obj = bpy.data.objects.new(edge_mesh.name, edge_mesh)
            edge_obj[strings.ldraw_filename_key] = f"{self.file.name}_edges"
            edge_obj[strings.ldraw_color_code_key] = color_code

            color = LDrawColor.get_color(color_code)
            edge_obj.color = color.edge_color_d

            self.__meta_step(edge_obj)

            self.__link_obj_to_collection(collection, edge_obj)

            edge_obj.parent = obj
            edge_obj.matrix_world = obj.matrix_world

    @classmethod
    def __link_obj_to_collection(cls, collection, obj):
        group.link_obj(collection, obj)

        if cls.__current_step_group is not None:
            group.link_obj(cls.__current_step_group, obj)

        if ImportOptions.meta_group:
            if cls.__next_collection is not None:
                group.link_obj(cls.__next_collection, obj)
            else:
                collection_name = 'Ungrouped'
                host_collection = cls.__groups_collection
                c = group.get_collection(collection_name, host_collection)
                group.link_obj(c, obj)

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
            host_collection = bpy.context.scene.collection
            parts_collection = group.get_collection(collection_name, host_collection)

            collection_name = f"Step {str(cls.__current_step)}"
            host_collection = parts_collection
            c = group.get_collection(collection_name, host_collection)
            cls.__current_step_group = c

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

    def __meta_print(self, child_node):
        if ImportOptions.meta_print_write:
            print(child_node.meta_args)

    def __meta_group(self, child_node):
        if ImportOptions.meta_group:
            if child_node.meta_command == "group_def":
                child_node.__meta_group_def()
            elif child_node.meta_command == "group_nxt":
                child_node.__meta_group_nxt()
            elif child_node.meta_command == "group_begin":
                child_node.__meta_group_begin()
            elif child_node.meta_command == "group_end":
                child_node.__meta_group_end()

    def __meta_group_def(self):
        LDrawNode.__collection_id_map[self.meta_args["id"]] = self.meta_args["name"]
        collection_name = LDrawNode.__collection_id_map[self.meta_args["id"]]
        host_collection = LDrawNode.__groups_collection
        group.get_collection(collection_name, host_collection)

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
        host_collection = LDrawNode.__groups_collection
        c = group.get_collection(collection_name, host_collection)
        LDrawNode.__next_collection = c

        if len(LDrawNode.__next_collections) > 0:
            collection = LDrawNode.__next_collection
            host_collection = LDrawNode.__next_collections[-1]
            group.link_child(collection, host_collection)

    @classmethod
    def __meta_group_end(cls):
        if len(cls.__next_collections) > 0:
            cls.__next_collection = cls.__next_collections.pop()
        else:
            cls.__next_collection = None

    def __meta_leocad_camera(self, child_node, matrix):
        clean_line = child_node.line
        _params = helpers.get_params(clean_line, "0 !LEOCAD CAMERA ")

        if self.camera is None:
            self.camera = LDrawCamera()

        # https://www.leocad.org/docs/meta.html
        # "Camera commands can be grouped in the same line"
        # _params = _params[1:] at the end bumps promotes _params[2] to _params[1]
        while len(_params) > 0:
            if _params[0] == "fov":
                self.camera.fov = float(_params[1])
                _params = _params[2:]
            elif _params[0] == "znear":
                self.camera.z_near = float(_params[1])
                _params = _params[2:]
            elif _params[0] == "zfar":
                self.camera.z_far = float(_params[1])
                _params = _params[2:]
            elif _params[0] == "position":
                (x, y, z) = map(float, _params[1:4])
                vector = mathutils.Vector((x, y, z))
                self.camera.position = vector
                _params = _params[4:]
            elif _params[0] == "target_position":
                (x, y, z) = map(float, _params[1:4])
                vector = mathutils.Vector((x, y, z))
                self.camera.target_position = vector
                _params = _params[4:]
            elif _params[0] == "up_vector":
                (x, y, z) = map(float, _params[1:4])
                vector = mathutils.Vector((x, y, z))
                self.camera.up_vector = vector
                _params = _params[4:]
            elif _params[0] == "orthographic":
                self.camera.orthographic = True
                _params = _params[1:]
            elif _params[0] == "hidden":
                self.camera.hidden = True
                _params = _params[1:]
            elif _params[0] == "name":
                # "0 !LEOCAD CAMERA NAME Camera  2".split("NAME ")[1] => "Camera  2"
                # "NAME Camera  2".split("NAME ")[1] => "Camera  2"
                name_args = clean_line.split("NAME ")
                self.camera.name = name_args[1]

                # By definition this is the last of the parameters
                _params = []

                LDrawNode.cameras.append(self.camera)
                self.camera = None
            else:
                _params = _params[1:]

    # https://www.ldraw.org/documentation/ldraw-org-file-format-standards/language-extension-for-texture-mapping.html
    def __meta_texmap(self, child_node, matrix):
        clean_line = child_node.line

        if self.texmap_start:
            if clean_line == "0 !TEXMAP FALLBACK":
                self.texmap_fallback = True
            elif clean_line == "0 !TEXMAP END":
                self.__set_texmap_end()
        elif clean_line.startswith("0 !TEXMAP START ") or clean_line.startswith("0 !TEXMAP NEXT "):
            if clean_line.startswith("0 !TEXMAP START "):
                self.texmap_start = True
            elif clean_line.startswith("0 !TEXMAP NEXT "):
                self.texmap_next = True
            self.texmap_fallback = False

            method = clean_line.split()[3]

            new_texmap = TexMap(method=method)
            if new_texmap.is_planar():
                _params = clean_line.split(maxsplit=13)  # planar

                (x1, y1, z1, x2, y2, z2, x3, y3, z3) = map(float, _params[4:13])

                texture_params = helpers.parse_csv_line(_params[13], 2)
                texture = texture_params[0]
                glossmap = texture_params[1]
                if glossmap == '':
                    glossmap = None

                new_texmap.parameters = [
                    matrix @ mathutils.Vector((x1, y1, z1)),
                    matrix @ mathutils.Vector((x2, y2, z2)),
                    matrix @ mathutils.Vector((x3, y3, z3)),
                ]
                new_texmap.texture = texture
                new_texmap.glossmap = glossmap
            elif new_texmap.is_cylindrical():
                _params = clean_line.split(maxsplit=14)  # cylindrical

                (x1, y1, z1, x2, y2, z2, x3, y3, z3, a) = map(float, _params[4:14])

                texture_params = helpers.parse_csv_line(_params[14], 2)
                texture = texture_params[0]
                glossmap = texture_params[1]
                if glossmap == '':
                    glossmap = None

                new_texmap.parameters = [
                    matrix @ mathutils.Vector((x1, y1, z1)),
                    matrix @ mathutils.Vector((x2, y2, z2)),
                    matrix @ mathutils.Vector((x3, y3, z3)),
                    a,
                ]
                new_texmap.texture = texture
                new_texmap.glossmap = glossmap
            elif new_texmap.is_spherical():
                _params = clean_line.split(maxsplit=15)  # spherical

                (x1, y1, z1, x2, y2, z2, x3, y3, z3, a, b) = map(float, _params[4:15])

                texture_params = helpers.parse_csv_line(_params[15], 2)
                texture = texture_params[0]
                glossmap = texture_params[1]
                if glossmap == '':
                    glossmap = None

                new_texmap.parameters = [
                    matrix @ mathutils.Vector((x1, y1, z1)),
                    matrix @ mathutils.Vector((x2, y2, z2)),
                    matrix @ mathutils.Vector((x3, y3, z3)),
                    a,
                    b,
                ]
                new_texmap.texture = texture
                new_texmap.glossmap = glossmap

            if self.texmap is not None:
                self.texmaps.append(self.texmap)
            self.texmap = new_texmap

    def __set_texmap_end(self):
        try:
            self.texmap = self.texmaps.pop()
        except IndexError as e:
            self.texmap = None

        self.texmap_start = False
        self.texmap_next = False
        self.texmap_fallback = False

    # -1 is this file
    # >= 0 is the nth geometry line where n = PE_TEX_PATH
    def __meta_pe_tex_path(self, child_node):
        clean_line = child_node.line
        _params = clean_line.split()

        pe_tex_path = int(_params[2])

        # if there are two pe_tex_paths, the second one is the subfile_line_index in that file
        try:
            pe_tex_path_1 = int(_params[2])
        except IndexError as e:
            pe_tex_path_1 = None

        self.current_pe_tex_path = pe_tex_path

    # PE_TEX_INFO bse64_str uses the file's uvs
    # PE_TEX_INFO x,y,z,a,b,c,d,e,f,g,h,i,bl/tl,tr/br is matrix and plane coordinates for uv calculations
    # if no matrix, identity @ rotation?
    def __meta_pe_tex_info(self, child_node, matrix):
        if self.current_pe_tex_path is None:
            return

        clean_line = child_node.line
        _params = clean_line.split()

        pe_tex_info = PETexInfo()
        base64_str = None
        if len(_params) == 3:  # this tex_info applies to
            base64_str = _params[2]
        elif len(_params) == 19:
            base64_str = _params[18]
            (x, y, z, a, b, c, d, e, f, g, h, i, bl_x, bl_y, tr_x, tr_y) = map(float, _params[2:18])
            matrix = mathutils.Matrix((
                (a, b, c, x),
                (d, e, f, y),
                (g, h, i, z),
                (0, 0, 0, 1)
            ))
            bl = mathutils.Vector((bl_x, bl_y))
            tr = mathutils.Vector((tr_x, tr_y))

            pe_tex_info.matrix = matrix
            pe_tex_info.v1 = bl
            pe_tex_info.v2 = tr

        if base64_str is None:
            return

        from . import base64_handler
        image = base64_handler.named_png_from_base64_str(f"{self.file.name}_{self.current_pe_tex_path}.png", base64_str)

        pe_tex_info.image = image.name

        self.pe_tex_infos[self.current_pe_tex_path] = pe_tex_info

        if self.current_pe_tex_path == -1:
            self.pe_tex_info = self.pe_tex_infos[self.current_pe_tex_path]
        self.current_pe_tex_path = None

    def __meta_subfile(self, child_node, color_code, matrix, geometry_data, collection, accum_cull=True, accum_invert=False):
        # if we have a pe_tex_info, but no pe_tex meta commands have been parsed
        # treat the pe_tex_info as the one to use
        # custom minifig head > 3626tex.dat (has no pe_tex) > 3626texshell.dat
        if len(self.pe_tex_infos) < 1 and self.pe_tex_info is not None:
            pe_tex_info = self.pe_tex_info
        else:
            pe_tex_info = self.pe_tex_infos.get(self.subfile_line_index)

        child_node.load(
            color_code=color_code,
            parent_matrix=matrix,
            geometry_data=geometry_data,
            parent_collection=collection,
            accum_cull=accum_cull,
            accum_invert=accum_invert,
            texmap=self.texmap,
            pe_tex_info=pe_tex_info,
        )

        self.subfile_line_index += 1
        self.__meta_root_group_nxt(child_node)

    def __meta_edge(self, child_node, color_code, matrix, geometry_data):
        vertices = child_node.meta_args

        geometry_data.add_edge_data(
            color_code=color_code,
            vertices=vertices,
            matrix=matrix,
        )

    def __meta_face(self, child_node, color_code, matrix, geometry_data, winding):
        clean_line = child_node.line
        _params = clean_line.split()

        vertices = child_node.meta_args
        vert_count = len(vertices)

        pe_texmap = None
        if self.pe_tex_info is not None:
            # if we have uv data and a pe_tex_info, otherwise pass
            # # custom minifig head > 3626tex.dat (has no pe_tex) > 3626texpole.dat (has no uv data)
            if len(_params) > 14:
                pe_texmap = PETexmap()
                pe_texmap.texture = self.pe_tex_info.image
                if vert_count == 3:
                    for i in range(vert_count):
                        x = round(float(_params[i * 2 + 11]), 3)
                        y = round(float(_params[i * 2 + 12]), 3)
                        uv = mathutils.Vector((x, y))
                        pe_texmap.uvs.append(uv)
                elif vert_count == 4:
                    for i in range(vert_count):
                        x = round(float(_params[i * 2 + 13]), 3)
                        y = round(float(_params[i * 2 + 14]), 3)
                        uv = mathutils.Vector((x, y))
                        pe_texmap.uvs.append(uv)

        # https://github.com/rredford/LdrawToObj/blob/802924fb8d42145c4f07c10824e3a7f2292a6717/LdrawData/LdrawToData.cs
        if winding == "CCW":
            pass
        elif winding == "CW":
            if vert_count == 3:
                vertices = [vertices[0], vertices[2], vertices[1]]
            elif vert_count == 4:
                vertices = [vertices[0], vertices[3], vertices[2], vertices[1]]

        geometry_data.add_face_data(
            color_code=color_code,
            vertices=vertices,
            matrix=matrix,
            texmap=self.texmap,
            pe_texmap=pe_texmap,
        )

    def __meta_line(self, child_node, color_code, matrix, geometry_data):
        vertices = child_node.meta_args

        geometry_data.add_line_data(
            color_code=color_code,
            vertices=vertices,
            matrix=matrix,
        )
