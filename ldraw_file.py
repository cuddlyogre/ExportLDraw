import os
import mathutils

from . import options
from . import filesystem

from .ldraw_node import LDrawNode
from .ldraw_geometry import LDrawGeometry
from .special_bricks import SpecialBricks


class LDrawFile:
    mpd_file_cache = {}
    file_cache = {}

    def __init__(self, filepath):
        self.filepath = filepath
        self.name = ""
        self.child_nodes = []
        self.geometry = LDrawGeometry()
        self.part_type = None
        self.lines = None

    @classmethod
    def reset_caches(cls):
        cls.mpd_file_cache = {}
        cls.file_cache = {}

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
            params = line.strip().split()

            if len(params) == 0:
                continue

            while len(params) < 9:
                params.append("")

            if params[0] == "0":
                if params[1] == "!LDRAW_ORG":
                    self.part_type = params[2].lower()
                elif params[1].lower() == "name:":
                    self.name = line[7:].lower().strip()
                elif params[1].lower() in ['print', 'write']:
                    if options.meta_print_write:
                        print(line[7:].lower().strip())
                elif params[1].lower() in ['step']:
                    if options.meta_step:
                        ldraw_node = LDrawNode('skip')
                        self.child_nodes.append(ldraw_node)
            else:
                if self.name == "":
                    self.name = os.path.basename(self.filepath)

                if params[0] == "1":
                    color_code = params[1]

                    (x, y, z, a, b, c, d, e, f, g, h, i) = map(float, params[2:14])
                    matrix = mathutils.Matrix(((a, b, c, x), (d, e, f, y), (g, h, i, z), (0, 0, 0, 1)))

                    filename = " ".join(params[14:]).lower()

                    if options.display_logo:
                        if filename in SpecialBricks.studs:
                            parts = filename.split(".")
                            name = parts[0]
                            ext = parts[1]
                            new_filename = f"{name}-{options.chosen_logo}.{ext}"
                            if filesystem.locate(new_filename):
                                filename = new_filename

                    if filename not in LDrawFile.file_cache:
                        ldraw_file = LDrawFile(filename)
                        ldraw_file.read_file()
                        ldraw_file.parse_file()
                        LDrawFile.file_cache[filename] = ldraw_file
                    ldraw_file = LDrawFile.file_cache[filename]

                    ldraw_node = LDrawNode(ldraw_file, color_code=color_code, matrix=matrix)
                    self.child_nodes.append(ldraw_node)
                elif params[0] in ["2", "3", "4"]:
                    if self.part_type is None:
                        self.part_type = 'part'

                    if params[0] in ["2"]:
                        self.geometry.parse_edge(params)
                    elif params[0] in ["3", "4"]:
                        self.geometry.parse_face(params)
