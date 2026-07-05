import bpy
import mathutils

from . import matrices
from .import_options import ImportOptions
from .texmap import TexMap
from . import group
from . import helpers
from . import ldraw_camera


current_frame = 0
current_step = 0
cameras = []
camera = None


def reset_caches():
    global current_frame
    global current_step
    global cameras
    global camera

    current_frame = 0
    current_step = 0
    cameras.clear()
    camera = None


def meta_bfc(clean_line, matrix, local_cull, winding, invert_next, accum_invert, bfc_certified):
    _params = clean_line.split()[2:]

    # https://www.ldraw.org/article/415.html#processing
    if bfc_certified is not False:
        if bfc_certified is None and "NOCERTIFY" not in _params:
            bfc_certified = True

        if "CERTIFY" in _params:
            bfc_certified = True

        if "NOCERTIFY" in _params:
            bfc_certified = False

        """
        https://www.ldraw.org/article/415.html#rendering
        Degenerate Matrices. Some orientation matrices do not allow calculation of a determinate.
        This calculation is central to BFC processing. If an orientation matrix for a subfile is
        degenerate, then culling will not be possible for that subfile.

        https://math.stackexchange.com/a/792591
        A singular matrix, also known as a degenerate matrix, is a square matrix whose determinate is zero.
        https://www.algebrapracticeproblems.com/singular-degenerate-matrix/
        A singular (or degenerate) matrix is a square matrix whose inverse matrix cannot be calculated.
        Therefore, the determinant of a singular matrix is equal to 0.
        """
        if matrix.determinant() == 0:
            bfc_certified = False

    if "CLIP" in _params:
        local_cull = True

    if "NOCLIP" in _params:
        local_cull = False

    if "CCW" in _params:
        if accum_invert:
            winding = "CW"
        else:
            winding = "CCW"

    if "CW" in _params:
        if accum_invert:
            winding = "CCW"
        else:
            winding = "CW"

    if "INVERTNEXT" in _params:
        invert_next = True

    """
    https://www.ldraw.org/article/415.html#rendering
    If the rendering engine does not detect and adjust for reversed matrices, the winding of all polygons in
    the subfile will be switched, causing the subfile to be rendered incorrectly.

    The typical method of determining that an orientation matrix is reversed is to calculate the determinant of
    the matrix. If the determinant is negative, then the matrix has been reversed.

    The typical way to adjust for matrix reversals is to switch the expected winding of the polygon vertices.
    That is, if the file specifies the winding as CW and the orientation matrix is reversed, the rendering
    program would proceed as if the winding is CCW.

    The INVERTNEXT option also reverses the winding of the polygons within the subpart or primitive.
    If the matrix applied to the subpart or primitive has itself been reversed the INVERTNEXT processing
    is done IN ADDITION TO the automatic inversion - the two effectively cancelling each other out.
    """
    if matrix.determinant() < 0:
        if not invert_next:
            if winding == "CW":
                winding = "CCW"
            else:
                winding = "CW"

    return local_cull, winding, invert_next, bfc_certified


def meta_step():
    global current_step
    global current_frame

    if not ImportOptions.meta_step:
        return

    first_frame = (ImportOptions.starting_step_frame + ImportOptions.frames_per_step)
    current_step_frame = (ImportOptions.frames_per_step * current_step)
    current_frame = first_frame + current_step_frame
    current_step += 1

    if ImportOptions.set_timeline_markers:
        bpy.context.scene.timeline_markers.new("STEP", frame=current_frame)

    if ImportOptions.meta_step_groups:
        collection_name = f"{group.top_collection.name} Steps"
        host_collection = group.top_collection
        steps_collection = group.get_collection(collection_name, host_collection)
        helpers.hide_obj(steps_collection)

        collection_name = f"Step {str(current_step)}"
        host_collection = steps_collection
        step_collection = group.get_collection(collection_name, host_collection)
        group.current_step_group = step_collection


def do_meta_step(obj):
    if ImportOptions.meta_step:
        helpers.hide_obj(obj)
        obj.keyframe_insert(data_path="hide_render", frame=ImportOptions.starting_step_frame)
        obj.keyframe_insert(data_path="hide_viewport", frame=ImportOptions.starting_step_frame)

        helpers.show_obj(obj)
        obj.keyframe_insert(data_path="hide_render", frame=current_frame)
        obj.keyframe_insert(data_path="hide_viewport", frame=current_frame)


