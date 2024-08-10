import mathutils

import os
import re

from .import_options import ImportOptions
from .filesystem import FileSystem
from .ldraw_node import LDrawNode
from .ldraw_color import LDrawColor
from . import base64_handler
from . import helpers
from . import ldraw_part_types
from . import texmap


class LDrawFile:
    """
    A file that has been loaded and its lines converted to header data and ldraw_nodes.
    """

    __unparsed_file_cache = {}
    __parsed_file_cache = {}

    @classmethod
    def reset_caches(cls):
        cls.__unparsed_file_cache.clear()
        cls.__parsed_file_cache.clear()

    def __init__(self, filename):
        self.filename = filename
        self.lines = []

        self.description = None
        self.name = os.path.basename(filename)
        self.author = None
        # default part_type of ldraw_file is None, which should mean "model" - see ldraw_part_types.model_types
        # it is far more likely that a part type will not be specified in models since they are more likely
        # to be authored by a user outside of specifications
        self.part_type = None
        self.actual_part_type = None
        self.optional_qualifier = None
        self.update_date = None
        self.license = None
        self.help = []
        self.category = []
        self.keywords = []
        self.cmdline = None
        self.history = []

        self.child_nodes = []
        self.geometry_commands = {}

        self.named = False

    def __str__(self):
        return "\n".join([
            f"filename: {self.filename}",
            f"description: {self.description}",
            f"name: {self.name}",
            f"author: {self.author}",
            f"part_type: {self.part_type}",
        ])

    @classmethod
    def read_color_table(cls):
        """Reads the color values from the LDConfig.ldr file. For details of the
        LDraw color system see: http://www.ldraw.org/article/547"""

        # if there is no LDCfgalt.ldr, look for LDConfig.ldr
        # the Stud.io library doesn't have LDCfgalt.ldr, so the default of use_alt_colors == True
        # might trip up the user because they'll get a bunch of invalid color errors
        alt_filename = "LDCfgalt.ldr"
        standard_filename = "LDConfig.ldr"

        if LDrawColor.use_alt_colors:
            filename = alt_filename
        else:
            filename = standard_filename

        ldraw_file = LDrawFile.get_file(filename)
        if filename == alt_filename and ldraw_file is None:
            ldraw_file = LDrawFile.get_file(standard_filename)

        # import all materials
        # from .blender_materials import BlenderMaterials
        # for line in ldraw_file.lines:
        #     clean_line = helpers.clean_line(line)
        #     if clean_line.startswith("0 !COLOUR "):
        #         color_code = LDrawColor.parse_color(clean_line)
        #         material = BlenderMaterials.get_material(color_code, easy_key=True)

        return ldraw_file

    @classmethod
    def get_file(cls, filename):
        ldraw_file = cls.__parsed_file_cache.get(filename)
        if ldraw_file is not None:
            return ldraw_file

        ldraw_file = cls.__unparsed_file_cache.get(filename)
        if ldraw_file is None:
            ldraw_file = cls.__load_file(filename)

        if ldraw_file is None:
            return ldraw_file

        ldraw_file.__parse_file()
        cls.__parsed_file_cache[filename] = ldraw_file
        return ldraw_file

    @classmethod
    def __load_file(cls, filename):
        filepath = FileSystem.locate(filename)
        if filepath is None:
            return None

        with open(filepath, 'r', encoding='utf-8') as file:
            return cls.__read_file(file, filename)

    @classmethod
    def __read_file(cls, file, filename):
        hit_not_blank_line = False
        is_mpd = None
        no_file = False
        first_mpd_filename = None
        current_file = None
        current_mpd_file = None
        current_data_filename = None
        current_data = None

        for line in file:
            clean_line = helpers.clean_line(line)
            strip_line = line.strip()

            if clean_line == "":
                continue

            # if we're working on a data block, keep adding to it
            # until we reach a line that is not is_texmap_line
            # at that point, process the data block
            if current_data_filename is not None:
                if texmap.is_texmap_line(clean_line):
                    if ImportOptions.meta_texmap:
                        try:
                            base64_data = texmap.clean_line(strip_line)
                            current_data.append(base64_data)
                        except IndexError as e:
                            print(e)
                            import traceback
                            print(traceback.format_exc())
                        continue
                else:
                    base64_handler.named_png_from_base64_str(current_data_filename, "".join(current_data))
                    current_data_filename = None
                    current_data = None

            is_file_line = clean_line.startswith("0 FILE ")
            is_nofile_line = clean_line.startswith("0 NOFILE")
            is_data_line = clean_line.startswith("0 !DATA ")
            is_mpd_line = is_file_line or is_data_line

            # if the first non-blank line is 0 FILE, this is an mpd
            if not hit_not_blank_line:
                is_mpd = is_mpd_line

            hit_not_blank_line = True

            # clean up texmap geometry line prefixes
            if ImportOptions.meta_texmap:
                line = texmap.clean_line(line)

            # not mpd -> regular ldr/dat file
            if not is_mpd:
                if current_file is None:
                    current_file = LDrawFile(filename)
                current_file.lines.append(line)
                continue

            if is_mpd_line:
                no_file = False

            if is_file_line:
                mpd_filename = strip_line.split(maxsplit=2)[2].lower()
                if first_mpd_filename is None:
                    first_mpd_filename = mpd_filename

                if current_mpd_file is not None:
                    cls.__unparsed_file_cache[current_mpd_file.filename] = current_mpd_file
                current_mpd_file = LDrawFile(mpd_filename)
                continue

            if is_nofile_line:
                no_file = True
                if current_mpd_file is not None:
                    cls.__unparsed_file_cache[current_mpd_file.filename] = current_mpd_file
                current_mpd_file = None
                continue

            if is_data_line:
                current_data_filename = strip_line.split(maxsplit=2)[2]
                current_data = []
                continue

            if no_file:
                continue

            if current_mpd_file is not None:
                current_mpd_file.lines.append(line)
                continue

        if current_data_filename is not None:
            base64_handler.named_png_from_base64_str(current_data_filename, "".join(current_data))
            current_data_filename = None
            current_data = None

        # last file in mpd will not be added to the file cache if it doesn't end in 0 NOFILE
        if current_mpd_file is not None:
            cls.__unparsed_file_cache[current_mpd_file.filename] = current_mpd_file

        if current_file is not None:
            cls.__unparsed_file_cache[current_file.filename] = current_file

        if first_mpd_filename is not None:
            filename = first_mpd_filename

        return cls.__unparsed_file_cache.get(filename)

    # create meta nodes when those commands affect the scene
    # process meta command in place if it only affects the file
    def __parse_file(self):
        for line in self.lines:
            try:
                clean_line = helpers.clean_line(line)
                strip_line = line.strip()

                if self.__line_description(strip_line): continue
                if self.__line_name(clean_line, strip_line): continue
                if self.__line_author(clean_line, strip_line): continue
                if self.__line_part_type(clean_line, strip_line): continue
                if self.__line_license(strip_line): continue
                if self.__line_help(strip_line): continue
                if self.__line_category(strip_line): continue
                if self.__line_keywords(strip_line): continue
                if self.__line_cmdline(strip_line): continue
                if self.__line_history(strip_line): continue
                if self.__line_comment(clean_line): continue
                if self.__line_color(clean_line): continue
                if self.__line_geometry(clean_line): continue
                if self.__line_subfile(clean_line, strip_line): continue
                if self.__line_bfc(clean_line, strip_line): continue
                if self.__line_step(clean_line): continue
                if self.__line_save(clean_line): continue
                if self.__line_clear(clean_line): continue
                if self.__line_print(clean_line): continue
                if self.__line_ldcad(clean_line): continue
                if self.__line_leocad(clean_line): continue
                if self.__line_texmap(clean_line): continue
                if self.__line_stud_io(clean_line): continue
            except Exception as e:
                print(e)
                import traceback
                print(traceback.format_exc())
                continue

    # always return false so that the rest of the line types are parsed even if this is true
    def __line_description(self, strip_line):
        if self.description is None:
            parts = strip_line.split(maxsplit=1)
            if len(parts) > 1:
                str = parts[1]
                self.description = str
        return False

    # name and author are allowed to be case insensitive
    # https://forums.ldraw.org/thread-23904-post-35984.html#pid35984
    def __line_name(self, clean_line, strip_line):
        if clean_line.lower().startswith("0 Name: ".lower()):
            if self.named:
                return True
            self.named = True
            self.name = strip_line.split(maxsplit=2)[2]
            return True
        return False

    def __line_author(self, clean_line, strip_line):
        if clean_line.lower().startswith("0 Author: ".lower()):
            self.author = strip_line.split(maxsplit=2)[2]
            return True
        return False

    def __line_part_type(self, clean_line, strip_line):
        in_part_type = False
        for date_type in ["ORIGINAL", "UPDATE"]:
            # print(strip_line)
            try:
                index = clean_line.index(date_type)
                date_string = clean_line[index:]
                parts = date_string.split(maxsplit=1)
                self.update_date = parts[1]
                clean_line = clean_line[0:index]
                in_part_type = True
            except ValueError as e:
                pass

        for optional_qualifier in ["Alias", "Physical_Colour", "Flexible_Section"]:
            try:
                index = strip_line.index(optional_qualifier)
                self.optional_qualifier = optional_qualifier
                clean_line = clean_line[0:index]
                in_part_type = True
            except ValueError as e:
                pass

        for part_type_prefix in ["0 !LDRAW_ORG ", "0 LDRAW_ORG "]:
            try:
                index = strip_line.index(part_type_prefix)
                parts = clean_line.split(maxsplit=2)
                self.actual_part_type = parts[2].strip()
                self.part_type = self.determine_part_type(self.actual_part_type)
                in_part_type = True
            except ValueError as e:
                pass

        for part_type_prefix in ["0 Unofficial ", "0 Un-official "]:
            try:
                index = strip_line.index(part_type_prefix)
                parts = clean_line.split(maxsplit=1)
                self.actual_part_type = parts[1].strip()
                self.part_type = self.determine_part_type(self.actual_part_type)
                in_part_type = True
            except ValueError as e:
                pass

        for part_type_prefix in ["0 Official LCAD "]:
            try:
                index = strip_line.index(part_type_prefix)
                parts = clean_line.split(maxsplit=4)
                self.actual_part_type = parts[3].strip()
                self.part_type = self.determine_part_type(self.actual_part_type)
                in_part_type = True
            except ValueError as e:
                pass

        if in_part_type:
            return True

        return False

    def __line_license(self, strip_line):
        if strip_line.startswith("0 !LICENSE "):
            self.license = strip_line.split(maxsplit=2)[2]
            return True
        return False

    def __line_help(self, strip_line):
        if strip_line.startswith("0 !HELP "):
            self.help.append(strip_line.split(maxsplit=2)[2])
            return True
        return False

    def __line_category(self, strip_line):
        if strip_line.startswith("0 !CATEGORY "):
            self.category.append(strip_line.split(maxsplit=2)[2])
            return True
        return False

    def __line_keywords(self, strip_line):
        if strip_line.startswith("0 !KEYWORDS "):
            self.keywords += strip_line.split(maxsplit=2)[2].split(',')
            return True
        return False

    def __line_cmdline(self, strip_line):
        if strip_line.startswith("0 !CMDLINE "):
            self.cmdline = strip_line.split(maxsplit=2)[2]
            return True
        return False

    def __line_history(self, strip_line):
        if strip_line.startswith("0 !HISTORY "):
            self.history.append(strip_line.split(maxsplit=4)[2:])
            return True
        return False

    def __line_comment(self, clean_line):
        if clean_line.startswith("0 //"):
            return True
        return False

    # TODO: add collection of colors specific to this file
    def __line_color(self, clean_line):
        if clean_line.startswith("0 !COLOUR "):
            if self.is_configuration():
                LDrawColor.parse_color(clean_line)
            else:
                # TODO: add this color to this file's colors
                # color = LDrawColor()
                # color.parse_color_params(clean_line)
                #  self.__colors[color.code] = color
                ...
            return True
        return False

    def __line_bfc(self, clean_line, strip_line):
        if strip_line.startswith("0 BFC "):
            ldraw_node = LDrawNode()
            ldraw_node.line = clean_line
            ldraw_node.meta_command = "bfc"
            ldraw_node.meta_args["command"] = strip_line.split(maxsplit=2)[2]
            self.child_nodes.append(ldraw_node)
            return True
        return False

    def __line_step(self, clean_line):
        if clean_line.startswith("0 STEP"):
            ldraw_node = LDrawNode()
            ldraw_node.line = clean_line
            ldraw_node.meta_command = "step"
            self.child_nodes.append(ldraw_node)
            return True
        return False

    def __line_save(self, clean_line):
        if clean_line.startswith("0 SAVE"):
            ldraw_node = LDrawNode()
            ldraw_node.line = clean_line
            ldraw_node.meta_command = "save"
            self.child_nodes.append(ldraw_node)
            return True
        return False

    def __line_clear(self, clean_line):
        if clean_line.startswith("0 CLEAR"):
            ldraw_node = LDrawNode()
            ldraw_node.line = clean_line
            ldraw_node.meta_command = "clear"
            self.child_nodes.append(ldraw_node)
            return True
        return False

    def __line_print(self, clean_line):
        if clean_line.startswith("0 PRINT ") or clean_line.startswith("0 WRITE "):
            ldraw_node = LDrawNode()
            ldraw_node.line = clean_line
            ldraw_node.meta_command = "print"
            ldraw_node.meta_args["message"] = clean_line.split(maxsplit=2)[2]
            self.child_nodes.append(ldraw_node)
            return True
        return False

    # http://www.melkert.net/LDCad/tech/meta
    def __line_ldcad(self, clean_line):
        if clean_line.startswith("0 !LDCAD GROUP_DEF "):
            ldraw_node = LDrawNode()
            ldraw_node.line = clean_line
            ldraw_node.meta_command = "group_def"

            # 0 !LDCAD GROUP_DEF [topLevel=true] [LID=119507361] [GID=FsMGcO9CYmY] [name=Group 12] [center=0 0 0]
            _params = re.search(r"\S+\s+\S+\s+\S+\s+(\[.*\])\s+(\[.*\])\s+(\[.*\])\s+(\[.*\])\s+(\[.*\])", clean_line)
            if not _params:
                return

            lid_str = _params[2]  # "[LID=119507361]"
            lid_args = re.search(r"\[(.*)=(.*)\]", lid_str)
            ldraw_node.meta_args["id"] = lid_args[2]  # "119507361"

            name_str = _params[4]  # "[name=Group 12]"
            name_args = re.search(r"\[(.*)=(.*)\]", name_str)
            ldraw_node.meta_args["name"] = name_args[2]  # "Group 12"

            center_str = _params[5]  # "[center=0 0 0]"
            name_args = re.search(r"\[(.*)=(.*)\]", center_str)
            center_str_val = name_args[2]  # "0 0 0"
            (x, y, z) = map(float, center_str_val.split())
            ldraw_node.meta_args["center"] = mathutils.Vector((x, y, z))

            self.child_nodes.append(ldraw_node)
            return True

        if clean_line.startswith("0 !LDCAD GROUP_NXT "):
            ldraw_node = LDrawNode()
            ldraw_node.line = clean_line
            ldraw_node.meta_command = "group_nxt"

            # 0 !LDCAD GROUP_NXT [ids=13016969] [nrs=-1]
            _params = re.search(r"\S+\s+\S+\s+\S+\s+(\[.*\])\s+(\[.*\])", clean_line)

            ids_str = _params[1]  # "[ids=13016969]"
            ids_args = re.search(r"\[(.*)=(.*)\]", ids_str)
            ldraw_node.meta_args["id"] = ids_args[2]  # "13016969"

            self.child_nodes.append(ldraw_node)
            return True
        return False

    # https://www.leocad.org/docs/meta.html
    def __line_leocad(self, clean_line):
        if clean_line.startswith("0 !LEOCAD GROUP BEGIN "):
            name_args = clean_line.split(maxsplit=4)
            ldraw_node = LDrawNode()
            ldraw_node.line = clean_line
            ldraw_node.meta_command = "group_begin"
            ldraw_node.meta_args["name"] = name_args[4]
            self.child_nodes.append(ldraw_node)
            return True

        if clean_line.startswith("0 !LEOCAD GROUP END"):
            ldraw_node = LDrawNode()
            ldraw_node.line = clean_line
            ldraw_node.meta_command = "group_end"
            self.child_nodes.append(ldraw_node)
            return True

        if clean_line.startswith("0 !LEOCAD CAMERA "):
            ldraw_node = LDrawNode()
            ldraw_node.line = clean_line
            ldraw_node.meta_command = "leocad_camera"
            self.child_nodes.append(ldraw_node)
            return True
        return False

    def __line_texmap(self, clean_line):
        if clean_line.startswith("0 !TEXMAP "):
            ldraw_node = LDrawNode()
            ldraw_node.line = clean_line
            ldraw_node.meta_command = "texmap"
            self.child_nodes.append(ldraw_node)
            return True
        return False

    def __line_stud_io(self, clean_line):
        if clean_line.startswith("0 PE_TEX_PATH "):
            ldraw_node = LDrawNode()
            ldraw_node.line = clean_line
            ldraw_node.meta_command = "pe_tex_path"
            self.child_nodes.append(ldraw_node)
            return True

        if clean_line.startswith("0 PE_TEX_INFO "):
            ldraw_node = LDrawNode()
            ldraw_node.line = clean_line
            ldraw_node.meta_command = "pe_tex_info"
            self.child_nodes.append(ldraw_node)
            return True

        # TODO: find out what this does
        if clean_line.startswith("0 PE_TEX_NEXT_SHEAR"):
            ldraw_node = LDrawNode()
            ldraw_node.line = clean_line
            ldraw_node.meta_command = "pe_tex_next_shear"
            self.child_nodes.append(ldraw_node)
            return True
        return False

    def __line_subfile(self, clean_line, strip_line):
        if clean_line.startswith("1 "):
            _params = clean_line.split(maxsplit=14)
            _sparams = strip_line.split(maxsplit=14)

            color_code = _params[1]

            (x, y, z, a, b, c, d, e, f, g, h, i) = map(float, _params[2:14])
            matrix = mathutils.Matrix((
                (a, b, c, x),
                (d, e, f, y),
                (g, h, i, z),
                (0, 0, 0, 1)
            ))

            # allows for extra spaces in the filename
            filename = _sparams[14].lower()

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
                chosen_logo = ImportOptions.chosen_logo_value()
                ext = parts[1]
                filename = f"{stud_name}-{chosen_logo}.{ext}"

            ldraw_file = LDrawFile.get_file(filename)
            if ldraw_file is None:
                return True

            ldraw_node = LDrawNode()
            ldraw_node.file = ldraw_file
            ldraw_node.line = clean_line
            ldraw_node.meta_command = "1"
            ldraw_node.color_code = color_code
            ldraw_node.matrix = matrix
            self.child_nodes.append(ldraw_node)

            if ldraw_file.is_geometry():
                self.geometry_commands.setdefault(_params[0], 0)
                self.geometry_commands[_params[0]] += 1

            return True
        return False

    def __line_geometry(self, clean_line):
        if (clean_line.startswith("2 ") or
                clean_line.startswith("3 ") or
                clean_line.startswith("4 ") or
                clean_line.startswith("5 ")):
            _params = clean_line.split()

            self.geometry_commands.setdefault(_params[0], 0)
            self.geometry_commands[_params[0]] += 1

            ldraw_node = LDrawNode()
            ldraw_node.line = clean_line
            ldraw_node.meta_command = _params[0]
            ldraw_node.color_code = _params[1]
            ldraw_node.vertices = self.__parse_face(_params)
            self.child_nodes.append(ldraw_node)
            return True
        return False

    @staticmethod
    def __parse_face(_params):
        line_type = _params[0]
        vert_count = 0
        if line_type == "2":
            vert_count = 2
        elif line_type == "3":
            vert_count = 3
        elif line_type == "4":
            vert_count = 4
        elif line_type == "5":
            # 1.148 26.114 -19.076
            # 6.9   25.8   -18.6
            # 0     26     -19
            # 2.121 26.44  -19.293
            vert_count = 4

        verts = []
        for i in range(vert_count):
            x = float(_params[i * 3 + 2])
            y = float(_params[i * 3 + 3])
            z = float(_params[i * 3 + 4])
            vertex = mathutils.Vector((x, y, z))
            verts.append(vertex)
        return verts

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

    # TODO: move to varaibles to prevent list lookups
    def is_configuration(self):
        return self.part_type in ldraw_part_types.configuration_types

    # this allows shortcuts to be split into their individual parts if desired
    def is_like_model(self):
        return self.is_model() or self.is_shortcut_model()

    def is_model(self):
        return self.part_type in ldraw_part_types.model_types

    def is_shortcut(self):
        return self.part_type in ldraw_part_types.shortcut_types

    def is_shortcut_model(self):
        return self.is_shortcut() and ImportOptions.treat_shortcut_as_model

    def is_shortcut_part(self):
        return self.is_shortcut() and not ImportOptions.treat_shortcut_as_model

    def is_part(self):
        return self.part_type in ldraw_part_types.part_types

    def is_like_part(self):
        return self.is_part() or self.is_shortcut_part() or self.has_geometry()

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

    def is_geometry(self):
        return self.is_subpart() or self.is_primitive()

    def has_geometry(self):
        return sum(self.geometry_commands.values()) > 0
