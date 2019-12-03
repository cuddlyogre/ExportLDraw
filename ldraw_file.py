import bpy
import mathutils
import bmesh

from . import filesystem
from . import matrices

from .ldraw_geometry import LDrawGeometry
from .face_info import FaceInfo
from .blender_materials import BlenderMaterials
from .special_bricks import SpecialBricks


class LDrawNode:
    file_cache = {}
    face_info_cache = {}
    geometry_cache = {}
    parse_edges = False
    make_gaps = True
    gap_scale = 0.997

    def __init__(self, filename, color_code="16", matrix=matrices.identity, bfc_cull=True, bfc_inverted=False):
        self.filename = filename
        self.file = None
        self.color_code = color_code
        self.matrix = matrix
        self.bfc_cull = bfc_cull
        self.bfc_inverted = bfc_inverted
        self.top = False

    def load(self, parent_matrix=matrices.identity, parent_color_code="16", arr=None, geometry=None, is_stud=False, is_edge_logo=False):
        if self.filename not in LDrawNode.file_cache:
            ldraw_file = LDrawFile(self.filename)
            ldraw_file.parse_file()
            LDrawNode.file_cache[self.filename] = ldraw_file
        self.file = LDrawNode.file_cache[self.filename]

        if self.file.name in ["stud.dat", "stud2.dat"]:
            is_stud = True

        # ["logo.dat", "logo2.dat", "logo3.dat", "logo4.dat", "logo5.dat"]
        if self.file.name in ["logo.dat", "logo2.dat"]:
            is_edge_logo = True

        if self.color_code != "16":
            parent_color_code = self.color_code
        key = f"{parent_color_code}_{self.file.name}"

        part_types = ['part', 'unofficial_part', 'unofficial_shortcut', 'shortcut', 'primitive', 'subpart']
        part_types = ['part', 'unofficial_part']  # very fast, misses primitives in shortcut files, splits shortcuts into multiple parts - shortcut_geometry
        part_types = ['part', 'unofficial_part', 'shortcut', 'unofficial_shortcut']
        is_part = self.file.part_type in part_types
        if is_part and geometry is None:
            self.top = True
            print(key)
            if key in LDrawNode.geometry_cache:
                geometry = LDrawNode.geometry_cache[key]
            else:
                geometry = LDrawGeometry()

            matrix = matrices.identity
        else:
            matrix = parent_matrix @ self.matrix

        if key not in LDrawNode.geometry_cache:
            if geometry is not None:
                if LDrawNode.parse_edges or (LDrawFile.display_logo and is_edge_logo):
                    geometry.edge_vertices.extend([matrix @ e for e in self.file.geometry.edge_vertices])
                    geometry.edge_faces.extend(self.file.geometry.edge_faces)

                geometry.vertices.extend([matrix @ e for e in self.file.geometry.vertices])
                geometry.faces.extend(self.file.geometry.faces)

                if key not in LDrawNode.face_info_cache:
                    new_face_info = []
                    for face_info in self.file.geometry.face_info:
                        copy = FaceInfo(color_code=parent_color_code,
                                        cull=face_info.cull,
                                        ccw=face_info.ccw,
                                        grain_slope_allowed=not is_stud)
                        if face_info.color_code != "16":
                            copy.color_code = face_info.color_code
                        new_face_info.append(copy)
                    LDrawNode.face_info_cache[key] = new_face_info

                new_face_info = LDrawNode.face_info_cache[key]
                geometry.face_info.extend(new_face_info)

            for child in self.file.child_nodes:
                child.load(parent_matrix=matrix,
                           parent_color_code=parent_color_code,
                           arr=arr,
                           geometry=geometry,
                           is_stud=is_stud,
                           is_edge_logo=is_edge_logo)

        if self.top:
            LDrawNode.geometry_cache[key] = geometry

            if key not in bpy.data.meshes:
                mesh = self.create_mesh(key, geometry)
                mesh.use_auto_smooth = True
                self.apply_materials(mesh, geometry)
                self.bmesh_ops(mesh)
                if LDrawNode.make_gaps:
                    self.do_gaps(mesh)

            mesh = bpy.data.meshes[key]
            obj = bpy.data.objects.new(key, mesh)
            obj.matrix_world = matrices.rotation @ parent_matrix @ self.matrix
            self.get_collection('Parts').objects.link(obj)

            edge_key = f"{self.file.name}"
            if edge_key not in bpy.data.meshes:
                self.create_edge_mesh(edge_key, geometry)

            if edge_key in bpy.data.meshes:
                edge_mesh = bpy.data.meshes[edge_key]
                edge_obj = bpy.data.objects.new(edge_key, edge_mesh)
                # edge_obj.matrix_world = matrices.rotation @ self.matrix
                edge_obj.parent = obj
                self.get_collection('Edges').objects.link(edge_obj)

            color_data = BlenderMaterials.get_color_data(parent_color_code)
            if color_data is not None:
                pass
                # print(color_data['edge_color'])

    def create_edge_mesh(self, key, geometry):
        if len(geometry.edge_vertices) < 1:
            return None

        vertices = [v.to_tuple() for v in geometry.edge_vertices]
        faces = []
        face_index = 0

        for f in geometry.edge_faces:
            new_face = []
            for _ in range(f):
                new_face.append(face_index)
                face_index += 1
            faces.append(new_face)

        mesh = bpy.data.meshes.new(key)
        mesh.from_pydata(vertices, [], faces)
        mesh.validate()
        mesh.update()

        return mesh

    def create_mesh(self, key, geometry):
        vertices = [v.to_tuple() for v in geometry.vertices]
        faces = []
        face_index = 0

        for f in geometry.faces:
            new_face = []
            for _ in range(f):
                new_face.append(face_index)
                face_index += 1
            faces.append(new_face)

        mesh = bpy.data.meshes.new(key)
        mesh.from_pydata(vertices, [], faces)
        mesh.validate()
        mesh.update()

        return mesh

    @staticmethod
    def get_collection(name):
        if name not in bpy.data.collections:
            bpy.data.collections.new(name)
        return bpy.data.collections[name]

    def edge_gp(self, mesh, parent_obj):
        key = self.file.name
        edge_obj = bpy.data.objects.new(f"e_{key}", mesh)
        edge_obj.matrix_world = matrices.rotation @ self.matrix
        bpy.context.scene.collection.objects.link(edge_obj)

        gpd = bpy.data.grease_pencils.new('gp')
        gpd.pixel_factor = 5.0
        gpd.stroke_depth_order = '3D'

        material = self.get_material('black')
        # https://developer.blender.org/T67102
        bpy.data.materials.create_gpencil_data(material)
        gpd.materials.append(material)

        gpl = gpd.layers.new('gpl')
        gpf = gpl.frames.new(1)
        gpl.active_frame = gpf

        for e in mesh.edges:
            gps = gpf.strokes.new()
            gps.material_index = 0
            gps.line_width = 10.0
            for v in e.vertices:
                i = len(gps.points)
                gps.points.add(1)
                gpp = gps.points[i]
                gpp.co = mesh.vertices[v].co

        gpo = bpy.data.objects.new('gpo', gpd)
        gpo.active_material = material
        gpo.parent = parent_obj
        self.get_collection('Edges').objects.link(gpo)

        bpy.data.meshes.remove(mesh)

    # https://blender.stackexchange.com/a/91687
    # for f in bm.faces:
    #     f.smooth = True
    # mesh = context.object.data
    # for f in mesh.polygons:
    #     f.use_smooth = True
    # values = [True] * len(mesh.polygons)
    # mesh.polygons.foreach_set("use_smooth", values)
    def apply_materials(self, mesh, geometry):
        # bpy.context.object.active_material.use_backface_culling = True
        # bpy.context.object.active_material.use_screen_refraction = True

        for i, f in enumerate(mesh.polygons):
            face_info = geometry.face_info[i]

            is_slope_material = False
            if face_info.grain_slope_allowed:
                is_slope_material = SpecialBricks.is_slope_face(self.file.name, f)

            material = BlenderMaterials.get_material(face_info.color_code, is_slope_material=is_slope_material)
            if material.name not in mesh.materials:
                mesh.materials.append(material)
            f.material_index = mesh.materials.find(material.name)
            f.use_smooth = True

    def bmesh_ops(self, mesh):
        bm = bmesh.new()
        bm.from_mesh(mesh)
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
        bm.to_mesh(mesh)
        bm.clear()
        bm.free()

    def do_gaps(self, mesh):
        scale = LDrawNode.gap_scale
        gaps_scale_matrix = mathutils.Matrix((
            (scale, 0.0, 0.0, 0.0),
            (0.0, scale, 0.0, 0.0),
            (0.0, 0.0, scale, 0.0),
            (0.0, 0.0, 0.0, 1.0)
        ))
        mesh.transform(gaps_scale_matrix)