def meta_save():
    if ImportOptions.meta_save:
        if ImportOptions.set_timeline_markers:
            bpy.context.scene.timeline_markers.new("SAVE", frame=current_frame)


def meta_clear():
    if ImportOptions.meta_clear:
        if ImportOptions.set_timeline_markers:
            bpy.context.scene.timeline_markers.new("CLEAR", frame=current_frame)
        if group.top_collection is not None:
            for obj in group.top_collection.all_objects:
                helpers.hide_obj(obj)
                obj.keyframe_insert(data_path="hide_render", frame=current_frame)
                obj.keyframe_insert(data_path="hide_viewport", frame=current_frame)


def meta_print(child_node):
    if ImportOptions.meta_print_write:
        print(child_node.meta_args["message"])


def meta_group(child_node):
    if ImportOptions.meta_group:
        if child_node.meta_command == "group_def":
            meta_group_def(child_node)
        elif child_node.meta_command == "group_nxt":
            meta_group_nxt(child_node)
        elif child_node.meta_command == "group_begin":
            meta_group_begin(child_node)
        elif child_node.meta_command == "group_end":
            meta_group_end()


def meta_group_def(child_node):
    group.collection_id_map[child_node.meta_args["id"]] = child_node.meta_args["name"]
    name = group.collection_id_map[child_node.meta_args["id"]]
    collection_name = f"{group.top_collection.name} {name}"
    host_collection = group.groups_collection
    group.get_collection(collection_name, host_collection)


def meta_group_nxt(child_node):
    group.stored_collection = group.next_collection
    collection = None
    if child_node.meta_args["id"] in group.collection_id_map:
        name = group.collection_id_map[child_node.meta_args["id"]]
        collection_name = f"{group.top_collection.name} {name}"
        collection = bpy.data.collections.get(collection_name)
    group.next_collection = collection
    group.end_next_collection = True


def meta_group_begin(child_node):
    if group.next_collection is not None:
        group.next_collections.append(group.next_collection)

    name = child_node.meta_args["name"]
    collection_name = f"{group.top_collection.name} {name}"
    host_collection = group.groups_collection
    collection = group.get_collection(collection_name, host_collection)
    group.next_collection = collection

    if len(group.next_collections) > 0:
        host_collection = group.next_collections[-1]
        group.link_child(collection, host_collection)
    # else:
    #     host_collection = group.top_collection
    #     group.link_child(collection, host_collection)


def meta_group_end():
    if len(group.next_collections) > 0:
        group.next_collection = group.next_collections.pop()
    else:
        group.next_collection = None


def meta_root_group_nxt(ldraw_node, child_node):
    if ImportOptions.meta_group:
        if ldraw_node.is_root and child_node.meta_command != "group_nxt":
            if group.end_next_collection:
                group.next_collection = None


def meta_leocad_camera(child_node, matrix):
    global cameras
    global camera

    clean_line = child_node.line
    _params = clean_line.lower().split()[3:]

    if camera is None:
        camera = ldraw_camera.LDrawCamera()

    # https://www.leocad.org/docs/meta.html
    # "Camera commands can be grouped in the same line"
    # _params = _params[1:] at the end bumps promotes _params[2] to _params[1]
    while len(_params) > 0:
        if _params[0] == "fov":
            camera.fov = float(_params[1])
            _params = _params[2:]
        elif _params[0] == "znear":
            camera.z_near = float(_params[1])
            _params = _params[2:]
        elif _params[0] == "zfar":
            camera.z_far = float(_params[1])
            _params = _params[2:]
        elif _params[0] == "position":
            (x, y, z) = map(float, _params[1:4])
            vector = matrix @ mathutils.Vector((x, y, z)) @ matrices.rotation_matrix
            camera.position = vector
            _params = _params[4:]
        elif _params[0] == "target_position":
            (x, y, z) = map(float, _params[1:4])
            vector = matrix @ mathutils.Vector((x, y, z)) @ matrices.rotation_matrix
            camera.target_position = vector
            _params = _params[4:]
        elif _params[0] == "up_vector":
            (x, y, z) = map(float, _params[1:4])
            vector = matrix @ mathutils.Vector((x, y, z)) @ matrices.rotation_matrix
            camera.up_vector = vector
            _params = _params[4:]
        elif _params[0] == "orthographic":
            camera.orthographic = True
            _params = _params[1:]
        elif _params[0] == "hidden":
            camera.hidden = True
            _params = _params[1:]
        elif _params[0] == "name":
            # "0 !LEOCAD CAMERA NAME Camera  2".split("NAME ")[1] => "Camera  2"
            # "NAME Camera  2".split("NAME ")[1] => "Camera  2"
            name_args = clean_line.split("NAME ")
            camera.name = name_args[1]

            # By definition this is the last of the parameters
            _params = []

            cameras.append(camera)
            camera = None
        else:
            _params = _params[1:]


