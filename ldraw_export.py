import bpy

from .ldraw_colors import LDrawColors

triangulate = None
recalculate_normals = None
selection_only = None
ngon_handling = None


def select_object(obj):
    obj.select_set(state=True)
    bpy.context.view_layer.objects.active = obj


def deselect_object(obj):
    obj.select_set(state=False)
    bpy.context.view_layer.objects.active = None


def link_to_scene(obj):
    if obj.name not in bpy.context.scene.objects:
        bpy.context.scene.collection.objects.link(obj)


def unlink_from_scene(obj):
    if obj.name in bpy.context.scene.objects:
        bpy.context.scene.collection.objects.unlink(obj)


def fix_rotation(obj):
    from math import radians
    from mathutils import Matrix
    obj.matrix_world = obj.matrix_world @ Matrix.Rotation(radians(90), 4, 'X')
    bpy.ops.object.transform_apply(location=False, rotation=True, scale=False)


def apply_transforms(obj):
    bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)


def apply_modifiers(obj):
    for m in obj.modifiers:
        if m.show_viewport:
            bpy.ops.object.modifier_apply(modifier=m.name)


def handle_ngons(obj):
    if ngon_handling == "skip":
        return

    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.mesh.select_all(action='DESELECT')
    bpy.ops.mesh.select_face_by_sides(number=4, type='GREATER')
    bpy.ops.mesh.quads_convert_to_tris(quad_method='BEAUTY', ngon_method='BEAUTY')
    bpy.ops.object.mode_set(mode='OBJECT')


def do_bpy_ops(obj):
    link_to_scene(obj)
    select_object(obj)
    handle_ngons(obj)
    fix_rotation(obj)
    apply_transforms(obj)
    apply_modifiers(obj)
    deselect_object(obj)
    unlink_from_scene(obj)


# https://stackoverflow.com/a/2440786
# https://www.ldraw.org/article/512.html#precision
def fix_round(number, places=3):
    x = round(number, places)
    value = ('%f' % x).rstrip('0').rstrip('.')

    # remove -0
    if value == "-0":
        value = "0"

    return value


# TODO: if obj["section_label"] then:
#  0 // f{obj["section_label"]}
def export_subfiles(obj, lines):
    import re
    # subpart.dat
    # subpart.dat.001 both match
    if not re.search("(.*\.(?:mpd|dat|ldr))\.*.*$", obj.name):
        return False

    aa = obj.matrix_world

    a = fix_round(aa[0][0])
    b = fix_round(aa[0][1])
    c = fix_round(-aa[0][2])
    x = fix_round(aa[0][3])

    d = fix_round(aa[1][0])
    e = fix_round(aa[1][1])
    f = fix_round(-aa[1][2])
    y = fix_round(aa[1][3])

    g = fix_round(-aa[2][0])
    h = fix_round(-aa[2][1])
    i = fix_round(aa[2][2])
    z = fix_round(-aa[2][3])

    # remove .000 for duplicated parts
    name = obj.name
    import re
    name = re.sub(r"\.\d+$", "", name)
    # name = re.sub(r"^\d+_", "", name)

    line = f"1 16 {x} {z} {y} {a} {c} {b} {g} {i} {h} {d} {f} {e} {name}"
    # line = f"1 4 {x} {y} {z} {a} {b} {c} {d} {e} {f} {g} {h} {i} {name}"
    lines.extend([line])

    return True


def export_polygons(obj, lines):
    if not getattr(obj.data, 'polygons', None):
        return False

    # so objects that are not linked to the scene don't get exported
    # objects during a failed export would be such an object
    if obj.users < 1:
        return False

    new_obj = obj.copy()
    mesh = obj.data.copy()
    new_obj.data = mesh

    # print(new_obj)
    do_bpy_ops(new_obj)

    for p in mesh.polygons:
        length = len(p.vertices)
        line_type = None
        if length == 3:
            line_type = 3
        elif length == 4:
            line_type = 4

        if line_type is None:
            continue

        # TODO: check for valid color codes
        if p.material_index + 1 > len(mesh.materials):
            color_code = "16"
        else:
            color_code = mesh.materials[p.material_index].name

        line = [str(line_type), str(color_code)]

        for v in p.vertices:
            for vv in mesh.vertices[v].co:
                line.extend([fix_round(vv)])

        lines.append(line)

    # export edges
    for e in mesh.edges:
        if e.use_edge_sharp and e.bevel_weight == 1.00:
            line = ["2", "24"]
            for v in e.vertices:
                for vv in mesh.vertices[v].co:
                    line.extend([fix_round(vv)])

            lines.append(line)

    bpy.data.objects.remove(new_obj)
    bpy.data.meshes.remove(mesh)

    return True


def write_file(lines, filepath):
    with open(filepath, 'w') as file:
        current_color_code = None
        for line in lines:
            if len(line) > 2:
                new_color_code = int(line[1])
                if new_color_code != current_color_code:
                    current_color_code = new_color_code
                    name = LDrawColors.colors[current_color_code]['name']
                    file.write("\n")
                    file.write(" ".join(["0 //", name]))
                    file.write("\n")

            file.write(" ".join(line))
            file.write("\n")


# objects in "Scene Collection > subfiles" will be output as line type 1
# objects marked sharp and with a bevel weight of 1.00 will be output as line type 2
# objects in "Scene Collection > polygons" will be output as line type 3 or 4, depending on their vertex count
# if ngons are triangulated, they will be line type 3, otherwise they won't be exported at all
# conditional lines, line type 5, aren't handled
def do_export(filepath, ldraw_path):
    LDrawColors.colors = {}  # required or else colors is seen as {}
    LDrawColors.read_color_table(ldraw_path)

    all_objects = bpy.context.scene.objects
    selected = bpy.context.selected_objects
    active = bpy.context.view_layer.objects.active

    if selection_only:
        objects = selected
    else:
        objects = all_objects

    if active is not None:
        bpy.ops.object.mode_set(mode='OBJECT')
    bpy.ops.object.select_all(action='DESELECT')

    lines = []

    header_text_name = "header"
    if header_text_name in bpy.data.texts:
        for line in bpy.data.texts[header_text_name].lines:
            lines.append([line.body])

    part_lines = []
    for obj in objects:
        # print(obj.name)
        if export_subfiles(obj, lines):
            continue
        export_polygons(obj, part_lines)

    # print(part_lines)

    part_lines = sorted(part_lines, key=lambda pl: (int(pl[1]), int(pl[0])))
    lines.extend(part_lines)

    write_file(lines, filepath)

    for obj in selected:
        if not obj.select_get():
            obj.select_set(True)

    bpy.context.view_layer.objects.active = active
