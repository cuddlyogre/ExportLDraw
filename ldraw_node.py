import uuid
import mathutils

from .geometry_data import GeometryData
from .import_options import ImportOptions
from .pe_texmap import PETexInfo
from . import base64_handler
from . import group
from . import ldraw_mesh
from . import ldraw_object
from . import ldraw_meta
from . import matrices


class LDrawNode:
    """
    A line of a file that has been processed into something usable.
    """

    part_count = 0
    current_filename = ""
    current_model_filename = ""

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
        self.meta_command = None
        self.meta_args = {}

    def load(self,
             color_code="16",
             parent_matrix=None,
             accum_matrix=None,
             geometry_data=None,
             accum_cull=True,
             accum_invert=False,
             bfc_certified=None,
             parent_collection=None,
             return_mesh=False,
             texmaps=None,
             texmap=None,
             texmap_start=False,
             texmap_next=False,
             texmap_fallback=False,
             pe_tex_infos=None,
             ):

        if texmaps is None:
            texmaps = []

        if pe_tex_infos is None:
            pe_tex_infos = {}

        pe_tex_info = pe_tex_infos.get(None)

        if self.file.is_edge_logo() and not ImportOptions.display_logo:
            return
        if self.file.is_stud() and ImportOptions.no_studs:
            return

        LDrawNode.current_filename = self.file.name

        # keep track of the matrix and color up to this point
        # parent_matrix is the previous level's transform
        # current_matrix is the matrix up to this point and used for placement of objects
        # accum_matrix is every transform up to this point
        # child_matrix is what is used to transform this level and set the parent transform of the next level
        parent_matrix = parent_matrix or matrices.identity_matrix
        accum_matrix = accum_matrix or matrices.identity_matrix

        matrix = self.matrix
        if self.is_root:
            matrix = matrix @ matrices.rotation_matrix

        current_matrix = parent_matrix @ matrix
        child_accum_matrix = accum_matrix @ current_matrix
        child_matrix = current_matrix

        # current_color_code is the color_code up to this point
        current_color_code = color_code

        # when a part is used on its own and also treated as a subpart like with a shortcut, the part will not render in the shortcut
        # geometry_data_key is essentially a list of attributes that are unique to parts that share the same file
        # texmap parts are defined as parts so it should be safe to exclude that from the key, but I'm including it anyway
        # pe_tex_info is defined like an mpd so multiple instances sharing the same part name will share the same texture unless it is included in the key
        # don't change the attributes of the child_nodes because that will affect other parts that use a given file
        # pass that information down to .load and modify geometry_data instead
        # the only thing unique about a geometry_data object is its filename, color, texmap, pe_tex_info
        geometry_data_key = LDrawNode.__build_key(self.file.name, color_code=current_color_code, texmap=texmap, pe_tex_info=pe_tex_info)

        # if there's no geometry_data and some part type, it's a top level part so start collecting geometry
        # there are occasions where files with part_type of model have geometry so you can't rely on its part_type
        # example: 10252 - 10252_towel.dat in 10252-1 - Volkswagen Beetle.mpd
        # sometimes a part will be a subpart, so you have to check if there's already geometry_data started, or else you'll create a new part
        # example: 3044.dat -> 3044b.dat
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

        top_part = geometry_data is None and self.file.is_like_part()
        top_model = geometry_data is None and self.file.is_like_model()

        merge_model = self.file.name == "10261 - candyflosscart.ldr"
        merge_model = False
        merge_model = top_model and merge_model

        part_model = self.file.is_like_stud()
        part_model = False
        top_part = top_part or part_model

        if top_part:
            LDrawNode.part_count += 1
            geometry_data = LDrawNode.geometry_datas.get(geometry_data_key)
            current_matrix = current_matrix @ matrices.reverse_rotation_matrix
            # clean up floating point errors
            for i in range(len(current_matrix)):
                for j in range(len(current_matrix[i])):
                    current_matrix[i][j] = round(current_matrix[i][j], 6)
                    # print(current_matrix[i][j])
            child_matrix = matrices.identity_matrix
        elif top_model:
            if merge_model:
                geometry_data = LDrawNode.geometry_datas.get(geometry_data_key)
                child_matrix = matrices.identity_matrix
            LDrawNode.current_model_filename = self.file.name

        if top_model or top_part:
            # creature_015_mangreengraysuitmustache.ldr is a BFC NOCERTIFY model which causes parts used by it to be NOCERTIFY everywhere
            # reset bfc for parts since they are what define the bfc state of their geometry
            accum_cull = True
            accum_invert = False
            bfc_certified = None

        collection = parent_collection
        if collection is None:
            collection = group.top_collection
            if top_model:
                collection = group.files_collection

        if top_model:
            collection = group.get_filename_collection(self.file.name, collection)

        # always process geometry_data if this is a subpart or there is no geometry_data
        # if geometry_data exists, this is a top level part that has already been processed so don't process this key again
        is_top = top_part or merge_model or part_model
        if not is_top or geometry_data is None:
            if is_top:
                geometry_data = GeometryData()

            local_cull = True
            winding = "CCW"
            invert_next = False

            current_pe_tex_info = None
            current_pe_tex_path = None
            subfile_line_index = 0

            for child_node in self.file.child_nodes:
                # PE_TEX_NEXT_SHEAR always comes before PE_TEX_INFO
                if not child_node.meta_command.startswith("pe_tex"):
                    current_pe_tex_info = None

                # texmap_fallback will only be true if ImportOptions.meta_texmap == True and you're on a fallback line
                # if ImportOptions.meta_texmap == False, it will always be False
                if child_node.meta_command in ["1", "2", "3", "4", "5"] and not texmap_fallback:
                    child_current_color = LDrawNode.__determine_color(color_code, child_node.color_code)

                    if child_node.meta_command == "1":
                        _pe_tex_infos = {}
                        if pe_tex_info is not None and pe_tex_info.matrix is None:
                            _pe_tex_infos[None] = pe_tex_info

                        for _pe_tex_info in pe_tex_infos.get(subfile_line_index, []):
                            if len(_pe_tex_info.tex_path) == 1:
                                _pe_tex_infos[None] = _pe_tex_info
                            else:
                                _pe_tex_info.tex_path = _pe_tex_info.tex_path[1:]
                                _pe_tex_infos.setdefault(_pe_tex_info.tex_path[0], [])
                                _pe_tex_infos[_pe_tex_info.tex_path[0]].append(_pe_tex_info)

                        child_node.load(
                            color_code=child_current_color,
                            parent_matrix=child_matrix,
                            accum_matrix=child_accum_matrix,
                            geometry_data=geometry_data,
                            accum_cull=bfc_certified and accum_cull and local_cull,
                            accum_invert=(accum_invert ^ invert_next),  # xor
                            bfc_certified=bfc_certified,
                            parent_collection=collection,
                            texmaps=texmaps,
                            texmap=texmap,
                            texmap_start=texmap_start,
                            texmap_next=texmap_next,
                            texmap_fallback=texmap_fallback,
                            pe_tex_infos=_pe_tex_infos,
                        )

                        # from testing Part Designer, only subfiles count
                        subfile_line_index += 1

                        ldraw_meta.meta_root_group_nxt(
                            ldraw_node=self,
                            child_node=child_node,
                        )
                    elif child_node.meta_command == "2":
                        ldraw_meta.meta_edge(
                            child_node=child_node,
                            color_code=child_current_color,
                            matrix=child_matrix,
                            geometry_data=geometry_data,
                        )
                    elif child_node.meta_command in ["3", "4"]:
                        _winding = None
                        if bfc_certified and accum_cull and local_cull:
                            _winding = winding

                        ldraw_meta.meta_face(
                            ldraw_node=self,
                            child_node=child_node,
                            color_code=child_current_color,
                            matrix=child_matrix,
                            geometry_data=geometry_data,
                            winding=_winding,
                            texmap=texmap,
                            pe_tex_info=pe_tex_info,
                        )
                    elif child_node.meta_command == "5":
                        ldraw_meta.meta_line(
                            child_node=child_node,
                            color_code=child_current_color,
                            matrix=child_matrix,
                            geometry_data=geometry_data,
                        )
                elif child_node.meta_command == "bfc":
                    # does it make sense for models to have bfc info? maybe if that model has geometry, but then it would be treated like a part
                    if ImportOptions.meta_bfc:
                        local_cull, winding, invert_next, bfc_certified = ldraw_meta.meta_bfc(
                            clean_line=child_node.line,
                            matrix=child_matrix,
                            local_cull=local_cull,
                            winding=winding,
                            invert_next=invert_next,
                            accum_invert=accum_invert,
                            bfc_certified=bfc_certified,
                        )
                elif child_node.meta_command == "texmap":
                    texmap, texmap_start, texmap_next, texmap_fallback = ldraw_meta.meta_texmap(
                        clean_line=child_node.line,
                        matrix=child_matrix,
                        texmaps=texmaps,
                        texmap=texmap,
                        texmap_start=texmap_start,
                        texmap_next=texmap_next,
                        texmap_fallback=texmap_fallback,
                    )
                elif child_node.meta_command.startswith("pe_tex_"):
                    # works
                    # 0 PE_TEX_PATH -1
                    # works
                    # 0 PE_TEX_PATH 0
                    # works
                    # 0 PE_TEX_PATH 0
                    # 0 PE_TEX_PATH -1
                    # !works
                    # 0 PE_TEX_PATH 0 1
                    # !works
                    # backside of studs have texture applied
                    # 3004pb062.dat
                    # 0 PE_TEX_PATH 0 0 2
                    # tex_paths = [0, 0, 2]
                    # tex_path = tex_paths.pop(0) -> 0
                    # if tex_path == subfile_line_index and len(tex_paths) > 1 pass tex_paths to child else, use tex_info for this file

                    # 0 PE_TEX_PATH ...
                    # 0 PE_TEX_NEXT_SHEAR -> optional
                    # 0 PE_TEX_INFO ...
                    if child_node.meta_command == "pe_tex_path":
                        clean_line = child_node.line
                        _params = clean_line.split()[2:]

                        current_pe_tex_info = PETexInfo()
                        current_pe_tex_info.tex_path = [int(x) for x in _params]
                    elif child_node.meta_command == "pe_tex_next_shear":
                        current_pe_tex_info.next_shear = True
                    elif child_node.meta_command == "pe_tex_info":
                        clean_line = child_node.line
                        _params = clean_line.split()[2:]

                        # if there is one or 17, use the last item as the image data
                        base64_str = _params[-1]
                        image = base64_handler.named_png_from_base64_str(f"{self.file.name}_{current_pe_tex_path}.png", base64_str)
                        current_pe_tex_info.image = image.name

                        # if there is 17, it defines the boundingbox
                        if len(_params) == 17:
                            # defines a bounding box and its transformation
                            # this doesn't work well with some very distorted texture applications
                            # this also may be where PE_TEX_NEXT_SHEAR comes in

                            (x, y, z, a, b, c, d, e, f, g, h, i) = map(float, _params[0:12])
                            matrix = mathutils.Matrix((
                                (a, b, c, x),
                                (d, e, f, y),
                                (g, h, i, z),
                                (0, 0, 0, 1)
                            ))

                            current_pe_tex_info.matrix = matrix.freeze()

                            point_min = mathutils.Vector((0, 0))
                            point_max = mathutils.Vector((0, 0))
                            point_min.x = float(_params[12])
                            point_min.y = float(_params[13])
                            point_max.x = float(_params[14])
                            point_max.y = float(_params[15])
                            point_diff = point_max - point_min

                            current_pe_tex_info.point_min = point_min.freeze()
                            current_pe_tex_info.point_max = point_max.freeze()
                            current_pe_tex_info.point_diff = point_diff.freeze()

                        tex_path = current_pe_tex_info.tex_path[0]
                        if tex_path == -1:
                            pe_tex_info = current_pe_tex_info
                        else:
                            pe_tex_infos.setdefault(tex_path, [])
                            pe_tex_infos[tex_path].append(current_pe_tex_info)
                else:
                    # these meta commands really only make sense if they are encountered at the model level
                    # these should never be encountered when geometry_data not None
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
                        ldraw_meta.meta_leocad_camera(child_node, child_matrix)

                if texmap_next:
                    texmap, texmap_start, texmap_next, texmap_fallback = ldraw_meta.set_texmap_end(texmaps)

                if child_node.meta_command != "bfc":
                    invert_next = False
                elif child_node.meta_command == "bfc" and child_node.meta_args["command"] != "INVERTNEXT":
                    invert_next = False

        if is_top:
            # geometry_data will not be None if this is a new mesh
            # geometry_data will be None if the mesh already exists
            if geometry_data_key not in LDrawNode.geometry_datas and geometry_data is not None:
                geometry_data.key = geometry_data_key
                geometry_data.file = self.file
                geometry_data.bfc_certified = bfc_certified
                LDrawNode.geometry_datas[geometry_data_key] = geometry_data
            geometry_data = LDrawNode.geometry_datas[geometry_data_key]

            obj_matrix = current_matrix

            if part_model:
                obj_matrix = matrix
                obj_matrix = parent_matrix
                obj_matrix = current_matrix
                obj_matrix = child_matrix
                obj_matrix = accum_matrix @ matrix

            # blender mesh data is unique also based on color
            # this means a geometry_data for a file is created only once, but a mesh is created for every color that uses that geometry_data
            key = geometry_data.key
            mesh = ldraw_mesh.create_mesh(key, geometry_data, color_code, return_mesh=return_mesh)
            if return_mesh:
                return mesh
            obj = ldraw_object.create_object(mesh, geometry_data, color_code, obj_matrix, collection)

            if ImportOptions.import_edges:
                edge_key = f"e_{geometry_data.key}"
                edge_mesh = ldraw_mesh.create_edge_mesh(edge_key, geometry_data)
                edge_obj = ldraw_object.create_edge_obj(edge_mesh, geometry_data, color_code, obj, collection)

            if group.end_next_collection:
                group.next_collection = None

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
    def __build_key(filename, color_code=None, texmap=None, pe_tex_info=None, matrix=None):
        _key = (filename, color_code,)

        if texmap is not None:
            _key += (texmap.method, texmap.texture,)

        if pe_tex_info is not None:
            _key += (pe_tex_info.image, str(uuid.uuid4()))

        if matrix is not None:
            _key += (matrix,)

        str_key = str(_key)
        if len(str_key) < 60:
            return str(str_key)

        key = LDrawNode.key_map.get(_key)
        if key is None:
            LDrawNode.key_map[_key] = str(uuid.uuid4())
            key = LDrawNode.key_map.get(_key)
        return key
