import os
import mathutils
import struct
import re
import csv
import io

from . import options
from . import filesystem

from .ldraw_node import LDrawNode
from .ldraw_geometry import LDrawGeometry
from .special_bricks import SpecialBricks
from .ldraw_colors import LDrawColors


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
            filepath = filesystem.locate(self.filepath)
            if filepath is None:
                print(f"missing {self.filepath}")
                return
            self.lines = filesystem.read_file(filepath)

    def parse_file(self):
        for line in self.lines:
            line = line.replace("\t", " ")
            rows = list(csv.reader(io.StringIO(line), delimiter=' ', quotechar='"', skipinitialspace=True))

            if len(rows) == 0:
                continue

            params = rows[0]

            if len(params) == 0:
                continue

            while len(params) < 14:
                params.append("")

            if params[0] == "0":
                if params[1].lower() in ["!colour"]:
                    name = params[2]
                    color_code = int(params[4])

                    linear_rgba = LDrawFile.__hex_digits_to_linear_rgba(params[6][1:], 1.0)
                    alpha = linear_rgba[3]
                    linear_rgba = LDrawFile.__srgb_to_linear_rgb(linear_rgba[0:3])

                    lineaer_rgba_edge = LDrawFile.__hex_digits_to_linear_rgba(params[8][1:], 1.0)
                    lineaer_rgba_edge = LDrawFile.__srgb_to_linear_rgb(lineaer_rgba_edge[0:3])

                    color = {
                        "name": name,
                        "color": linear_rgba,
                        "alpha": alpha,
                        "edge_color": lineaer_rgba_edge,
                        "luminance": 0.0,
                        "material": "BASIC"
                    }

                    if "ALPHA" in params:
                        color["alpha"] = int(LDrawFile.__get_value(params, "ALPHA")) / 256.0

                    if "LUMINANCE" in params:
                        color["luminance"] = int(LDrawFile.__get_value(params, "LUMINANCE"))

                    if "CHROME" in params:
                        color["material"] = "CHROME"

                    if "PEARLESCENT" in params:
                        color["material"] = "PEARLESCENT"

                    if "RUBBER" in params:
                        color["material"] = "RUBBER"

                    if "METAL" in params:
                        color["material"] = "METAL"

                    if "MATERIAL" in params:
                        subline = params[params.index("MATERIAL"):]

                        color["material"] = LDrawFile.__get_value(subline, "MATERIAL")
                        hex_digits = LDrawFile.__get_value(subline, "VALUE")[1:]
                        color["secondary_color"] = LDrawFile.__hex_digits_to_linear_rgba(hex_digits, 1.0)
                        color["fraction"] = LDrawFile.__get_value(subline, "FRACTION")
                        color["vfraction"] = LDrawFile.__get_value(subline, "VFRACTION")
                        color["size"] = LDrawFile.__get_value(subline, "SIZE")
                        color["minsize"] = LDrawFile.__get_value(subline, "MINSIZE")
                        color["maxsize"] = LDrawFile.__get_value(subline, "MAXSIZE")

                    LDrawColors.set_color(color_code, color)
                if params[1].lower() in ["!ldraw_org", "ldraw_org", "unofficial", "un-official", "official"]:
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
            else:
                if self.name == "":
                    self.name = os.path.basename(self.filepath)

                if params[0] == "1":
                    color_code = params[1]

                    (x, y, z, a, b, c, d, e, f, g, h, i) = map(float, params[2:14])

                    matrix = mathutils.Matrix((
                        (a, b, c, x),
                        (d, e, f, y),
                        (g, h, i, z),
                        (0, 0, 0, 1)
                    ))

                    filename = " ".join(params[14:]).lower()

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
                elif params[0] in ["2", "3", "4"]:
                    if self.part_type is None:
                        self.part_type = 'part'

                    if params[0] in ["2"]:
                        self.geometry.parse_edge(params)
                    elif params[0] in ["3", "4"]:
                        self.geometry.parse_face(params)

    @classmethod
    def handle_mpd(cls, filepath):
        ldraw_file = LDrawFile(filepath)
        ldraw_file.read_file()
        lines = ldraw_file.lines

        if not lines[0].lower().startswith("0 f"):
            return filepath

        root_file = None
        current_file = None
        for line in lines:
            params = line.strip().split()

            if len(params) == 0:
                continue

            while len(params) < 9:
                params.append("")

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
    def __get_value(line, value):
        """Parses a color value from the ldConfig.ldr file"""
        if value in line:
            n = line.index(value)
            return line[n + 1]

    @staticmethod
    def __srgb_to_rgb_value(value):
        # See https://en.wikipedia.org/wiki/SRGB#The_reverse_transformation
        if value < 0.04045:
            return value / 12.92
        return ((value + 0.055) / 1.055) ** 2.4

    @classmethod
    def __srgb_to_linear_rgb(cls, srgb_color):
        # See https://en.wikipedia.org/wiki/SRGB#The_reverse_transformation
        (sr, sg, sb) = srgb_color
        r = cls.__srgb_to_rgb_value(sr)
        g = cls.__srgb_to_rgb_value(sg)
        b = cls.__srgb_to_rgb_value(sb)
        return r, g, b

    @classmethod
    def __hex_digits_to_linear_rgba(cls, hex_digits, alpha):
        # String is "RRGGBB" format
        int_tuple = struct.unpack('BBB', bytes.fromhex(hex_digits))
        srgb = tuple([val / 255 for val in int_tuple])
        linear_rgb = cls.__srgb_to_linear_rgb(srgb)
        return linear_rgb[0], linear_rgb[1], linear_rgb[2], alpha
