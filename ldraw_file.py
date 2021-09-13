import os
import re
import mathutils
import uuid

from . import import_options
from . import filesystem
from . import helpers
from . import ldraw_part_types
from . import special_bricks

from .ldraw_node import LDrawNode
from .ldraw_geometry import LDrawGeometry
from . import ldraw_colors
from . import ldraw_camera
from . import texmap

mpd_file_cache = {}
file_cache = {}
key_map = {}


def reset_caches():
    global mpd_file_cache
    global file_cache
    global key_map
    mpd_file_cache = {}
    file_cache = {}
    key_map = {}


def read_color_table():
    ldraw_colors.reset_caches()

    """Reads the color values from the LDConfig.ldr file. For details of the
    LDraw color system see: http://www.ldraw.org/article/547"""

    if ldraw_colors.use_alt_colors:
        filename = "LDCfgalt.ldr"
    else:
        filename = "LDConfig.ldr"

    ldraw_file = LDrawFile(filename)
    ldraw_file.read_file()
    ldraw_file.parse_file()


def handle_mpd(filepath):
    if filepath in mpd_file_cache:
        return mpd_file_cache[filepath].filename

    filepath = filesystem.locate(filepath)
    if filepath is None:
        return None

    lines = []
    with open(filepath, 'r') as file:
        is_mpd = False
        while True:
            line = file.readline()
            if not line:
                break

            clean_line = helpers.clean_line(line)
            # fixed_line = line.strip()
            if clean_line == "":
                continue
            if clean_line.startswith("0 FILE") and not is_mpd:
                is_mpd = True
            if not is_mpd:
                return filepath
            lines.append(clean_line)

    if len(lines) < 1:
        return None

    root_file_name = None
    current_file = None
    for line in lines:
        params = helpers.parse_line(line, 17)

        if params is None:
            continue

        if params[0] == "0" and params[1] == "FILE":
            filename = line[7:].lower()
            if current_file is not None:
                mpd_file_cache[current_file.filename] = current_file
            current_file = LDrawFile(filename)

            if root_file_name is None:
                root_file_name = filename

        elif params[0] == "0" and params[1].lower() == "nofile":
            if current_file is not None:
                mpd_file_cache[current_file.filename] = current_file
            current_file = None

        elif current_file is not None:
            current_file.lines.append(line)

    if current_file is not None:
        mpd_file_cache[current_file.filename] = current_file

    if root_file_name is not None:
        return root_file_name

    return filepath


