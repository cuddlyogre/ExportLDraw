import bpy
import bmesh

from . import strings
from . import options
from . import ldraw_file
from . import ldraw_colors
from . import filesystem
from . import matrices
from . import helpers
from . import ldraw_part_types


# https://devtalk.blender.org/t/to-mesh-and-creating-new-object-issues/8557/4
# https://docs.blender.org/api/current/bpy.types.Depsgraph.html
def clean_mesh(obj):
    bm = bmesh.new()
    bm.from_object(obj, bpy.context.evaluated_depsgraph_get())

    bm.transform(matrices.reverse_rotation @ obj.matrix_world)

    if options.triangulate:
        bmesh.ops.triangulate(bm, faces=bm.faces[:], quad_method='BEAUTY', ngon_method='BEAUTY')
    elif options.ngon_handling == "triangulate":
        faces = []
        for f in bm.faces:
            if len(f.verts) > 4:
                faces.append(f)
        bmesh.ops.triangulate(bm, faces=faces, quad_method='BEAUTY', ngon_method='BEAUTY')

    if options.remove_doubles:
        bmesh.ops.remove_doubles(bm, verts=bm.verts[:], dist=options.merge_distance)

    if options.recalculate_normals:
        bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])

    mesh = obj.data.copy()
    bm.to_mesh(mesh)
    bm.clear()
    bm.free()
    return mesh


# https://stackoverflow.com/a/2440786
# https://www.ldraw.org/article/512.html#precision
def fix_round(number, places=3):
    x = round(number, places)
    value = ("%f" % x).rstrip("0").rstrip(".")

    # remove -0
    if value == "-0":
        value = "0"

    return value


# TODO: if obj["section_label"] then:
#  0 // f{obj["section_label"]}
def export_subfiles(obj, lines, is_model=False):
    if strings.ldraw_filename_key not in obj:
        return False
    name = obj[strings.ldraw_filename_key]

    color_code = "16"
    color = ldraw_colors.get_color(color_code)

    if len(obj.data.materials) > 0:
        material = obj.data.materials[0]
        if strings.ldraw_color_code_key in material:
            color_code = str(material[strings.ldraw_color_code_key])
            color = ldraw_colors.get_color(color_code)

    color_code = color.code

    precision = options.export_precision
    if strings.ldraw_export_precision_key in obj:
        precision = obj[strings.ldraw_export_precision_key]

    if is_model:
        aa = matrices.reverse_rotation @ obj.matrix_world

        a = fix_round(aa[0][0], precision)
        b = fix_round(aa[0][1], precision)
        c = fix_round(aa[0][2], precision)
        x = fix_round(aa[0][3], precision)

        d = fix_round(aa[1][0], precision)
        e = fix_round(aa[1][1], precision)
        f = fix_round(aa[1][2], precision)
        y = fix_round(aa[1][3], precision)

        g = fix_round(aa[2][0], precision)
        h = fix_round(aa[2][1], precision)
        i = fix_round(aa[2][2], precision)
        z = fix_round(aa[2][3], precision)

        line = f"1 {color_code} {x} {y} {z} {a} {b} {c} {d} {e} {f} {g} {h} {i} {name}"
    else:
        aa = obj.matrix_world

        a = fix_round(aa[0][0], precision)
        b = fix_round(aa[0][1], precision)
        c = fix_round(-aa[0][2], precision)
        x = fix_round(aa[0][3], precision)

        d = fix_round(aa[1][0], precision)
        e = fix_round(aa[1][1], precision)
        f = fix_round(-aa[1][2], precision)
        y = fix_round(aa[1][3], precision)

        g = fix_round(-aa[2][0], precision)
        h = fix_round(-aa[2][1], precision)
        i = fix_round(aa[2][2], precision)
        z = fix_round(-aa[2][3], precision)

        line = f"1 {color_code} {x} {z} {y} {a} {c} {b} {g} {i} {h} {d} {f} {e} {name}"
    lines.append(line)


