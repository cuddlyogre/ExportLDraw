import os

import bpy
import mathutils
import bmesh
import math

from . import filesystem
from . import matrices

from .ldraw_geometry import LDrawGeometry
from .face_info import FaceInfo
from .blender_materials import BlenderMaterials
from .special_bricks import SpecialBricks


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

    def load(self, parent_matrix=matrices.identity, parent_color_code="16", arr=None, indent=0, geometry=None, is_stud=False):
        if self.filename in LDrawNode.node_cache:
            self.file = LDrawNode.node_cache[self.filename]
        else:
            self.file = LDrawFile(self.filename)
            LDrawNode.node_cache[self.filename] = self.file

        if self.file.is_stud:
            is_stud = True

        # ['part', 'unofficial_part', 'unofficial_shortcut', 'shortcut', 'primitive', 'subpart']
        is_part = self.file.part_type in ['part', 'unofficial_part', 'shortcut', 'unofficial_shortcut']
        if is_part and geometry is None:
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
                copy = FaceInfo(color_code=parent_color_code, cull=face_info.cull, ccw=face_info.ccw, grain_slope_allowed=not self.file.is_stud)
                if face_info.color_code != "16":
                    copy.color_code = face_info.color_code
                new_face_info.append(copy)

            geometry.face_info.extend(new_face_info)

        for child in self.file.child_nodes:
            child.load(parent_matrix=matrix, parent_color_code=parent_color_code, indent=indent + 1, arr=arr, geometry=geometry, is_stud=is_stud)

        if self.top:
            vertices = [v.to_tuple() for v in geometry.vertices]
            edges = [v.to_tuple() for v in geometry.edges]

            faces = []
            face_index = 0
            for f in geometry.faces:
                new_face = []
                for _ in f:
                    new_face.append(face_index)
                    face_index += 1
                faces.append(new_face)

            mesh = bpy.data.meshes.new(self.file.name)
            mesh.from_pydata(vertices, [], faces)
            mesh.validate()
            mesh.update()

            obj = bpy.data.objects.new(self.file.name, mesh)

            for i, f in enumerate(obj.data.polygons):
                face_info = geometry.face_info[i]

                is_slope_material = False
                if face_info.grain_slope_allowed:
                    is_slope_material = SpecialBricks.is_slope_face(self.file.name, f)

                material = BlenderMaterials.get_material(face_info.color_code, is_slope_material=is_slope_material)
                if obj.data.materials.get(material.name) is None:
                    obj.data.materials.append(material)
                f.material_index = obj.data.materials.find(material.name)

            bm = bmesh.new()
            bm.from_mesh(obj.data)
            bm.faces.ensure_lookup_table()
            bm.verts.ensure_lookup_table()
            bm.edges.ensure_lookup_table()

            remove_doubles = True
            if remove_doubles:
                weld_distance = 0.0005
                bmesh.ops.remove_doubles(bm, verts=bm.verts[:], dist=weld_distance)

            recalculate_normals = True
            if recalculate_normals:
                bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])

            bm.to_mesh(obj.data)
            bm.clear()
            bm.free()

            do_gaps = True
            if do_gaps:
                # Distance between gaps is controlled by Options.gapWidth
                # Gap height is set smaller than gapWidth since empirically, stacked bricks tend
                # to be pressed more tightly together
                gap_width = 0.15
                gap_height = gap_width
                obj_scale = obj.scale
                dimensions = obj.dimensions

                # Checks whether the object isn't flat in a certain direction
                # to avoid division by zero.
                # Else, the scale factor is set proportional to the inverse of
                # the dimension so that the mesh shrinks a fixed distance
                # (determined by the gap_width and the scale of the object)
                # in every direction, creating a uniform gap.
                scale_fac = mathutils.Vector((1.0, 1.0, 1.0))
                if dimensions.x != 0:
                    scale_fac.x = 1 - gap_width * abs(obj_scale.x) / dimensions.x
                if dimensions.y != 0:
                    scale_fac.y = 1 - gap_height * abs(obj_scale.y) / dimensions.y
                if dimensions.z != 0:
                    scale_fac.z = 1 - gap_width * abs(obj_scale.z) / dimensions.z

                # A safety net: Don't distort the part too much (e.g. -ve scale would not look good)
                if scale_fac.x < 0.95:
                    scale_fac.x = 0.95
                if scale_fac.y < 0.95:
                    scale_fac.y = 0.95
                if scale_fac.z < 0.95:
                    scale_fac.z = 0.95

                # Scale all vertices in the mesh
                gaps_scale_matrix = mathutils.Matrix((
                    (scale_fac.x, 0.0, 0.0, 0.0),
                    (0.0, scale_fac.y, 0.0, 0.0),
                    (0.0, 0.0, scale_fac.z, 0.0),
                    (0.0, 0.0, 0.0, 1.0)
                ))
                obj.data.transform(gaps_scale_matrix)

            # TODO: add obj to list and add at the end
            bpy.context.scene.collection.objects.link(obj)

            obj.select_set(state=True)
            bpy.context.view_layer.objects.active = obj
            bpy.ops.object.shade_smooth()
            obj.select_set(state=False)
            bpy.context.view_layer.objects.active = None

            # bpy.context.scene.collection.objects.unlink(obj)

            # Add Bevel modifier to each instance
            add_bevel_modifier = False
            bevel_width = 0.5
            import_scale = 1.0
            if add_bevel_modifier:
                bevel_modifier = obj.modifiers.new("Bevel", type='BEVEL')
                bevel_modifier.width = bevel_width * import_scale
                bevel_modifier.segments = 4
                bevel_modifier.profile = 0.5
                bevel_modifier.limit_method = 'WEIGHT'
                bevel_modifier.use_clamp_overlap = True

            edge_split = True
            # Add edge split modifier to each instance
            if edge_split:
                edge_modifier = obj.modifiers.new("Edge Split", type='EDGE_SPLIT')
                edge_modifier.use_edge_sharp = True
                edge_modifier.split_angle = math.radians(30.0)

            obj.matrix_world = matrices.rotation @ self.matrix


