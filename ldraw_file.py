import os
import mathutils
import re

from . import options
from . import filesystem
from . import helpers
from . import ldraw_part_types

from .ldraw_node import LDrawNode
from .ldraw_geometry import LDrawGeometry
from .special_bricks import SpecialBricks
from .ldraw_colors import LDrawColors
from .ldraw_camera import LDrawCamera


class LDrawFile:
    mpd_file_cache = {}
    file_cache = {}

    def __init__(self, filepath):
        self.filepath = filepath
        self.name = ""
        self.child_nodes = []
        self.geometry = LDrawGeometry()
        self.part_type = None
        self.lines = []

    @staticmethod
    def reset_caches():
        LDrawFile.mpd_file_cache = {}
        LDrawFile.file_cache = {}

    def read_file(self):
        if self.filepath in LDrawFile.mpd_file_cache:
            self.lines = LDrawFile.mpd_file_cache[self.filepath].lines
        else:
            # if missing, use a,b,c etc parts if available
            # TODO: look in this file's directory and directories relative to this file's directory
            filepath = filesystem.locate(self.filepath)
            if filepath is None:
                print(f"missing {self.filepath}")
                return
            self.lines = filesystem.read_file(filepath)

    def parse_file(self):
        if len(self.lines) < 1:
            return

        ldraw_camera = None

        for line in self.lines:
            params = helpers.parse_line(line, 14)

            if params is None:
                continue

            if params[0] == "0":
                if params[1].lower() in ["!colour"]:
                    LDrawColors.parse_color(params)
                elif params[1].lower() in ["!ldraw_org"]:
                    if params[2].lower() in ["lcad"]:
                        self.part_type = params[3].lower()
                    else:
                        self.part_type = params[2].lower()
                elif params[1].lower() == "name:":
                    self.name = line[7:].lower().strip()
                elif params[1].lower() in ['step']:
                    if options.meta_step:
                        ldraw_node = LDrawNode(None)
                        ldraw_node.meta_command = params[1].lower()
                        self.child_nodes.append(ldraw_node)
                elif params[1].lower() in ['save']:
                    if options.meta_save:
                        ldraw_node = LDrawNode(None)
                        ldraw_node.meta_command = params[1].lower()
                        self.child_nodes.append(ldraw_node)
                elif params[1].lower() in ['clear']:
                    if options.meta_clear:
                        ldraw_node = LDrawNode(None)
                        ldraw_node.meta_command = params[1].lower()
                        self.child_nodes.append(ldraw_node)
                elif params[1].lower() in ['print', 'write']:
                    if options.meta_print_write:
                        print(line[7:].strip())
                elif params[1].lower() in ["!ldcad"]:  # http://www.melkert.net/LDCad/tech/meta
                    if params[2].lower() in ["group_def"]:
                        params = re.search(r".*?\s+.*?\s+.*?\s+(\[.*\])\s+(\[.*\])\s+(\[.*\])\s+(\[.*\])\s+(\[.*\])", line.strip())

                        # if params is None:
                        #     print(f"BAD LINE: {line}")
                        #     continue

                        ldraw_node = LDrawNode(None)
                        ldraw_node.meta_command = "group_def"

                        id_args = re.search(r"\[(.*)=(.*)\]", params[2])
                        ldraw_node.meta_args['id'] = id_args[2]

                        name_args = re.search(r"\[(.*)=(.*)\]", params[4])
                        ldraw_node.meta_args['name'] = name_args[2]

                        self.child_nodes.append(ldraw_node)
                    elif params[2].lower() in ["group_nxt"]:
                        params = re.search(r".*\s+.*\s+.*\s+(\[.*\])\s+(\[.*\])", line.strip())

                        # if params is None:
                        #     print(f"BAD LINE: {line}")
                        #     continue

                        ldraw_node = LDrawNode(None)
                        ldraw_node.meta_command = "group_nxt"

                        id_args = re.search(r"\[(.*)=(.*)\]", params[1])
                        ldraw_node.meta_args['id'] = id_args[2]

                        self.child_nodes.append(ldraw_node)
                elif params[1].lower() in ["!leocad"]:  # https://www.leocad.org/docs/meta.html
                    if params[2].lower() in ["group"]:
                        if params[3].lower() in ["begin"]:
                            # begin_params = re.search(r"(?:.*\s+){3}begin\s+(.*)", line, re.IGNORECASE)
                            begin_params = re.search(r".*?\s+.*?\s+.*?\s+.*?\s+(.*)", line.strip())

                            # if begin_params is None:
                            #     print(f"BAD LINE: {line}")
                            #     continue

                            if begin_params is not None:
                                ldraw_node = LDrawNode(None)
                                ldraw_node.meta_command = "group_begin"
                                ldraw_node.meta_args['name'] = begin_params[1]
                                self.child_nodes.append(ldraw_node)
                        elif params[3].lower() in ["end"]:
                            ldraw_node = LDrawNode(None)
                            ldraw_node.meta_command = "group_end"
                            self.child_nodes.append(ldraw_node)

                    elif params[2] == "CAMERA":
                        if ldraw_camera is None:
                            ldraw_camera = LDrawCamera()

                        params = params[3:]

                        # https://www.leocad.org/docs/meta.html
                        # "Camera commands can be grouped in the same line"
                        # params = params[1:] at the end bumps promotes params[2] to params[1]

                        while len(params) > 0:
                            if params[0] == "FOV":
                                ldraw_camera.fov = float(params[1])
                                params = params[2:]
                            elif params[0] == "ZNEAR":
                                scale = 1.0
                                ldraw_camera.z_near = scale * float(params[1])
                                params = params[2:]
                            elif params[0] == "ZFAR":
                                scale = 1.0
                                ldraw_camera.z_far = scale * float(params[1])
                                params = params[2:]
                            elif params[0] in ["POSITION", "TARGET_POSITION", "UP_VECTOR"]:
                                (x, y, z) = map(float, params[1:4])
                                vector = mathutils.Vector((x, y, z))

                                if params[0] == "POSITION":
                                    ldraw_camera.position = vector
                                    if options.debug_text:
                                        print("POSITION")
                                        print(ldraw_camera.position)
                                        print(ldraw_camera.target_position)
                                        print(ldraw_camera.up_vector)

                                elif params[0] == "TARGET_POSITION":
                                    ldraw_camera.target_position = vector
                                    if options.debug_text:
                                        print("TARGET_POSITION")
                                        print(ldraw_camera.position)
                                        print(ldraw_camera.target_position)
                                        print(ldraw_camera.up_vector)

                                elif params[0] == "UP_VECTOR":
                                    ldraw_camera.up_vector = vector
                                    if options.debug_text:
                                        print("UP_VECTOR")
                                        print(ldraw_camera.position)
                                        print(ldraw_camera.target_position)
                                        print(ldraw_camera.up_vector)

                                params = params[4:]

                            elif params[0] == "ORTHOGRAPHIC":
                                ldraw_camera.orthographic = True
                                params = params[1:]
                            elif params[0] == "HIDDEN":
                                ldraw_camera.hidden = True
                                params = params[1:]
                            elif params[0] == "NAME":
                                # camera_name_params = re.search(r"(?:.*\s+){3}name(.*)", line, re.IGNORECASE)
                                camera_name_params = re.search(r".*?\s+.*?\s+.*?\s+.*?\s+(.*)", line.strip())

                                # if camera_name_params is None:
                                #     print(f"BAD LINE: {line}")
                                #     continue

                                ldraw_camera.name = camera_name_params[1].strip()

                                # By definition this is the last of the parameters
                                params = []

                                LDrawCamera.add_camera(ldraw_camera)
                                ldraw_camera = None
                            else:
                                params = params[1:]
                else:
                    continue
                    # https://www.ldraw.org/documentation/ldraw-org-file-format-standards/language-extension-for-texture-mapping.html
                    if params[1].lower() in ["!texmap"]:
                        ldraw_node = LDrawNode(None)
                        ldraw_node.meta_command = params[1].lower()
                        ldraw_node.meta_args = params[2:]
                        self.child_nodes.append(ldraw_node)
                    elif params[1].lower() in ["!:"]:
                        self.parse_geometry_line(params[2:])
            else:
                self.parse_geometry_line(line, params)

        if self.name == "":
            self.name = os.path.basename(self.filepath)

    def parse_geometry_line(self, line, params):
        if params[0] == "1":
            self.parse_child_node(line, params)
        elif params[0] in ["2"]:
            if self.part_type is None:
                self.part_type = 'part'
            self.geometry.parse_edge(params)
        elif params[0] in ["3", "4"]:
            if self.part_type is None:
                self.part_type = 'part'
            self.geometry.parse_face(params)

    def parse_child_node(self, line, params):
        color_code = params[1]

        (x, y, z, a, b, c, d, e, f, g, h, i) = map(float, params[2:14])
        matrix = mathutils.Matrix((
            (a, b, c, x),
            (d, e, f, y),
            (g, h, i, z),
            (0, 0, 0, 1)
        ))

        # there might be spaces in the filename, so don't just split on whitespace
        # filename_args = re.search(r"(?:.*\s+){14}(.*)", line.strip())
        # print(line.strip())
        filename_args = re.search(r".*?\s+.*?\s+.*?\s+.*?\s+.*?\s+.*?\s+.*?\s+.*?\s+.*?\s+.*?\s+.*?\s+.*?\s+.*?\s+.*?\s+(.*)", line.strip())

        # if filename_args is None:
        #     print(f"BAD LINE: {line}")
        #     return

        filename = filename_args[1].lower()
        # filename = " ".join(params[14:]).lower()
        if options.display_logo:
            if filename in SpecialBricks.studs:
                parts = filename.split(".")
                name = parts[0]
                ext = parts[1]
                new_filename = f"{name}-{options.chosen_logo}.{ext}"
                if filesystem.locate(new_filename):
                    filename = new_filename
        key = []
        key.append(options.resolution)
        if options.display_logo:
            key.append(options.chosen_logo)
        if options.remove_doubles:
            key.append("rd")
        key.append(color_code)
        key.append(os.path.basename(filename))
        key = "_".join([k.lower() for k in key])
        key = re.sub(r"[^a-z0-9._]", "-", key)

        if key not in LDrawFile.file_cache:
            ldraw_file = LDrawFile(filename)
            ldraw_file.read_file()
            ldraw_file.parse_file()
            LDrawFile.file_cache[key] = ldraw_file
        ldraw_file = LDrawFile.file_cache[key]

        ldraw_node = LDrawNode(ldraw_file, color_code=color_code, matrix=matrix)
        self.child_nodes.append(ldraw_node)

        if self.part_type is None:
            if ldraw_node.file.part_type in ldraw_part_types.subpart_types:
                self.part_type = "part"

    @classmethod
    def handle_mpd(cls, filepath):
        ldraw_file = LDrawFile(filepath)
        ldraw_file.read_file()
        lines = ldraw_file.lines

        if len(lines) < 1:
            return None

        if not lines[0].lower().startswith("0 f"):
            return filepath

        root_file = None
        current_file = None
        for line in lines:
            params = helpers.parse_line(line, 9)

            if params is None:
                continue

            if params[0] == "0" and params[1].lower() == "file":
                cls.__parse_current_file(current_file)
                current_file = LDrawFile(line[7:].lower())

                if root_file is None:
                    root_file = line[7:].lower()

            elif params[0] == "0" and params[1].lower() == "nofile":
                cls.__parse_current_file(current_file)
                current_file = None

            else:
                if current_file is not None:
                    current_file.lines.append(line)

        cls.__parse_current_file(current_file)

        if root_file is not None:
            return root_file
        return filepath

    @classmethod
    def __parse_current_file(cls, ldraw_file):
        if ldraw_file is not None:
            cls.mpd_file_cache[ldraw_file.filepath] = ldraw_file

    @staticmethod
    # if this is in LDrawColors, ImportError: cannot import name 'LDrawColors' from 'ExportLdraw.ldraw_colors'
    # two files cannot refer to each other
    def read_color_table():
        LDrawColors.reset_caches()

        """Reads the color values from the LDConfig.ldr file. For details of the
        Ldraw color system see: http://www.ldraw.org/article/547"""

        if options.use_alt_colors:
            filepath = "LDCfgalt.ldr"
        else:
            filepath = "LDConfig.ldr"

        ldraw_file = LDrawFile(filepath)
        ldraw_file.read_file()
        ldraw_file.parse_file()