class LDrawFile:
    display_logo = False
    chosen_logo = None

    def __init__(self, filepath):
        self.filepath = filepath
        self.name = ""
        self.child_nodes = []
        self.geometry = LDrawGeometry()
        self.part_type = None
        self.lines = None

    def parse_file(self):
        bfc_certified = False
        bfc_winding_ccw = False
        bfc_local_cull = False
        bfc_invert_next = False

        if self.lines is None:
            # if missing, use a,b,c etc parts if available
            filepath = filesystem.locate(self.filepath)
            if filepath is None:
                return
            self.lines = filesystem.read_file(filepath)

        for line in self.lines:
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
                    # print(self.name)
            else:
                if params[0] == "1":
                    color_code = params[1]

                    (x, y, z, a, b, c, d, e, f, g, h, i) = map(float, params[2:14])
                    matrix = mathutils.Matrix(((a, b, c, x), (d, e, f, y), (g, h, i, z), (0, 0, 0, 1)))

                    # https://www.ldraw.org/article/415.html
                    det = matrix.determinant()
                    if det < 0:
                        bfc_invert_next = not bfc_invert_next

                    can_cull_child_node = (bfc_certified or self.part_type in ['part', 'unofficial_part']) and bfc_local_cull and det != 0

                    filename = " ".join(params[14:])

                    if LDrawFile.display_logo:
                        if filename in SpecialBricks.studs:
                            parts = filename.split(".")
                            name = parts[0]
                            ext = parts[1]
                            new_filename = f"{name}-{LDrawFile.chosen_logo}.{ext}"
                            if filesystem.locate(new_filename):
                                filename = new_filename

                    # print(f"{filename} children")
                    ldraw_node = LDrawNode(filename, color_code=color_code, matrix=matrix, bfc_cull=can_cull_child_node, bfc_inverted=bfc_invert_next)

                    self.child_nodes.append(ldraw_node)
                elif params[0] in ["2"]:
                    self.geometry.parse_edge(params)
                elif params[0] in ["3", "4"]:
                    bfc_cull = bfc_certified and bfc_local_cull
                    self.geometry.parse_face(params, bfc_cull, bfc_winding_ccw)

                bfc_invert_next = False
