import os
import re
import mathutils
import uuid

from .import_options import ImportOptions
from .filesystem import FileSystem
from .ldraw_node import LDrawNode
from .ldraw_geometry import LDrawGeometry
from .texmap import TexMap
from .ldraw_colors import LDrawColor
from .ldraw_camera import LDrawCamera

from . import helpers
from . import ldraw_part_types


class LDrawFile:
    __file_lines_cache = {}
    __file_cache = {}
    __key_map = {}

    @classmethod
    def reset_caches(cls):
        cls.__file_lines_cache = {}
        cls.__file_cache = {}
        cls.__key_map = {}

    def __init__(self, filename):
        self.filepath = None
        self.filename = filename

        self.description = None
        self.name = os.path.basename(filename)
        self.author = None
        # default part_type of ldraw_file is None, which should mean "model" - see ldraw_part_types.model_types
        # it is far more likely that a part type will not be specified in models since they are are more likely
        # to be authored by a user outside of specifications
        self.part_type = None
        self.actual_part_type = None

        self.lines = []

        self.child_nodes = []
        self.geometry = LDrawGeometry()
        self.extra_child_nodes = None
        self.extra_geometry = None

        self.texmap_start = False
        self.texmap_next = False
        self.texmap_fallback = False

        self.camera = None

    def __str__(self):
        return "\n".join([
            f"filename: {self.filename}",
            f"description: {self.description}",
            f"name: {self.name}",
            f"author: {self.author}",
        ])

    @classmethod
    def read_color_table(cls):
        LDrawColor.reset_caches()

        """Reads the color values from the LDConfig.ldr file. For details of the
        LDraw color system see: http://www.ldraw.org/article/547"""

        if LDrawColor.use_alt_colors:
            filename = "LDCfgalt.ldr"
        else:
            filename = "LDConfig.ldr"

        ldraw_file = cls.get_file(filename)
        if ldraw_file is None:
            return

    @classmethod
    def get_file(cls, filename):
        filepath = None
        if filename not in cls.__file_lines_cache:
            # TODO: if missing, use a,b,c,etc parts if available
            filepath = FileSystem.locate(filename)
            if filepath is None:
                return None

            is_mpd = False
            no_file = False
            first_mpd_filename = None
            current_file = None
            try:
                with open(filepath, mode='r', encoding='utf-8') as file:
                    while True:
                        line = file.readline()
                        if not line:
                            break

                        clean_line = helpers.clean_line(line)
                        strip_line = line.strip()

                        if clean_line == "":
                            continue

                        if clean_line.startswith("0 FILE "):
                            if not is_mpd:
                                is_mpd = True

                            no_file = False

                            mpd_filename = strip_line.split(maxsplit=2)[2].lower()
                            if first_mpd_filename is None:
                                first_mpd_filename = mpd_filename

                            if current_file is not None:
                                cls.__file_lines_cache[current_file.filename] = current_file
                            current_file = cls(mpd_filename)
                        elif is_mpd:
                            if no_file:
                                continue

                            if clean_line.startswith("0 NOFILE"):
                                no_file = True
                                if current_file is not None:
                                    cls.__file_lines_cache[current_file.filename] = current_file
                                current_file = None

                            elif current_file is not None:
                                current_file.lines.append(line)
                        else:
                            if filename not in cls.__file_lines_cache:
                                cls.__file_lines_cache[filename] = cls(filename)
                            cls.__file_lines_cache[filename].lines.append(line)
                    if current_file is not None:
                        cls.__file_lines_cache[current_file.filename] = current_file
            except Exception as e:
                print(e)

            if first_mpd_filename is not None:
                filename = first_mpd_filename

        ldraw_file = cls(filename)
        ldraw_file.filepath = filepath
        ldraw_file.lines = cls.__file_lines_cache[filename].lines
        ldraw_file.__parse_file()
        # print(ldraw_file)
        return ldraw_file

    # create meta nodes when those commands affect the scene
    # process meta command in place if it only affects the file
    def __parse_file(self):
        for line in self.lines:
            clean_line = helpers.clean_line(line)
            strip_line = line.strip()

            if self.__line_name(clean_line, strip_line):
                continue

            if self.__line_author(clean_line, strip_line):
                continue

            if self.__line_part_type(clean_line, strip_line):
                continue

            if self.__line_color(clean_line):
                continue

            if self.__line_step(clean_line):
                continue

            if self.__line_save(clean_line):
                continue

            if self.__line_clear(clean_line):
                continue

            if self.__line_print(clean_line):
                continue

            if self.__line_ldcad(clean_line):
                continue

            if self.__line_leocad(clean_line):
                continue

            if self.__line_texmap(clean_line):
                continue

            if self.texmap_start:
                self.__texmap_start(clean_line)
                continue

            if not self.texmap_fallback:
                if self.__parse_geometry_line(clean_line):
                    continue

            # this goes last so that description will be properly detected
            if self.__line_comment(clean_line, strip_line):
                continue

        if self.extra_geometry is not None or self.extra_child_nodes is not None:
            self.__handle_extra_geometry()

    @staticmethod
    def __build_key(filename, extra=False):
        _key = []
        _key.append(filename)
        if extra:
            _key.append("extra")
        if TexMap.texmap is not None:
            _key.append(TexMap.texmap.id)
        _key = "_".join([str(k).lower() for k in _key])
        if _key not in LDrawFile.__key_map:
            LDrawFile.__key_map[_key] = str(uuid.uuid4())
        key = LDrawFile.__key_map[_key]
        return key

    def __line_name(self, clean_line, strip_line):
        if not clean_line.lower().startswith("0 Name: ".lower()):
            return False

        self.name = strip_line.split(maxsplit=2)[2]

        return True

    def __line_author(self, clean_line, strip_line):
        if not clean_line.lower().startswith("0 Author: ".lower()):
            return False

        self.author = strip_line.split(maxsplit=2)[2]

        return True

    def __line_part_type(self, clean_line, strip_line):
        if not (clean_line.startswith("0 !LDRAW_ORG ") or
                clean_line.startswith("0 LDRAW_ORG ") or
                clean_line.startswith("0 Official LCAD ") or
                clean_line.startswith("0 Unofficial ") or
                clean_line.startswith("0 Un-official ")):
            return False

        if clean_line.startswith("0 Official LCAD "):
            self.actual_part_type = strip_line.split(maxsplit=4)[3]
        else:
            self.actual_part_type = strip_line.split(maxsplit=3)[2]
        self.part_type = self.determine_part_type(self.actual_part_type)

        return True

    @staticmethod
    def __line_color(clean_line):
        if not clean_line.startswith("0 !COLOUR "):
            return False

        _params = helpers.get_params(clean_line, "0 !COLOUR ", lowercase=False)
        LDrawColor.parse_color(_params)

        return True

    def __line_step(self, clean_line):
        if not clean_line.startswith("0 STEP"):
            return False

        ldraw_node = LDrawNode()
        ldraw_node.line = clean_line
        ldraw_node.meta_command = "step"
        self.child_nodes.append(ldraw_node)

        return True

    def __line_save(self, clean_line):
        if not clean_line.startswith("0 SAVE"):
            return False

        ldraw_node = LDrawNode()
        ldraw_node.line = clean_line
        ldraw_node.meta_command = "save"
        self.child_nodes.append(ldraw_node)

        return True

    def __line_clear(self, clean_line):
        if not clean_line.startswith("0 CLEAR"):
            return False

        ldraw_node = LDrawNode()
        ldraw_node.line = clean_line
        ldraw_node.meta_command = "clear"
        self.child_nodes.append(ldraw_node)

        return True

    def __line_print(self, clean_line):
        if clean_line not in ["0 PRINT", "0 WRITE"]:
            return False

        ldraw_node = LDrawNode()
        ldraw_node.line = clean_line
        ldraw_node.meta_command = "print"
        ldraw_node.meta_args["message"] = clean_line.split(maxsplit=2)[2]
        self.child_nodes.append(ldraw_node)

        return True

    def __line_ldcad(self, clean_line):
        if not clean_line.startswith("0 !LDCAD "):
            return False

        if not self.__line_ldcad_group_def(clean_line):
            return False

        if not self.__line_ldcad_group_nxt(clean_line):
            return False

        return True

    def __line_ldcad_group_def(self, clean_line):
        if not clean_line.startswith("0 !LDCAD GROUP_DEF "):
            return False

        # http://www.melkert.net/LDCad/tech/meta
        _params = re.search(r"\S+\s+\S+\s+\S+\s+(\[.*\])\s+(\[.*\])\s+(\[.*\])\s+(\[.*\])\s+(\[.*\])", clean_line)
        ldraw_node = LDrawNode()
        ldraw_node.line = clean_line
        ldraw_node.meta_command = "group_def"
        id_args = re.search(r"\[(.*)=(.*)\]", _params[2])
        ldraw_node.meta_args["id"] = id_args[2]
        name_args = re.search(r"\[(.*)=(.*)\]", _params[4])
        ldraw_node.meta_args["name"] = name_args[2]
        self.child_nodes.append(ldraw_node)

        return True

    def __line_ldcad_group_nxt(self, clean_line):
        if not clean_line.startswith("0 !LDCAD GROUP_NXT "):
            return False

        _params = re.search(r"\S+\s+\S+\s+\S+\s+(\[.*\])\s+(\[.*\])", clean_line)
        ldraw_node = LDrawNode()
        ldraw_node.line = clean_line
        ldraw_node.meta_command = "group_nxt"
        id_args = re.search(r"\[(.*)=(.*)\]", _params[1])
        ldraw_node.meta_args["id"] = id_args[2]
        self.child_nodes.append(ldraw_node)

        return True

    def __line_leocad(self, clean_line):
        if not clean_line.startswith("0 !LEOCAD "):
            return False

        if not self.__line_leocad_group_begin(clean_line):
            return False

        if not self.__line_leocad_group_end(clean_line):
            return False

        if not self.__line_leocad_camera(clean_line):
            return False

        return True

    def __line_leocad_group_begin(self, clean_line):
        if not clean_line.startswith("0 !LEOCAD GROUP BEGIN "):
            return False

        # https://www.leocad.org/docs/meta.html
        name_args = clean_line.split(maxsplit=4)
        ldraw_node = LDrawNode()
        ldraw_node.line = clean_line
        ldraw_node.meta_command = "group_begin"
        ldraw_node.meta_args["name"] = name_args[4]
        self.child_nodes.append(ldraw_node)

        return True

    def __line_leocad_group_end(self, clean_line):
        if not clean_line.startswith("0 !LEOCAD GROUP END"):
            return False

        ldraw_node = LDrawNode()
        ldraw_node.line = clean_line
        ldraw_node.meta_command = "group_end"
        self.child_nodes.append(ldraw_node)

        return True

    def __line_leocad_camera(self, clean_line):
        if not clean_line.startswith("0 !LEOCAD CAMERA "):
            return False

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
            elif _params[0] in ["position", "target_position", "up_vector"]:
                (x, y, z) = map(float, _params[1:4])
                vector = mathutils.Vector((x, y, z))

                if _params[0] == "position":
                    self.camera.position = vector

                elif _params[0] == "target_position":
                    self.camera.target_position = vector

                elif _params[0] == "up_vector":
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

                LDrawCamera.cameras.append(self.camera)
                self.camera = None
            else:
                _params = _params[1:]

        return True

    def __line_texmap(self, clean_line):
        if not clean_line.startswith("0 !TEXMAP "):
            return False

        # https://www.ldraw.org/documentation/ldraw-org-file-format-standards/language-extension-for-texture-mapping.html
        _params = helpers.get_params(clean_line, "0 !TEXMAP ")

        if self.texmap_start:
            if _params[0].lower() in ["fallback"]:
                self.texmap_fallback = True
            elif _params[0].lower() in ["end"]:
                self.__set_texmap_end()
        elif _params[0].lower() in ["start", "next"]:
            if _params[0].lower() == "start":
                self.texmap_start = True
            elif _params[0].lower() == "next":
                self.texmap_next = True
            self.texmap_fallback = False

            new_texmap = None
            method = _params[1].lower()
            if method in ['planar']:
                _params = clean_line[len("0 !TEXMAP "):].split(maxsplit=11)  # planar

                (x1, y1, z1, x2, y2, z2, x3, y3, z3) = map(float, _params[2:11])

                texture_params = helpers.parse_csv_line(_params[11], 2)
                texture = texture_params[0]
                glossmap = texture_params[1]

                new_texmap = TexMap(
                    method=method,
                    parameters=[
                        mathutils.Vector((x1, y1, z1)),
                        mathutils.Vector((x2, y2, z2)),
                        mathutils.Vector((x3, y3, z3)),
                    ],
                    texture=texture,
                    glossmap=glossmap,
                )
            elif method in ['cylindrical']:
                _params = clean_line[len("0 !TEXMAP "):].split(maxsplit=12)  # cylindrical

                (x1, y1, z1, x2, y2, z2, x3, y3, z3, a) = map(float, _params[2:12])

                texture_params = helpers.parse_csv_line(_params[12], 2)
                texture = texture_params[0]
                glossmap = texture_params[1]

                new_texmap = TexMap(
                    method=method,
                    parameters=[
                        mathutils.Vector((x1, y1, z1)),
                        mathutils.Vector((x2, y2, z2)),
                        mathutils.Vector((x3, y3, z3)),
                        a,
                    ],
                    texture=texture,
                    glossmap=glossmap,
                )
            elif method in ['spherical']:
                _params = clean_line[len("0 !TEXMAP "):].split(maxsplit=13)  # spherical

                (x1, y1, z1, x2, y2, z2, x3, y3, z3, a, b) = map(float, _params[2:13])

                texture_params = helpers.parse_csv_line(_params[13], 2)
                texture = texture_params[0]
                glossmap = texture_params[1]

                new_texmap = TexMap(
                    method=method,
                    parameters=[
                        mathutils.Vector((x1, y1, z1)),
                        mathutils.Vector((x2, y2, z2)),
                        mathutils.Vector((x3, y3, z3)),
                        a,
                        b,
                    ],
                    texture=texture,
                    glossmap=glossmap,
                )

            if new_texmap is not None:
                if TexMap.texmap is not None:
                    TexMap.texmaps.append(TexMap.texmap)
                TexMap.texmap = new_texmap

        return True

    def __line_comment(self, clean_line, strip_line):
        if not clean_line.startswith("0"):
            return False

        if self.texmap_next:
            """"""
            # if 0 line and texmap next, error
            # also error
        elif clean_line.startswith("0 //"):
            """"""
        elif self.description is None:
            self.description = strip_line.split(maxsplit=1)[1]

        return True

    def __texmap_start(self, clean_line):
        if clean_line.startswith("0 !: "):
            # remove 0 !: from line so that it can be parsed like a normal line
            _clean_line = clean_line[len("0 !: "):].strip()
            self.__parse_geometry_line(_clean_line)
        else:
            self.__parse_geometry_line(clean_line)
        if self.texmap_next:
            self.__set_texmap_end()

    def __set_texmap_end(self):
        try:
            TexMap.texmap = TexMap.texmaps.pop()
        except Exception as e:
            TexMap.texmap = None

        self.texmap_start = False
        self.texmap_next = False
        self.texmap_fallback = False

    def __parse_geometry_line(self, clean_line):
        if self.__line_subfile(clean_line):
            return True
        if self.__line_geometry(clean_line):
            return True
        return False

    def __line_subfile(self, clean_line):
        _params = clean_line.split(maxsplit=14)
        if _params[0] != "1":
            return False

        color_code = _params[1]

        (x, y, z, a, b, c, d, e, f, g, h, i) = map(float, _params[2:14])
        matrix = mathutils.Matrix((
            (a, b, c, x),
            (d, e, f, y),
            (g, h, i, z),
            (0, 0, 0, 1)
        ))

        # matrix = mathutils.Matrix((
        #     (a, d, g, 0),
        #     (b, e, h, 0),
        #     (c, f, i, 0),
        #     (x, y, z, 1)
        # ))

        filename = _params[14].lower()

        # filename = "stud-logo.dat"
        # parts = filename.split(".") => ["stud-logo", "dat"]
        # name = parts[0] => "stud-logo"
        # name_parts = name.split('-') => ["stud", "logo"]
        # stud_name = name_parts[0] => "stud"
        # chosen_logo = special_bricks.chosen_logo => "logo5"
        # ext = parts[1] => "dat"
        # filename = f"{stud_name}-{chosen_logo}.{ext}" => "stud-logo5.dat"
        if ImportOptions.display_logo and filename in ldraw_part_types.stud_names:
            parts = filename.split('.')
            name = parts[0]
            name_parts = name.split('-')
            stud_name = name_parts[0]
            chosen_logo = ImportOptions.chosen_logo
            ext = parts[1]
            filename = f"{stud_name}-{chosen_logo}.{ext}"

        key = self.__build_key(filename)

        ldraw_file = LDrawFile.__file_cache.get(key)
        if ldraw_file is None:
            ldraw_file = LDrawFile.get_file(filename)
            if ldraw_file is None:
                return True
            LDrawFile.__file_cache[key] = ldraw_file

        if ImportOptions.no_studs and ldraw_file.is_like_stud():
            return True

        ldraw_node = LDrawNode()
        ldraw_node.line = clean_line
        ldraw_node.file = ldraw_file
        ldraw_node.color_code = color_code
        ldraw_node.matrix = matrix

        # if any line in a model file is a subpart, treat that model as a part,
        # otherwise subparts are not parsed correctly
        # if subpart found, create new LDrawNode with those subparts and add that to child_nodes
        if self.is_like_model() and (ldraw_file.is_subpart() or ldraw_file.is_primitive()):
            if self.extra_child_nodes is None:
                self.extra_child_nodes = []
            self.extra_child_nodes.append(ldraw_node)
        else:
            self.child_nodes.append(ldraw_node)
        return True

    def __line_geometry(self, clean_line):
        _params = clean_line.split(maxsplit=14)
        if _params[0] not in ["2", "3", "4", "5"]:
            return False

        # add geometry that is in a model or shortcut file to a file
        # object so that it will be parsed
        if self.is_like_model():
            if self.extra_geometry is None:
                self.extra_geometry = LDrawGeometry()
            self.extra_geometry.parse_face(_params, LDrawFile.__texmap)
        else:
            self.geometry.parse_face(_params, LDrawFile.__texmap)
        return True

    def __handle_extra_geometry(self):
        key = self.__build_key(self.filename, extra=True)
        if key not in LDrawFile.__file_cache:
            filename = f"{self.name}_extra"
            ldraw_file = LDrawFile(filename)
            ldraw_file.actual_part_type = "Extra_Data_Part"
            ldraw_file.part_type = self.determine_part_type(ldraw_file.actual_part_type)
            ldraw_file.child_nodes = (self.extra_child_nodes or [])
            ldraw_file.geometry = (self.extra_geometry or LDrawGeometry())
            LDrawFile.__file_cache[key] = ldraw_file
        ldraw_file = LDrawFile.__file_cache[key]
        ldraw_node = LDrawNode()
        ldraw_node.line = ""
        ldraw_node.file = ldraw_file
        self.child_nodes.append(ldraw_node)

    def is_configuration(self):
        return self.part_type in ldraw_part_types.configuration_types

    # this allows shortcuts to be split into their individual parts if desired
    def is_like_model(self):
        return self.is_model() or (ImportOptions.treat_shortcut_as_model and self.is_shortcut())

    def is_model(self):
        return self.part_type in ldraw_part_types.model_types

    def is_shortcut(self):
        return self.part_type in ldraw_part_types.shortcut_types

    def is_part(self):
        return self.part_type in ldraw_part_types.part_types

    def is_subpart(self):
        return self.part_type in ldraw_part_types.subpart_types

    def is_primitive(self):
        return self.part_type in ldraw_part_types.primitive_types

    def is_like_stud(self):
        return self.name.startswith("stud")

    def is_stud(self):
        return self.name in ldraw_part_types.stud_names

    def is_edge_logo(self):
        return self.name in ldraw_part_types.edge_logo_names

    def is_logo(self):
        return self.name in ldraw_part_types.logo_names

    # if there's a line type specified, determine what that type is
    @staticmethod
    def determine_part_type(actual_part_type):
        _actual_part_type = actual_part_type.lower()
        if "primitive" in _actual_part_type:
            return "primitive"
        elif "subpart" in _actual_part_type:
            return "subpart"
        elif "part" in _actual_part_type:
            return "part"
        elif "shortcut" in _actual_part_type:
            return "shortcut"
        elif "model" in _actual_part_type:
            return "model"
        elif "configuration" in _actual_part_type:
            return "configuration"
        return "part"