# syntax: <pngfile> [GLOSSMAP pngfile2] -- the GLOSSMAP keyword sits between the two
# filenames; quoted filenames with spaces are handled by the csv parse
def __parse_texmap_filenames(params_str):
    texture_params = helpers.parse_csv_line(params_str)
    image_name = texture_params[0]
    glossmap_image_name = None
    if len(texture_params) > 2 and texture_params[1] == "GLOSSMAP":
        glossmap_image_name = texture_params[2]
    return image_name, glossmap_image_name


# https://www.ldraw.org/documentation/ldraw-org-file-format-standards/language-extension-for-texture-mapping.html
def meta_texmap(clean_line, matrix, texmaps, texmap, texmap_start, texmap_next, texmap_fallback):
    if not ImportOptions.meta_texmap:
        return texmap, texmap_start, texmap_next, texmap_fallback

    if clean_line == "0 !TEXMAP FALLBACK":
        if texmap_start:
            texmap_fallback = True
    elif clean_line == "0 !TEXMAP END":
        # END pairs with a START in this file; a NEXT ends implicitly after its geometry line
        if texmap_start:
            texmap, texmap_start, texmap_next, texmap_fallback = set_texmap_end(texmaps)
    elif texmap_fallback:
        # everything between FALLBACK and END exists for non-TEXMAP renderers --
        # ignore any nested !TEXMAP commands there
        pass
    elif clean_line.startswith("0 !TEXMAP START ") or clean_line.startswith("0 !TEXMAP NEXT "):
        is_next = clean_line.startswith("0 !TEXMAP NEXT ")

        method = clean_line.split()[3]

        new_texmap = TexMap(method=method)
        if new_texmap.is_planar():
            _params = clean_line.split(maxsplit=13)  # planar

            (x1, y1, z1, x2, y2, z2, x3, y3, z3) = map(float, _params[4:13])

            new_texmap.parameters = [
                matrix @ mathutils.Vector((x1, y1, z1)),
                matrix @ mathutils.Vector((x2, y2, z2)),
                matrix @ mathutils.Vector((x3, y3, z3)),
            ]
            new_texmap.image_name, new_texmap.glossmap_image_name = __parse_texmap_filenames(_params[13])
        elif new_texmap.is_cylindrical():
            _params = clean_line.split(maxsplit=14)  # cylindrical

            (x1, y1, z1, x2, y2, z2, x3, y3, z3, a) = map(float, _params[4:14])

            new_texmap.parameters = [
                matrix @ mathutils.Vector((x1, y1, z1)),
                matrix @ mathutils.Vector((x2, y2, z2)),
                matrix @ mathutils.Vector((x3, y3, z3)),
                a,
            ]
            new_texmap.image_name, new_texmap.glossmap_image_name = __parse_texmap_filenames(_params[14])
        elif new_texmap.is_spherical():
            _params = clean_line.split(maxsplit=15)  # spherical

            (x1, y1, z1, x2, y2, z2, x3, y3, z3, a, b) = map(float, _params[4:15])

            new_texmap.parameters = [
                matrix @ mathutils.Vector((x1, y1, z1)),
                matrix @ mathutils.Vector((x2, y2, z2)),
                matrix @ mathutils.Vector((x3, y3, z3)),
                a,
                b,
            ]
            new_texmap.image_name, new_texmap.glossmap_image_name = __parse_texmap_filenames(_params[15])

        # spec: "If another texture is currently in use, it is pushed onto a stack for
        # retrieval when an END command is given." Save enough state to restore the outer
        # section when this texture ends (via END, or implicitly after NEXT's geometry line)
        if texmap is not None:
            texmaps.append((texmap, texmap_start, texmap_fallback))
        texmap = new_texmap
        if is_next:
            texmap_next = True
        else:
            texmap_start = True
        texmap_fallback = False

    return texmap, texmap_start, texmap_next, texmap_fallback


