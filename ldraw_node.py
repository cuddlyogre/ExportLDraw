import uuid

from . import group
from .geometry_data import GeometryData
from .import_options import ImportOptions
from . import helpers
from . import ldraw_mesh
from . import ldraw_object
from . import ldraw_meta
from . import matrices


class LDrawNode:
    """
    All of the data that makes up a part.
    """

    part_count = 0
    key_map = {}

    @classmethod
    def reset_caches(cls):
        cls.part_count = 0
        cls.key_map = {}

    @classmethod
    def import_setup(cls):
        ldraw_meta.meta_step()

    def __init__(self):
        self.is_root = False
        self.top = False
        self.file = None
        self.line = ""
        self.color_code = "16"
        self.matrix = matrices.identity_matrix
        self.vertices = []
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

    def load(self,
             parent_node=None,
             color_code="16",
             parent_matrix=None,
             geometry_data=None,
             accum_cull=True,
             accum_invert=False,
             parent_collection=None,
             texmap=None,
             pe_tex_info=None,
             ):

        if self.file.is_edge_logo() and not ImportOptions.display_logo:
            return
        if self.file.is_like_stud() and ImportOptions.no_studs:
            return

        if parent_matrix is None:
            parent_matrix = matrices.identity_matrix

        self.texmap = texmap
        self.pe_tex_info = pe_tex_info

        # by default, treat this as anything other than a top level part
        # obj_matrix is the matrix up to the point and used for placement of objects
        # vertex_matrix is the matrix that gets passed to subparts
        obj_matrix = (parent_matrix @ self.matrix).freeze()
        vertex_matrix = obj_matrix
        collection = parent_collection

        if group.top_collection is None:
            collection_name = self.file.name
            host_collection = group.get_scene_collection()
            collection = group.get_filename_collection(collection_name, host_collection)
            group.top_collection = collection

            collection_name = 'Parts'
            host_collection = group.top_collection
            collection = group.get_collection(collection_name, host_collection)
            group.parts_collection = collection

        if ImportOptions.meta_group:
            collection_name = 'Groups'
            host_collection = group.top_collection
            _collection = group.get_collection(collection_name, host_collection)
            group.groups_collection = _collection
            helpers.hide_obj(group.groups_collection)

            collection_name = 'Ungrouped'
            host_collection = group.top_collection
            _collection = group.get_collection(collection_name, host_collection)
            group.ungrouped_collection = _collection
            helpers.hide_obj(group.ungrouped_collection)

        # if it's a model, don't start collecting geometry
        # else if there's no geometry, start collecting geometry

        # if a file has geometry, treat it like a part
        # otherwise that geometry won't be rendered
        if self.file.is_like_model() and not self.file.has_geometry():
            # if parent_collection is not None, this is a nested model
            if parent_collection is not None:
                collection = group.get_filename_collection(self.file.name, parent_collection)
        elif geometry_data is None or ImportOptions.preserve_hierarchy:  # top-level part
            LDrawNode.part_count += 1
            self.top = True
            vertex_matrix = matrices.identity_matrix
            geometry_data = GeometryData()

        # parent_is_top
        # true == the parent node is a part
        # false == parent node is a model
        # when a part is used on its own and also treated as a subpart like with a shortcut, the part will not render in the shortcut
        key = LDrawNode.__build_key(self.file.name, color_code, vertex_matrix, accum_cull, accum_invert, parent_is_top=(parent_node and parent_node.top), texmap=texmap, pe_tex_info=pe_tex_info)

        if self.file.is_like_model():
            if self.file.has_geometry():
                self.bfc_certified = False
            else:
                self.bfc_certified = True
        else:
            self.bfc_certified = None

        local_cull = True
        winding = "CCW"
        invert_next = False

        mesh = ldraw_mesh.get_mesh(key)
        if mesh is None or ImportOptions.preserve_hierarchy:
            for child_node in self.file.child_nodes:
                if child_node.meta_command in ["1", "2", "3", "4", "5"] and not self.texmap_fallback:
                    current_color = LDrawNode.__determine_color(color_code, child_node.color_code)
                    if child_node.meta_command == "1":
                        # if we have a pe_tex_info, but no pe_tex meta commands have been parsed
                        # treat the pe_tex_info as the one to use
                        # custom minifig head > 3626tex.dat (has no pe_tex) > 3626texshell.dat
                        if len(self.pe_tex_infos) < 1 and self.pe_tex_info is not None:
                            pe_tex_info = self.pe_tex_info
                        else:
                            pe_tex_info = self.pe_tex_infos.get(self.subfile_line_index)

                        # TODO: preload file, return mesh.name and get mesh and merge that mesh with the current mesh
                        # may crash based on https://docs.blender.org/api/current/info_gotcha.html#help-my-script-crashes-blender
                        # but testing seems to indicate that adding to bpy.data.meshes does not change hash(mesh) value
                        child_node.load(
                            parent_node=self,
                            color_code=current_color,
                            parent_matrix=vertex_matrix if not ImportOptions.preserve_hierarchy else obj_matrix,
                            geometry_data=geometry_data,
                            accum_cull=self.bfc_certified and accum_cull and local_cull,
                            accum_invert=(accum_invert ^ invert_next),  # xor
                            parent_collection=collection,
                            texmap=self.texmap,
                            pe_tex_info=pe_tex_info,
                        )
                        # for node in child_node.load(
                        #         color_code=current_color,
                        #         parent_matrix=matrix if not ImportOptions.preserve_hierarchy else obj_matrix,
                        #         geometry_data=geometry_data,
                        #         accum_cull=self.bfc_certified and accum_cull and local_cull,
                        #         accum_invert=(accum_invert ^ invert_next),  # xor
                        #         parent_collection=collection,
                        #         texmap=self.texmap,
                        #         pe_tex_info=pe_tex_info,
                        # ):
                        #     yield node

                        self.subfile_line_index += 1
                        ldraw_meta.meta_root_group_nxt(self, child_node)
                    elif child_node.meta_command == "2":
                        ldraw_meta.meta_edge(
                            child_node,
                            current_color,
                            vertex_matrix,
                            geometry_data,
                        )
                    elif child_node.meta_command in ["3", "4"]:
                        _winding = None
                        if self.bfc_certified and accum_cull and local_cull:
                            _winding = winding

                        ldraw_meta.meta_face(
                            self,
                            child_node,
                            current_color,
                            vertex_matrix,
                            geometry_data,
                            _winding,
                        )
                    elif child_node.meta_command == "5":
                        ldraw_meta.meta_line(
                            child_node,
                            current_color,
                            vertex_matrix,
                            geometry_data,
                        )
                elif child_node.meta_command == "bfc":
                    if ImportOptions.meta_bfc:
                        local_cull, winding, invert_next = ldraw_meta.meta_bfc(self, child_node, vertex_matrix, local_cull, winding, invert_next, accum_invert)
                elif child_node.meta_command == "step":
                    ldraw_meta.meta_step()
                elif child_node.meta_command == "save":
                    ldraw_meta.meta_save()
                elif child_node.meta_command == "clear":
                    ldraw_meta.meta_clear()
                elif child_node.meta_command == "print":
                    ldraw_meta.meta_print(child_node)
                elif child_node.meta_command.startswith("group"):
                    ldraw_meta.meta_group(child_node)
                elif child_node.meta_command == "leocad_camera":
                    ldraw_meta.meta_leocad_camera(self, child_node, vertex_matrix)
                elif child_node.meta_command == "texmap":
                    ldraw_meta.meta_texmap(self, child_node, vertex_matrix)
                elif child_node.meta_command.startswith("pe_tex_"):
                    ldraw_meta.meta_pe_tex(self, child_node, vertex_matrix)

                if self.texmap_next:
                    ldraw_meta.set_texmap_end(self)

                if child_node.meta_command != "bfc":
                    invert_next = False
                elif child_node.meta_command == "bfc" and child_node.meta_args["command"] != "INVERTNEXT":
                    invert_next = False

        if self.top:
            obj = LDrawNode.__create_obj(self, key, geometry_data, obj_matrix, color_code, collection)

            # if LDrawNode.part_count == 1:
            #     raise BaseException("done")

            # yield obj
            return obj

    @staticmethod
    def __create_obj(ldraw_node, key, geometry_data, obj_matrix, color_code, collection):
        mesh = ldraw_mesh.create_mesh(ldraw_node, key, geometry_data)
        obj = ldraw_object.process_top_object(ldraw_node, mesh, key, obj_matrix, color_code, collection)
        return obj

    # set the working color code to this file's
    # color code if it isn't color code 16
    @staticmethod
    def __determine_color(parent_color_code, this_color_code):
        color_code = this_color_code
        if this_color_code == "16":
            color_code = parent_color_code
        return color_code

    # must include matrix, so that parts that are just mirrored versions of other parts
    # such as 32527.dat (mirror of 32528.dat) will render
    @staticmethod
    def __build_key(filename, color_code, matrix, accum_cull, accum_invert, parent_is_top=None, texmap=None, pe_tex_info=None):
        _key = (filename, color_code, matrix, accum_cull, accum_invert, parent_is_top,)
        if texmap is not None:
            _key += ((texmap.method, texmap.texture, texmap.glossmap),)
        if pe_tex_info is not None:
            _key += ((pe_tex_info.image, pe_tex_info.matrix, pe_tex_info.v1, pe_tex_info.v1),)

        key = LDrawNode.key_map.get(_key)
        if key is None:
            LDrawNode.key_map[_key] = str(uuid.uuid4())
            key = LDrawNode.key_map.get(_key)

        return key
