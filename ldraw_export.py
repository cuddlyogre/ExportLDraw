from math import radians
from mathutils import Matrix
import re
import csv
import io

import bpy
import bmesh

from . import filesystem
from .ldraw_file import LDrawFile
from .ldraw_colors import LDrawColors
from . import matrices


class LDrawExporter:
    triangulate = None
    recalculate_normals = None
    selection_only = None
    ngon_handling = None

    @staticmethod
    def clean_mesh(obj):
        mesh = obj.data.copy()

        bm = bmesh.new()
        bm.from_object(obj, bpy.context.evaluated_depsgraph_get())

        bm.transform(matrices.reverse_rotation @ obj.matrix_world)

        if LDrawExporter.ngon_handling == "triangulate":
            faces = []
            for f in bm.faces:
                if len(f.verts) > 4:
                    faces.append(f)
            bmesh.ops.triangulate(bm,
                                  faces=faces,
                                  quad_method='BEAUTY',
                                  ngon_method='BEAUTY')

        bm.to_mesh(mesh)
        bm.clear()
        bm.free()

        return mesh

    # https://stackoverflow.com/a/2440786
    # https://www.ldraw.org/article/512.html#precision
    @staticmethod
    def fix_round(number, places=3):
        x = round(number, places)
        value = ('%f' % x).rstrip('0').rstrip('.')

        # remove -0
        if value == "-0":
            value = "0"

        return value

    # TODO: if obj["section_label"] then:
    #  0 // f{obj["section_label"]}
    @classmethod
    def export_subfiles(cls, obj, lines, is_model=False):
        # subpart.dat
        # subpart.dat.001 both match
        if not re.search(r"(.*\.(?:mpd|dat|ldr))\.*.*$", obj.name):
            return False

        name = obj.name
        if "filename" in obj:
            name = obj["filename"]

        # remove .000 for duplicated parts
        name = re.sub(r"\.\d+$", "", name)
        # name = re.sub(r"^\d+_", "", name)

        color_code = "16"
        if len(obj.data.materials) > 0:
            material = obj.data.materials[0]
            color_code = material.name
            if "color_code" in material:
                color_code = material["color_code"]

            color = LDrawColors.get_color(color_code)
            if color is not None:
                color_code = color["code"]

        if is_model:
            aa = matrices.reverse_rotation @ obj.matrix_world

            a = cls.fix_round(aa[0][0])
            b = cls.fix_round(aa[0][1])
            c = cls.fix_round(aa[0][2])
            x = cls.fix_round(aa[0][3])

            d = cls.fix_round(aa[1][0])
            e = cls.fix_round(aa[1][1])
            f = cls.fix_round(aa[1][2])
            y = cls.fix_round(aa[1][3])

            g = cls.fix_round(aa[2][0])
            h = cls.fix_round(aa[2][1])
            i = cls.fix_round(aa[2][2])
            z = cls.fix_round(aa[2][3])

            line = f"1 {color_code} {x} {y} {z} {a} {b} {c} {d} {e} {f} {g} {h} {i} {name}"
        else:
            aa = obj.matrix_world

            a = cls.fix_round(aa[0][0])
            b = cls.fix_round(aa[0][1])
            c = cls.fix_round(-aa[0][2])
            x = cls.fix_round(aa[0][3])

            d = cls.fix_round(aa[1][0])
            e = cls.fix_round(aa[1][1])
            f = cls.fix_round(-aa[1][2])
            y = cls.fix_round(aa[1][3])

            g = cls.fix_round(-aa[2][0])
            h = cls.fix_round(-aa[2][1])
            i = cls.fix_round(aa[2][2])
            z = cls.fix_round(-aa[2][3])

            line = f"1 {color_code} {x} {z} {y} {a} {c} {b} {g} {i} {h} {d} {f} {e} {name}"
        lines.append(line)

        return True

    @classmethod
    def export_polygons(cls, obj, lines):
        if not getattr(obj.data, 'polygons', None):
            return False

        # so objects that are not linked to the scene don't get exported
        # objects during a failed export would be such an object
        if obj.users < 1:
            return False

        mesh = cls.clean_mesh(obj)

        for p in mesh.polygons:
            length = len(p.vertices)
            line_type = None
            if length == 3:
                line_type = 3
            elif length == 4:
                line_type = 4

            if line_type is None:
                continue

            color_code = "16"
            if p.material_index + 1 <= len(mesh.materials):
                material = mesh.materials[p.material_index]
                color_code = material.name
                if "color_code" in material:
                    color_code = material["color_code"]

            color = LDrawColors.get_color(color_code)
            color_code = "16"
            if color is not None:
                color_code = color["code"]

            line = [str(line_type), str(color_code)]

            for v in p.vertices:
                for vv in mesh.vertices[v].co:
                    line.append(cls.fix_round(vv))

            lines.append(line)

        # export edges
        for e in mesh.edges:
            if e.use_edge_sharp and e.bevel_weight == 1.00:
                line = ["2", "24"]
                for v in e.vertices:
                    for vv in mesh.vertices[v].co:
                        line.append(cls.fix_round(vv))

                lines.append(line)

        bpy.data.meshes.remove(mesh)

        return True

    # objects in "Scene Collection > subfiles" will be output as line type 1
    # objects marked sharp and with a bevel weight of 1.00 will be output as line type 2
    # objects in "Scene Collection > polygons" will be output as line type 3 or 4, depending on their vertex count
    # if ngons are triangulated, they will be line type 3, otherwise they won't be exported at all
    # conditional lines, line type 5, aren't handled
    @classmethod
    def do_export(cls, filepath):
        filesystem.build_search_paths()
        LDrawFile.read_color_table()

        all_objects = bpy.context.scene.objects
        selected = bpy.context.selected_objects
        active = bpy.context.view_layer.objects.active

        objects = all_objects
        if cls.selection_only:
            objects = selected

        lines = []

        part_type = None

        header_text_name = "header"
        if header_text_name in bpy.data.texts:
            for text_line in bpy.data.texts[header_text_name].lines:
                lines.append(text_line.body)

                line = text_line.body

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
                    if params[1].lower() in ["!ldraw_org"]:
                        if params[2].lower() in ["lcad"]:
                            part_type = params[3].lower()
                        else:
                            part_type = params[2].lower()

        model_types = ['model', 'unofficial_model', 'un-official model', 'submodel', None]
        is_model = part_type in model_types

        part_lines = []
        for obj in objects:
            if obj.data is None:
                continue
            # print(obj.name)
            if cls.export_subfiles(obj, lines, is_model=is_model):
                continue
            cls.export_polygons(obj, part_lines)

        part_lines = sorted(part_lines, key=lambda pl: (int(pl[1]), int(pl[0])))

        sorted_part_lines = []
        current_color_code = None
        for text_line in part_lines:
            if len(text_line) > 2:
                new_color_code = int(text_line[1])
                if new_color_code != current_color_code:
                    current_color_code = new_color_code
                    name = LDrawColors.get_color(current_color_code)['name']
                    sorted_part_lines.append("\n")
                    sorted_part_lines.append(f"0 // {name}")
            sorted_part_lines.append(" ".join(text_line))
        lines.extend(sorted_part_lines)

        with open(filepath, 'w') as file:
            for i, text_line in enumerate(lines):
                # print(line)
                if text_line != "\n":
                    file.write(text_line)
                file.write("\n")

        for obj in selected:
            if not obj.select_get():
                obj.select_set(True)

        bpy.context.view_layer.objects.active = active
