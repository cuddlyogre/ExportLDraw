import os

import bpy
import mathutils

from . import filesystem
from . import matrices

from .ldraw_geometry import LDrawGeometry
from .face_info import FaceInfo
from .blender_materials import BlenderMaterials


class LDrawNode:
    node_cache = {}
    mesh_cache = {}

    def __init__(self, filename, color_code="16", matrix=matrices.identity, bfc_cull=True, bfc_inverted=False):
        self.filename = filename
        self.file = None
        self.color_code = color_code
        self.matrix = matrix
        self.bfc_cull = bfc_cull
        self.bfc_inverted = bfc_inverted
        self.top = False

    def load(self, parent_matrix=matrices.identity, parent_color_code="16", arr=None, indent=0, geometry=None):
        if self.filename in LDrawNode.node_cache:
            self.file = LDrawNode.node_cache[self.filename]
        else:
            self.file = LDrawFile(self.filename)
            LDrawNode.node_cache[self.filename] = self.file

        # ['part', 'unofficial_part', 'unofficial_shortcut', 'shortcut', 'primitive', 'subpart']
        if self.file.part_type in ['part', 'unofficial_part', 'shortcut', 'unofficial_shortcut'] and geometry is None:
            geometry = LDrawGeometry()
            self.top = True

        if self.color_code != "16":
            parent_color_code = self.color_code

        if self.top:
            matrix = parent_matrix
        else:
            matrix = parent_matrix @ self.matrix

        if geometry is not None:
            geometry.vertices.extend([matrix @ e for e in self.file.geometry.vertices])
            geometry.edges.extend([matrix @ e for e in self.file.geometry.edges])
            geometry.faces.extend(self.file.geometry.faces)

            new_face_info = []
            for face_info in self.file.geometry.face_info:
                copy = FaceInfo(color_code=parent_color_code, cull=face_info.cull, ccw=face_info.ccw)
                if face_info.color_code != "16":
                    copy.color_code = face_info.color_code
                new_face_info.append(copy)

            geometry.face_info.extend(new_face_info)

        for child in self.file.child_nodes:
            child.load(parent_matrix=matrix, parent_color_code=parent_color_code, indent=indent + 1, arr=arr, geometry=geometry)

        if self.top:
            if self.filename in LDrawNode.mesh_cache:
                mesh_data = LDrawNode.mesh_cache[self.filename]
            else:
                vertices = [v.to_tuple() for v in geometry.vertices]

                faces = []
                face_index = 0
                for f in geometry.faces:
                    new_face = []
                    for _ in f:
                        new_face.append(face_index)
                        face_index += 1
                    faces.append(new_face)

                mesh_data = {"vertices": vertices, "faces": faces}
                LDrawNode.mesh_cache[self.filename] = mesh_data

            mesh = bpy.data.meshes.new(self.filename)
            mesh.from_pydata(mesh_data["vertices"], [], mesh_data["faces"])
            mesh.validate()
            mesh.update()

            obj = bpy.data.objects.new(self.filename, mesh)

            for i, f in enumerate(obj.data.polygons):
                face_info = geometry.face_info[i]
                material = BlenderMaterials.get_material(face_info.color_code)
                if obj.data.materials.get(material.name) is None:
                    obj.data.materials.append(material)
                f.material_index = obj.data.materials.find(material.name)

            obj.matrix_world = matrices.rotation @ self.matrix
            bpy.context.scene.collection.objects.link(obj)


class LDrawFile:
    def __init__(self, filepath):
        self.filepath = filesystem.locate(filepath)
        self.child_nodes = []
        self.geometry = LDrawGeometry()
        self.part_type = None
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
                    self.part_type = params[2].lower()
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
                    can_cull_child_node = (bfc_certified or self.part_type in ['part', 'unofficial_part']) and bfc_local_cull and det != 0

                    ldraw_node = LDrawNode(filename, color_code=color_code, matrix=matrix, bfc_cull=can_cull_child_node, bfc_inverted=bfc_invert_next)

                    self.child_nodes.append(ldraw_node)
                elif params[0] == "2":
                    self.geometry.parse_edge(params)
                elif params[0] in ["3", "4"]:
                    bfc_cull = bfc_certified and bfc_local_cull
                    self.geometry.parse_face(params, bfc_cull, bfc_winding_ccw)

                bfc_invert_next = False