class LDrawFile:
    def __init__(self, filepath):
        self.filepath = filesystem.locate(filepath)
        self.name = ""
        self.is_stud = False
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

        if self.filepath is None:
            return

        # print(self.filepath)
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
                elif params[1].lower() == "name:":
                    self.name = params[2]
                    self.is_stud = self.name in ["stud.dat", "stud2.dat"]
                    print(self.name)
            else:
                if params[0] == "1":
                    color_code = params[1]

                    (x, y, z, a, b, c, d, e, f, g, h, i) = map(float, params[2:14])
                    matrix = mathutils.Matrix(((a, b, c, x), (d, e, f, y), (g, h, i, z), (0, 0, 0, 1)))

                    det = matrix.determinant()
                    if det < 0:
                        bfc_invert_next = not bfc_invert_next

                    filename = " ".join(params[14:])

                    render_logo = False
                    if render_logo:
                        used_logo = "logo3"
                        if filename in ["stud.dat", "stud2.dat"]:
                            parts = filename.split(".")
                            name = parts[0]
                            ext = parts[1]
                            new_filename = f"{name}-{used_logo}.{ext}"
                            if filesystem.locate(new_filename):
                                filename = new_filename

                    can_cull_child_node = (bfc_certified or self.part_type in ['part', 'unofficial_part']) and bfc_local_cull and det != 0

                    ldraw_node = LDrawNode(filename, color_code=color_code, matrix=matrix, bfc_cull=can_cull_child_node, bfc_inverted=bfc_invert_next)

                    self.child_nodes.append(ldraw_node)
                elif params[0] in ["2"]:
                    render_edges = False
                    self.geometry.parse_edge(params, as_face=render_edges)
                elif params[0] in ["3", "4"]:
                    bfc_cull = bfc_certified and bfc_local_cull
                    self.geometry.parse_face(params, bfc_cull, bfc_winding_ccw)

                bfc_invert_next = False
