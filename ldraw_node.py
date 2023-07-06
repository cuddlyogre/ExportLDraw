import uuid

from .geometry_data import GeometryData
from .import_options import ImportOptions
from . import group
from . import helpers
from . import ldraw_mesh
from . import ldraw_object
from . import ldraw_meta
from . import matrices


class LDrawNode:
    """
    A line of a file that has been processed into something usable.
    """

    part_count = 0
    key_map = {}
    geometry_datas = {}

    @classmethod
    def reset_caches(cls):
        cls.part_count = 0
        cls.key_map.clear()
        cls.geometry_datas.clear()

    def __init__(self):
        self.is_root = False
        self.file = None
        self.line = ""
        self.color_code = "16"
        self.matrix = matrices.identity_matrix
        self.vertices = []
        self.bfc_certified = None
        self.meta_command = None
        self.meta_args = {}

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
        if self.file.is_stud() and ImportOptions.no_studs:
            return

        if parent_matrix is None:
            parent_matrix = matrices.identity_matrix

        self.texmap = texmap
        self.pe_tex_info = pe_tex_info

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

        # by default, treat this as anything other than a top level part
        # keep track of the matrix and color up to this point
        # if it's a top level part, obj_matrix is its global transformation
        # if it's anything else, vertex_matrix is what is used to tranform the vertices
        # obj_matrix is the matrix up to the point and used for placement of objects
        # vertex_matrix is the matrix that gets passed to subparts
        top = False
        vertex_matrix = (parent_matrix @ self.matrix).freeze()
        obj_matrix = vertex_matrix
        obj_color_code = color_code

        # when a part is used on its own and also treated as a subpart like with a shortcut, the part will not render in the shortcut
        # obj_key is essentially a list of attributes that are unique to parts that share the same file
        # texmap parts are defined as parts so it should be safe to exclude that from the key
        # pe_tex_info is defined like an mpd so mutliple instances sharing the same part name will share the same texture unless it is included in the key
        # the only thing unique about a geometry_data object is its filename and whether it has pe_tex_info
        geometry_data_key = LDrawNode.__build_key(self.file.name, pe_tex_info)
        # blender mesh data is unique also based on color
        # this means a geometry_data for a file is created only once, but a mesh is created for every color that uses that geometry_data
        obj_key = f"{geometry_data_key}_{color_code}"

        # if there's no geometry, it's a top level part so start collecting geometry
        # there are occasions where files with part_type of model have geometry so you can't rely on its part_type
        # example: 10252 - 10252_towel.dat in 10252-1 - Volkswagen Beetle.mpd
        # the only way to be sure is if a file has geometry, always treat it like a part otherwise that geometry won't be rendered
        # geometry_data is always None if the geometry_data with this key has already been processed
        # if is_shortcut_part, always treat like top level part, otherwise shortcuts that
        # are children of other shortcuts will be treated as top level parts won't be treated as top level parts
        # this allows the button on part u9158.dat to be its own separate object
        # this allows the horse's head on part 4493c04.dat to be its own object, as well as both halves of its body
        # TODO: force special parts to always be a top level part - such as the horse head or button
        #  in cases where they aren't part of a shortcut
        # TODO: is_shortcut_model splits 99141c01.dat and u9158.dat into its subparts -
        #  u9158.dat - ensure the battery contacts are correct
        cached_geometry_data = None
        if geometry_data is None and (self.file.has_geometry() or self.file.is_part() or self.file.is_shortcut_part()):
            # top-level part
            LDrawNode.part_count += 1
            top = True
            vertex_matrix = matrices.identity_matrix
            cached_geometry_data = LDrawNode.geometry_datas.get(geometry_data_key)
            # set top level parts to 16 so that geometry_data is only created once per filename
            # then change their 16 faces to obj_color_code
            # TODO: replace material of 16 faces with geometry nodes
            color_code = "16"
        else:
            if self.file.is_like_model():
                self.bfc_certified = True  # or else accum_cull will be false, which turns off bfc processing
                if parent_collection is not None:
                    # if parent_collection is not None, this is a nested model
                    collection = group.get_filename_collection(self.file.name, parent_collection)

        # always process geometry_data if this is a subpart or there is no cached_geometry_data
        # if geometry_data exists, this is a top level part that has already been processed so don't process this key again
        if not top or cached_geometry_data is None:
            if top:
                geometry_data = GeometryData()

            local_cull = True
            winding = "CCW"
            invert_next = False

            for child_node in self.file.child_nodes:
                # self.texmap_fallback will only be true if ImportOptions.meta_texmap == True and you're on a fallback line
                # if ImportOptions.meta_texmap == False, it will always be False
                if child_node.meta_command in ["1", "2", "3", "4", "5"] and not self.texmap_fallback:
                    child_current_color = LDrawNode.__determine_color(color_code, child_node.color_code)
                    if child_node.meta_command == "1":
                        # if we have a pe_tex_info, but no pe_tex meta commands have been parsed
                        # treat the pe_tex_info as the one to use
                        # custom minifig head > 3626tex.dat (has no pe_tex) > 3626texshell.dat
                        if len(self.pe_tex_infos) < 1 and self.pe_tex_info is not None:
                            pe_tex_info = self.pe_tex_info
                        else:
                            pe_tex_info = self.pe_tex_infos.get(self.subfile_line_index)

                        child_node.load(
                            color_code=child_current_color,
                            parent_matrix=vertex_matrix,
                            geometry_data=geometry_data,
                            accum_cull=self.bfc_certified and accum_cull and local_cull,
                            accum_invert=(accum_invert ^ invert_next),  # xor
                            parent_collection=collection,
                            texmap=self.texmap,
                            pe_tex_info=pe_tex_info,
                        )
                        # for node in child_node.load(
                        #         color_code=child_current_color,
                        #         parent_matrix=vertex_matrix,
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
                            child_current_color,
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
                            child_current_color,
                            vertex_matrix,
                            geometry_data,
                            _winding,
                        )
                    elif child_node.meta_command == "5":
                        ldraw_meta.meta_line(
                            child_node,
                            child_current_color,
                            vertex_matrix,
                            geometry_data,
                        )
                elif child_node.meta_command == "bfc":
                    if ImportOptions.meta_bfc:
                        local_cull, winding, invert_next = ldraw_meta.meta_bfc(self, child_node, vertex_matrix, local_cull, winding, invert_next, accum_invert)
                elif child_node.meta_command == "texmap":
                    ldraw_meta.meta_texmap(self, child_node, vertex_matrix)
                elif child_node.meta_command.startswith("pe_tex_"):
                    ldraw_meta.meta_pe_tex(self, child_node, vertex_matrix)
                else:
                    # these meta commands really only make sense if they are encountered at the model level
                    # these should never be encoutered when geometry_data not None
                    # so they should be processed every time they are hit
                    # as opposed to just once because they won't be cached
                    if child_node.meta_command == "step":
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
                        ldraw_meta.meta_leocad_camera(child_node, vertex_matrix)

                if self.texmap_next:
                    ldraw_meta.set_texmap_end(self)

                if child_node.meta_command != "bfc":
                    invert_next = False
                elif child_node.meta_command == "bfc" and child_node.meta_args["command"] != "INVERTNEXT":
                    invert_next = False

        if top:
            # geometry_data will not be None if this is a new mesh
            # geometry_data will be None if the mesh already exists
            cached_geometry_data = LDrawNode.geometry_datas.setdefault(geometry_data_key, geometry_data)
            obj = LDrawNode.__create_obj(self, obj_key, cached_geometry_data, obj_matrix, obj_color_code, collection)

            # if LDrawNode.part_count == 1:
            #     raise BaseException("done")

            # yield obj
            return obj

    @staticmethod
    def __create_obj(ldraw_node, key, geometry_data, matrix, color_code, collection):
        mesh = ldraw_mesh.create_mesh(ldraw_node, key, geometry_data, color_code)
        obj = ldraw_object.process_top_object(ldraw_node, mesh, key, matrix, color_code, collection)
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
    def __build_key(filename, color_code=None, pe_tex_info=None, matrix=None):
        _key = (filename, color_code,)

        if pe_tex_info is not None:
            _key += ((pe_tex_info.image, pe_tex_info.matrix, pe_tex_info.v1, pe_tex_info.v2),)
        else:
            _key += (None,)

        _key += (matrix,)

        key = LDrawNode.key_map.get(_key)
        if key is None:
            LDrawNode.key_map[_key] = str(uuid.uuid4())
            key = LDrawNode.key_map.get(_key)

        return key