def set_texmap_end(texmaps):
    # restore the enclosing texture section, if any (the stack holds
    # (texmap, texmap_start, texmap_fallback) tuples pushed by meta_texmap)
    if len(texmaps) > 0:
        texmap, texmap_start, texmap_fallback = texmaps.pop()
    else:
        texmap = None
        texmap_start = False
        texmap_fallback = False

    texmap_next = False

    return texmap, texmap_start, texmap_next, texmap_fallback


# PE_TEX_INFO PNGBASE64== is applied to all lines, including subfiles, that have uv coordinates, should only follow path -1
# PE_TEX_INFO x,y,z,a,b,c,d,e,f,g,h,i,bl/tl,tr/br PNGBASE64== defines a bounding box and its transformation. intersection determines how the uvs will be unwrapped
# multiple PE_TEX_INFO will only respect the most recent one
# if no matrix, identity @ rotation?

# https://github.com/ScanMountGoat/ldr_tools_blender/issues/31#issuecomment-2161285322
# PE_TEX_PATH is the nth line of types 1,3,4
# can be any number of subfile lines - n n n n
# each n is the nth 1,3,4 at that line in that file of the hierarchy
# if final number is a subfile, treat it like a -1 for that file
# if final number is a polygon, apply it to that polygon
# what do we do when there is a tex_path -1 alongside tex_path >= 0?
# how do we handle instances of 0, 0 1, 0 2, 0 1 2 - overlap?

# ALL FIXED:
# these parts don't render correctly - examples\bad_import
# 4181pb014.dat - 23 is misplaced, has something to do with having 0 1 and 0 2 path
# 15068pb046a.dat - texture is smeared, has something to do with PE_TEX_NEXT_SHEAR
# 10202pb021.dat - texture shows on top and bottom and the entire under side, has something to do with having a 0 and -1 path
# 10202pb022.dat - texture shows on top and bottom and sides, has something to do with having a 0 and -1 path
# x.dat - multiple rendering errors, likely due to PE_TEX_NEXT_SHEAR and overlapping paths
# STILL NOT WORKING CORRECTLY:
# bl_36036pb045.dat - texture shows on the inside of the part because the projection is being done before the part is complete

# apply to all lines (polygons only?) of this file and subfiles that have uv coordinates in their polygon definitions
# 0 PE_TEX_PATH -1
# 0 PE_TEX_INFO PNGBASE64==

# the same function as -1 but for the subfile at line 0
# 0 PE_TEX_PATH 0
# 0 PE_TEX_INFO PNGBASE64==

# for the subfile at index 5, then at index 0 of that subfile
# 0 PE_TEX_PATH 5 0
# 0 PE_TEX_INFO -0.5346 -0.1464 2.2554 3.1670 0.8638 -1.5619 2.4660 -0.0307 -2.4765 12.9236 -0.0535 13.1611 -4.1933 16.2951 8.3761 3.6621 PNGBASE64==

# for the subfile at index 5, then at index 4 of that subfile, apply a shear matrix
# 0 PE_TEX_PATH 5 4
# 0 PE_TEX_NEXT_SHEAR
# 0 PE_TEX_INFO 0.6682 7.2554 13.4921 -3.9588 -1.0797 1.9523 -40.5715 0.2365 -24.6051 -16.5249 0.2054 16.5954 15.5934 18.4983 19.7776 12.8449 PNGBASE64==

# this doesn't work well with some very distorted texture applications
# PE_TEX_NEXT_SHEAR is unknown
# this may be where PE_TEX_NEXT_SHEAR comes in
# is there a hardcoded or programmatically determined shear matrix?