def export_polygons(obj, lines):
    if obj.data is None:
        return False

    if not getattr(obj.data, 'polygons', None):
        return False

    mesh = clean_mesh(obj)

    precision = options.export_precision
    if strings.ldraw_export_precision_key in obj:
        precision = obj[strings.ldraw_export_precision_key]

    for polygon in mesh.polygons:
        length = len(polygon.vertices)
        line_type = None
        if length == 3:
            line_type = 3
        elif length == 4:
            line_type = 4

        if line_type is None:
            continue

        color_code = "16"
        color = ldraw_colors.get_color(color_code)

        if polygon.material_index + 1 <= len(mesh.materials):
            material = mesh.materials[polygon.material_index]
            if strings.ldraw_color_code_key in material:
                color_code = str(material[strings.ldraw_color_code_key])
                color = ldraw_colors.get_color(color_code)

        color_code = color.code

        line = [str(line_type), color_code]

        for v in polygon.vertices:
            for vv in mesh.vertices[v].co:
                line.append(fix_round(vv, precision))

        lines.append(line)

    # export edges
    for e in mesh.edges:
        if e.use_edge_sharp:
            line = ["2", "24"]
            for v in e.vertices:
                for vv in mesh.vertices[v].co:
                    line.append(fix_round(vv))

            lines.append(line)

    bpy.data.meshes.remove(mesh)

    return True


# edges marked sharp will be output as line type 2
# tris => line type 3
# quads => line type 4
# conditional lines => line type 5 and ngons, aren't handled
# header file is determined by strings.ldraw_filename_key of active object
# if strings.ldraw_export_polygons_key == 1 current object being iterated will be exported as line type 2,3,4
# otherwise line type 2
def do_export(filepath):
    filesystem.build_search_paths()
    ldraw_file.read_color_table()

    active_object = bpy.context.object
    all_objects = bpy.context.scene.objects
    selected_objects = bpy.context.selected_objects
    active_objects = bpy.context.view_layer.objects.active

    objects = all_objects
    if options.selection_only:
        objects = selected_objects

    # TODO: use LDrawFile
    lines = []
    part_type = None

    if strings.ldraw_filename_key in active_object:
        header_text_name = active_object[strings.ldraw_filename_key]

        if header_text_name in bpy.data.texts:
            header_text = bpy.data.texts[header_text_name]

            for part_line in header_text.lines:
                lines.append(part_line.body)

                line = part_line.body

                params = helpers.parse_line(line, 14)

                if params is None:
                    continue

                if params[0] == "0":
                    if params[1].lower() in ["!ldraw_org"]:
                        if params[2].lower() in ["lcad"]:
                            part_type = params[3].lower()
                        else:
                            part_type = params[2].lower()

    is_model = part_type in ldraw_part_types.model_types

    subfile_objects = []
    polygon_objects = []

    for obj in objects:
        # so objects that are not linked to the scene don't get exported
        # objects during a failed export would be such an object
        if obj.users < 1:
            continue

        do_export_polygons = False
        if strings.ldraw_export_polygons_key in obj:
            do_export_polygons = obj[strings.ldraw_export_polygons_key] == 1

        if do_export_polygons:
            polygon_objects.append(obj)
        else:
            subfile_objects.append(obj)

    for obj in subfile_objects:
        export_subfiles(obj, lines, is_model=is_model)
    if len(subfile_objects) > 0:
        lines.append("\n")

    part_lines = []
    for obj in polygon_objects:
        export_polygons(obj, part_lines)

    sorted_part_lines = sorted(part_lines, key=lambda pl: (int(pl[1]), int(pl[0])))

    current_color_code = None
    joined_part_lines = []
    for part_line in sorted_part_lines:
        if len(part_line) > 2:
            new_color_code = part_line[1]
            if new_color_code != current_color_code:
                if current_color_code is not None:
                    joined_part_lines.append("\n")

                current_color_code = new_color_code
                color = ldraw_colors.get_color(current_color_code)

                joined_part_lines.append(f"0 // {color.name}")

        joined_part_lines.append(" ".join(part_line))
    lines.extend(joined_part_lines)

    with open(filepath, 'w') as file:
        for line in lines:
            file.write(line)
            if line != "\n":
                file.write("\n")

    for obj in selected_objects:
        if not obj.select_get():
            obj.select_set(True)

    bpy.context.view_layer.objects.active = active_objects