class LDrawFile:
    def __init__(self, filename):
        self.filename = filename
        self.filepath = None
        self.name = ""
        self.child_nodes = []
        self.geometry = LDrawGeometry()
        self.part_type = None
        self.lines = []
        self.extra_child_nodes = None
        self.extra_geometry = None

        self.texmap_start = False
        self.texmap_next = False
        self.texmap_fallback = False

        self.bfc_certified = None
        self.bfc_winding = "CCW"
        self.bfc = True
        self.bfc_culling = True

    def read_file(self):
        if self.filename in mpd_file_cache:
            self.lines = mpd_file_cache[self.filename].lines
        else:
            # TODO: if missing, use a,b,c etc parts if available
            self.filepath = filesystem.locate(self.filename)
            if self.filepath is None:
                print("missing {x}".format(**{"x": self.filename}))
                return False
            self.lines = filesystem.read_file(self.filepath)
        return True

    def parse_file(self):
        camera = None

        for line in self.lines:
            clean_line = helpers.clean_line(line)
            params = helpers.parse_line(line, 17)

            if params is None:
                continue

            # create meta nodes when those commands affect the scene
            # process meta command in place if it only affects the file
            if clean_line.startswith('0 BFC '):
                if self.bfc_certified is False:
                    continue

                print(clean_line)
                if clean_line == '0 BFC NOCERTIFY':
                    if self.bfc_certified is None:
                        self.bfc_certified = False
                else:
                    if self.bfc_certified is None:
                        self.bfc_certified = True

                    if clean_line in ['0 BFC CERTIFY', '0 BFC CERTIFY CCW']:
                        self.bfc_winding = "CCW"
                    elif clean_line == '0 BFC CERTIFY CW':
                        self.bfc_winding = "CW"
                    elif clean_line == '0 BFC CW':
                        ldraw_node = LDrawNode()
                        ldraw_node.meta_command = "bfc"
                        ldraw_node.meta_args = "cw"
                        self.child_nodes.append(ldraw_node)
                    elif clean_line == '0 BFC CCW':
                        ldraw_node = LDrawNode()
                        ldraw_node.meta_command = "bfc"
                        ldraw_node.meta_args = "ccw"
                        self.child_nodes.append(ldraw_node)
                    elif clean_line == '0 BFC CLIP':
                        ldraw_node = LDrawNode()
                        ldraw_node.meta_command = "bfc clip"
                        self.child_nodes.append(ldraw_node)
                    elif clean_line in ['0 BFC CLIP CW', '0 BFC CW CLIP']:
                        ldraw_node = LDrawNode()
                        ldraw_node.meta_command = "bfc clip"
                        ldraw_node.meta_args = "cw"
                        self.child_nodes.append(ldraw_node)
                    elif clean_line in ['0 BFC CLIP CCW', '0 BFC CCW CLIP']:
                        ldraw_node = LDrawNode()
                        ldraw_node.meta_command = "bfc clip"
                        ldraw_node.meta_args = "ccw"
                        self.child_nodes.append(ldraw_node)
                    elif clean_line == '0 BFC NOCLIP':
                        ldraw_node = LDrawNode()
                        ldraw_node.meta_command = "bfc noclip"
                        self.child_nodes.append(ldraw_node)
                    elif clean_line == '0 BFC INVERTNEXT':
                        ldraw_node = LDrawNode()
                        ldraw_node.meta_command = "bfc invertnext"
                        self.child_nodes.append(ldraw_node)
            elif params[0] == "0":
                if self.bfc_certified is None:
                    self.bfc_certified = False

                if params[1].lower() in ["!colour"]:
                    ldraw_colors.parse_color(params)
                elif params[1].lower() in ["!ldraw_org"]:
                    if params[2].lower() in ["lcad"]:
                        self.part_type = params[3].lower()
                    else:
                        self.part_type = params[2].lower()
                elif params[1].lower() in ["name:"]:
                    self.name = line[7:].lower().strip()
                elif params[1].lower() in ["step"]:
                    ldraw_node = LDrawNode()
                    ldraw_node.meta_command = "step"
                    self.child_nodes.append(ldraw_node)
                elif params[1].lower() in ["save"]:
                    ldraw_node = LDrawNode()
                    ldraw_node.meta_command = "save"
                    self.child_nodes.append(ldraw_node)
                elif params[1].lower() in ["clear"]:
                    ldraw_node = LDrawNode()
                    ldraw_node.meta_command = "clear"
                    self.child_nodes.append(ldraw_node)
                elif params[1].lower() in ["print", "write"]:
                    ldraw_node = LDrawNode()
                    ldraw_node.meta_command = "print"
                    ldraw_node.meta_args = line[7:].strip()
                    self.child_nodes.append(ldraw_node)
                elif self.texmap_next:
                    pass
                    # if 0 line and texmap next, error
                    # also error
                elif params[1].lower() in ["!texmap"]:  # https://www.ldraw.org/documentation/ldraw-org-file-format-standards/language-extension-for-texture-mapping.html
                    if params[2].lower() in ["start", "next"]:
                        if params[2].lower() == "start":
                            self.texmap_start = True
                        elif params[2].lower() == "next":
                            self.texmap_next = True
                        self.texmap_fallback = False

                        new_texmap = texmap.TexMap.parse_params(params)
                        if new_texmap is not None:
                            if texmap.texmap is not None:
                                texmap.texmaps.append(texmap.texmap)
                            texmap.texmap = new_texmap

                    elif self.texmap_start:
                        if params[2].lower() in ["fallback"]:
                            self.texmap_fallback = True
                        elif params[2].lower() in ["end"]:
                            self.set_texmap_end()
                elif self.texmap_start:
                    if params[1].lower() in ["!:"]:
                        # remove 0 !: from line so that it can be parsed like a normal line
                        clean_line = re.sub(r"(.*?\s+!:\s+)", "", line)
                        clean_params = params[2:]
                        self.parse_geometry_line(clean_line, clean_params)
                    if self.texmap_next:
                        self.set_texmap_end()
                elif params[1].lower() in ["PE_TEX_PATH"]:  # for stud.io uvs
                    if params[2].lower() in ['-1']:
                        # use uv coordinates that at the end of 3,4 lines
                        # 2*vertcount places at the end of the line
                        pass
                elif params[1].lower() in ["pe_tex_info"]:
                    filename = self.name
                    if filename == "":
                        filename = os.path.basename(self.filename)
                    image_data = params[2]
                    texmap.TexMap.base64_to_png(filename, image_data)
                elif params[1].lower() in ["!ldcad"]:  # http://www.melkert.net/LDCad/tech/meta
                    if params[2].lower() in ["group_def"]:
                        params = re.search(r"\S+\s+\S+\s+\S+\s+(\[.*\])\s+(\[.*\])\s+(\[.*\])\s+(\[.*\])\s+(\[.*\])", line.strip())

                        ldraw_node = LDrawNode()
                        ldraw_node.meta_command = "group_def"

                        id_args = re.search(r"\[(.*)=(.*)\]", params[2])
                        ldraw_node.meta_args["id"] = id_args[2]

                        name_args = re.search(r"\[(.*)=(.*)\]", params[4])
                        ldraw_node.meta_args["name"] = name_args[2]

                        self.child_nodes.append(ldraw_node)
                    elif params[2].lower() in ["group_nxt"]:
                        params = re.search(r"\S+\s+\S+\s+\S+\s+(\[.*\])\s+(\[.*\])", line.strip())

                        ldraw_node = LDrawNode()
                        ldraw_node.meta_command = "group_nxt"

                        id_args = re.search(r"\[(.*)=(.*)\]", params[1])
                        ldraw_node.meta_args["id"] = id_args[2]

                        self.child_nodes.append(ldraw_node)
                elif params[1].lower() in ["!leocad"]:  # https://www.leocad.org/docs/meta.html
                    if params[2].lower() in ["group"]:
                        if params[3].lower() in ["begin"]:
                            # begin_params = re.search(r"(?:.*\s+){3}begin\s+(.*)", line, re.IGNORECASE)
                            begin_params = re.search(r"\S+\s+\S+\s+\S+\s+\S+\s+(.*)", line.strip())

                            if begin_params is not None:
                                ldraw_node = LDrawNode()
                                ldraw_node.meta_command = "group_begin"
                                ldraw_node.meta_args["name"] = begin_params[1]
                                self.child_nodes.append(ldraw_node)
                        elif params[3].lower() in ["end"]:
                            ldraw_node = LDrawNode()
                            ldraw_node.meta_command = "group_end"
                            self.child_nodes.append(ldraw_node)
                    elif params[2] == "CAMERA":
                        if camera is None:
                            camera = ldraw_camera.LDrawCamera()

                        params = params[3:]

                        # https://www.leocad.org/docs/meta.html
                        # "Camera commands can be grouped in the same line"
                        # params = params[1:] at the end bumps promotes params[2] to params[1]

                        while len(params) > 0:
                            if params[0] == "FOV":
                                camera.fov = float(params[1])
                                params = params[2:]
                            elif params[0] == "ZNEAR":
                                camera.z_near = float(params[1])
                                params = params[2:]
                            elif params[0] == "ZFAR":
                                camera.z_far = float(params[1])
                                params = params[2:]
                            elif params[0] in ["POSITION", "TARGET_POSITION", "UP_VECTOR"]:
                                (x, y, z) = map(float, params[1:4])
                                vector = mathutils.Vector((x, y, z))

                                if params[0] == "POSITION":
                                    camera.position = vector

                                elif params[0] == "TARGET_POSITION":
                                    camera.target_position = vector

                                elif params[0] == "UP_VECTOR":
                                    camera.up_vector = vector

                                params = params[4:]

                            elif params[0] == "ORTHOGRAPHIC":
                                camera.orthographic = True
                                params = params[1:]
                            elif params[0] == "HIDDEN":
                                camera.hidden = True
                                params = params[1:]
                            elif params[0] == "NAME":
                                camera_name_params = re.search(r"\S+\s+\S+\s+\S+\s+\S+\s+(.*)", line.strip())

                                camera.name = camera_name_params[1].strip()

                                # By definition this is the last of the parameters
                                params = []

                                ldraw_camera.cameras.append(camera)
                                camera = None
                            else:
                                params = params[1:]
            else:
                if not self.texmap_fallback:
                    self.parse_geometry_line(line, params)

        if self.name == "":
            self.name = os.path.basename(self.filename)

        if self.extra_geometry is not None or self.extra_child_nodes is not None:
            _key = []
            _key.append(self.filename)
            _key.append("extra")
            _key.append(filesystem.resolution)
            if import_options.remove_doubles:
                _key.append("rd")
            if import_options.display_logo:
                _key.append(special_bricks.chosen_logo)
            if import_options.smooth_type == "auto_smooth":
                _key.append("as")
            if import_options.smooth_type == "edge_split":
                _key.append("es")
            if ldraw_colors.use_alt_colors:
                _key.append("alt")
            if texmap.texmap is not None:
                _key.append(texmap.texmap.id)
            _key = "_".join([str(k).lower() for k in _key])
            _key = re.sub(r"[^a-z0-9._]", "-", _key)

            if _key not in key_map:
                key_map[_key] = str(uuid.uuid4())
            key = key_map[_key]

            if key not in file_cache:
                filename = "{x}_extra".format(**{"x": self.name})
                ldraw_file = LDrawFile(filename)
                ldraw_file.name = filename
                ldraw_file.part_type = "part"
                ldraw_file.child_nodes = (self.extra_child_nodes or [])
                ldraw_file.geometry = (self.extra_geometry or LDrawGeometry())
                file_cache[key] = ldraw_file
            ldraw_file = file_cache[key]
            ldraw_node = LDrawNode()
            ldraw_node.file = ldraw_file
            self.child_nodes.append(ldraw_node)

    def set_texmap_end(self):
        if len(texmap.texmaps) < 1:
            texmap.texmap = None
        else:
            texmap.texmap = texmap.texmaps.pop()
        self.texmap_start = False
        self.texmap_next = False
        self.texmap_fallback = False

    def parse_geometry_line(self, line, params):
        if params[0] == "1":
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
            filename_args = re.search(r"(\S+)\s+(\S+)\s+(\S+)\s+(\S+)\s+(\S+)\s+(\S+)\s+(\S+)\s+(\S+)\s+(\S+)\s+(\S+)\s+(\S+)\s+(\S+)\s+(\S+)\s+(\S+)(?:\s+(\S+.*))?", line.strip())
            filename = filename_args.group(15).lower()

            # filename = "stud-logo.dat"
            # parts = filename.split(".") => ["stud-logo", "dat"]
            # name = parts[0] => "stud-logo"
            # name_parts = name.split('-') => ["stud", "logo"]
            # stud_name = name_parts[0] => "stud"
            # chosen_logo = special_bricks.chosen_logo => "logo5"
            # ext = parts[1] => "dat"
            # filename = f"{stud_name}-{chosen_logo}.{ext}" => "stud-logo5.dat"
            if import_options.display_logo and self.is_stud():
                parts = filename.split(".")
                name = parts[0]
                name_parts = name.split('-')
                stud_name = name_parts[0]
                chosen_logo = special_bricks.chosen_logo
                ext = parts[1]
                filename = "{stud_name}-{chosen_logo}.{ext}".format(**{"stud_name": stud_name, "chosen_logo": chosen_logo, "ext": ext})

            _key = []
            _key.append(filename)
            _key.append(filesystem.resolution)
            if import_options.remove_doubles:
                _key.append("rd")
            if import_options.display_logo:
                _key.append(special_bricks.chosen_logo)
            if import_options.smooth_type == "auto_smooth":
                _key.append("as")
            if import_options.smooth_type == "edge_split":
                _key.append("es")
            if ldraw_colors.use_alt_colors:
                _key.append("alt")
            if texmap.texmap is not None:
                _key.append(texmap.texmap.id)
            _key = "_".join([str(k).lower() for k in _key])
            _key = re.sub(r"[^a-z0-9._]", "-", _key)

            if _key not in key_map:
                key_map[_key] = str(uuid.uuid4())
            key = key_map[_key]

            if key not in file_cache:
                filename = handle_mpd(filename)
                ldraw_file = LDrawFile(filename)
                if not ldraw_file.read_file():
                    return None
                ldraw_file.parse_file()
                file_cache[key] = ldraw_file
            ldraw_file = file_cache[key]

            if import_options.no_studs and ldraw_file.is_like_stud():
                return

            ldraw_node = LDrawNode()
            ldraw_node.file = ldraw_file
            ldraw_node.color_code = color_code
            ldraw_node.matrix = matrix

            # if any line in a model file is a subpart, treat that model as a part, otherwise subparts are not parsed correctly
            # if subpart found, create new LDrawNode with those subparts and add that to child_nodes
            if self.is_like_model() and (ldraw_file.is_subpart() or ldraw_file.is_primitive()):
                if self.extra_child_nodes is None:
                    self.extra_child_nodes = []
                self.extra_child_nodes.append(ldraw_node)
            else:
                self.child_nodes.append(ldraw_node)
        elif params[0] in ["2", "3", "4"]:
            if self.is_like_model():
                if self.extra_geometry is None:
                    self.extra_geometry = LDrawGeometry()
                self.extra_geometry.parse_face(params, texmap.texmap)
            else:
                self.geometry.parse_face(params, texmap.texmap)

    # this allows shortcuts to be split into their individual parts if desired
    def is_like_model(self):
        return self.is_model() or (import_options.treat_shortcut_as_model and self.is_shortcut())

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
