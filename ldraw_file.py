import os

import bpy
import mathutils

from . import filesystem
from . import matrices

from .ldraw_geometry import LDrawGeometry
from .blender_materials import BlenderMaterials


class LDrawNode:
    cache = {}
    join_lists = []

    def __init__(self, filename, color_code="16", matrix=matrices.identity, bfc_cull=True, bfc_inverted=False):
        self.filename = filename
        self.file = None
        self.color_code = color_code
        self.matrix = matrix
        self.bfc_cull = bfc_cull
        self.bfc_inverted = bfc_inverted
        self.top = False

    def load(self, parent_matrix=matrices.rotation, join_list=None, parent_color_code="16", arr=None, indent=0, geometry=None):
        string = f"{'-' * indent}{self.filename}"
        print(string)

        if arr is not None:
            arr.append(string)

        if self.filename in LDrawNode.cache:
            self.file = LDrawNode.cache[self.filename]
        else:
            self.file = LDrawFile(self.filename)
            LDrawNode.cache[self.filename] = self.file

        matrix = parent_matrix @ self.matrix

        if self.file.is_part and join_list is None:
            parent_color_code = self.color_code
            join_list = []
            self.top = True

        points = [p.to_tuple() for p in self.file.geometry.verts]
        faces = self.file.geometry.faces
        mesh = bpy.data.meshes.new(self.filename)
        mesh.from_pydata(points, [], faces)
        mesh.validate()
        mesh.update()
        obj = bpy.data.objects.new(self.filename, mesh)
        if self.file.is_part:
            obj.matrix_world = matrix
        else:
            obj.data.transform(matrix)

        for i, f in enumerate(obj.data.polygons):
            face_info = self.file.geometry.face_info[i]

            if face_info.color_code == "16":
                color_code = parent_color_code
            else:
                color_code = face_info.color_code

            material = BlenderMaterials.get_material(color_code)

            if obj.data.materials.get(material.name) is None:
                obj.data.materials.append(material)
            f.material_index = obj.data.materials.find(material.name)

        if join_list is not None:
            join_list.append(obj)

        for child in self.file.child_nodes:
            child.load(parent_matrix=matrix, join_list=join_list, parent_color_code=parent_color_code, indent=indent + 1, arr=arr, geometry=geometry)

        if self.file.is_part and self.top:
            # https://blender.stackexchange.com/a/133021
            c = {}
            c["object"] = c["active_object"] = join_list[0]
            c["selected_objects"] = c["selected_editable_objects"] = join_list
            bpy.ops.object.join(c)
            bpy.context.scene.collection.objects.link(c["active_object"])


class LDrawFile:
    def __init__(self, filepath):
        self.filepath = filesystem.locate(filepath)
        self.child_nodes = []
        self.geometry = LDrawGeometry()
        self.is_part = False
        filesystem.append_search_paths(os.path.dirname(filepath))
        self.parse_file()

    def parse_file(self):
        bfc_certified = False
        bfc_winding_ccw = False
        bfc_local_cull = False
        bfc_invert_next = False

        lines = filesystem.read_file(self.filepath)
        for line in lines:
            params = line.strip().split()

            if len(params) == 0:
                continue

            while len(params) < 9:
                params.append("")

            if params[0] == "0":
                if params[1] == "!LDRAW_ORG":
                    part_type = params[2].lower()
                    self.is_part = part_type in ['part', 'unofficial_part', 'unofficial_shortcut', 'shorcut']
                elif params[1] == "BFC":
                    if params[2] == "NOCERTIFY":
                        bfc_certified = False
                    else:
                        bfc_certified = True

                    if "CW" in params:
                        bfc_winding_ccw = False
                    elif "CCW" in params:
                        bfc_winding_ccw = True
                    elif "CLIP" in params:
                        bfc_local_cull = True
                    elif "NOCLIP" in params:
                        bfc_local_cull = False
                    elif "INVERTNEXT" in params:
                        bfc_invert_next = True
            else:
                if params[0] == "1":
                    color_code = params[1]

                    (x, y, z, a, b, c, d, e, f, g, h, i) = map(float, params[2:14])
                    matrix = mathutils.Matrix(((a, b, c, x), (d, e, f, y), (g, h, i, z), (0, 0, 0, 1)))

                    det = matrix.determinant()
                    if det < 0:
                        bfc_invert_next = not bfc_invert_next

                    filename = " ".join(params[14:])
                    can_cull_child_node = (bfc_certified or self.is_part) and bfc_local_cull and det != 0

                    ldraw_node = LDrawNode(filename, color_code=color_code, matrix=matrix, bfc_cull=can_cull_child_node, bfc_inverted=bfc_invert_next)

                    self.child_nodes.append(ldraw_node)
                elif params[0] == "2":
                    self.geometry.parse_edge(params)
                elif params[0] == "3" or params[0] == "4":
                    bfc_cull = bfc_certified and bfc_local_cull
                    self.geometry.parse_face(params, bfc_cull, bfc_winding_ccw)

                bfc_invert_next = False
