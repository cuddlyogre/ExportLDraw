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
    files = {}
    file_cache = {}
    face_info_cache = {}
    geometry_cache = {}
    make_gaps = True
    gap_scale = 0.997
    remove_doubles = True
    shade_smooth = True
    current_group = None
    debug_text = False
    no_studs = False
    bevel_edges = False

    def __init__(self, filename, color_code="16", matrix=matrices.identity):
        self.filename = filename.lower()
        self.file = None
        self.color_code = color_code
        self.matrix = matrix
        self.top = False

    def load(self, parent_matrix=matrices.identity, parent_color_code="16", arr=None, geometry=None, is_stud=False, is_edge_logo=False, current_group=None):
        if self.filename not in LDrawNode.file_cache:
            if self.filename in LDrawNode.files:
                ldraw_file = LDrawNode.files[self.filename]
            else:
                ldraw_file = LDrawFile(self.filename)
            ldraw_file.parse_file()
            LDrawNode.file_cache[self.filename] = ldraw_file
        self.file = LDrawNode.file_cache[self.filename]

        if self.file.name in ["stud.dat", "stud2.dat"]:
            is_stud = True

        if LDrawNode.no_studs and self.file.name.startswith("stud"):
            return

        # ["logo.dat", "logo2.dat", "logo3.dat", "logo4.dat", "logo5.dat"]
        if self.file.name in ["logo.dat", "logo2.dat"]:
            is_edge_logo = True

        model_types = ['model', 'unofficial_model']
        is_model = self.file.part_type in model_types

        part_types = ['part', 'unofficial_part', 'unofficial_shortcut', 'shortcut', 'primitive', 'subpart']
        part_types = ['part', 'unofficial_part']  # very fast, misses primitives in shortcut files, splits shortcuts into multiple parts - shortcut_geometry
        part_types = ['part', 'unofficial_part', 'shortcut', 'unofficial_shortcut']
        is_part = self.file.part_type in part_types

        if self.color_code != "16":
            parent_color_code = self.color_code
        key = f"{parent_color_code}_{self.file.name}"

        matrix = parent_matrix @ self.matrix

        if is_model:
            if LDrawNode.debug_text:
                print("===========")
                print("is_model")
                print(self.file.name)
                print("===========")

            if self.file.name not in bpy.data.collections:
                bpy.data.collections.new(self.file.name)
            current_group = bpy.data.collections[self.file.name]

            if LDrawNode.current_group is not None:
                if current_group.name not in LDrawNode.current_group.children:
                    LDrawNode.current_group.children.link(current_group)
            else:
                LDrawNode.current_group = current_group

        elif is_part and geometry is None:
            if LDrawNode.debug_text:
                print("===========")
                print("is_part")
                print(self.file.name)
                print("===========")

            self.top = True

            if key not in LDrawNode.geometry_cache:
                geometry = LDrawGeometry()
            else:
                geometry = LDrawNode.geometry_cache[key]

            matrix = matrices.identity
        else:
            if LDrawNode.debug_text:
                print("===========")
                print("is_subpart")
                print(self.file.name)
                print("===========")

        if key not in LDrawNode.geometry_cache:
            if geometry is not None:
                if (not is_edge_logo) or (is_edge_logo and LDrawFile.display_logo):
                    for edge in self.file.geometry.edges:
                        geometry.edges.append((matrix @ edge[0], matrix @ edge[1]))

                geometry.vertices.extend([matrix @ e for e in self.file.geometry.vertices])
                geometry.faces.extend(self.file.geometry.faces)

                new_face_info = []
                if key not in LDrawNode.face_info_cache:
                    for i, face_info in enumerate(self.file.geometry.face_info):
                        copy = FaceInfo(color_code=parent_color_code,
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
                           is_edge_logo=is_edge_logo,
                           current_group=current_group)

        if self.top:
            # LDrawNode.geometry_cache[key] = geometry

            if key not in bpy.data.meshes:
                mesh = self.create_mesh(key, geometry)  # combine with apply_materials
                self.apply_materials(mesh, geometry)  # combine with create_mesh

                mesh.use_auto_smooth = LDrawNode.shade_smooth

                self.bmesh_ops(mesh, geometry)

                if LDrawNode.make_gaps:
                    self.do_gaps(mesh)

            mesh = bpy.data.meshes[key]
            obj = bpy.data.objects.new(key, mesh)
            obj.matrix_world = matrices.rotation @ parent_matrix @ self.matrix

            if current_group is not None:
                current_group.objects.link(obj)
            else:
                bpy.context.scene.collection.objects.link(obj)

            if False:
                edge_modifier = obj.modifiers.new("Edge Split", type='EDGE_SPLIT')
                edge_modifier.use_edge_angle = False
                edge_modifier.use_edge_sharp = True

            if LDrawNode.bevel_edges:
                bevel_modifier = obj.modifiers.new("Bevel", type='BEVEL')
                bevel_modifier.width = 0.10
                bevel_modifier.segments = 4
                bevel_modifier.profile = 0.5
                bevel_modifier.limit_method = 'WEIGHT'
                bevel_modifier.use_clamp_overlap = True

            # for m in obj.modifiers:
            #     if m.type == 'EDGE_SPLIT':
            #         obj.modifiers.remove(m)

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

    def bmesh_ops(self, mesh, geometry):
        if LDrawNode.bevel_edges:
            mesh.use_customdata_edge_bevel = True

        bm = bmesh.new()
        bm.from_mesh(mesh)

        bm.faces.ensure_lookup_table()
        bm.verts.ensure_lookup_table()
        bm.edges.ensure_lookup_table()

        weld_distance = 0.10
        if LDrawNode.remove_doubles:
            bmesh.ops.remove_doubles(bm, verts=bm.verts[:], dist=weld_distance)

        bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])

        # Create kd tree for fast "find nearest points" calculation
        kd = mathutils.kdtree.KDTree(len(bm.verts))
        for i, v in enumerate(bm.verts):
            kd.insert(v.co, i)
        kd.balance()
        # Create edgeIndices dictionary, which is the list of edges as pairs of indicies into our bm.verts array
        edge_indices = {}
        for ind, edge in enumerate(geometry.edges):
            # print(edge)
            # Find index of nearest points in bm.verts to geomEdge[0] and geomEdge[1]
            edges0 = [index for (co, index, dist) in kd.find_range(edge[0], weld_distance)]
            edges1 = [index for (co, index, dist) in kd.find_range(edge[1], weld_distance)]

            for e0 in edges0:
                for e1 in edges1:
                    edge_indices[(e0, e1)] = True
                    edge_indices[(e1, e0)] = True

        # Find layer for bevel weights
        if 'BevelWeight' in bm.edges.layers.bevel_weight:
            bevel_weight_layer = bm.edges.layers.bevel_weight['BevelWeight']
        else:
            bevel_weight_layer = None

        # Find the appropriate mesh edges and make them sharp (i.e. not smooth)
        for edge in bm.edges:
            v0 = edge.verts[0].index
            v1 = edge.verts[1].index
            if (v0, v1) in edge_indices:
                # Make edge sharp
                edge.smooth = False

                # Add bevel weight
                if bevel_weight_layer is not None:
                    bevel_wight = 1.0
                    edge[bevel_weight_layer] = bevel_wight

        bm.faces.ensure_lookup_table()
        bm.verts.ensure_lookup_table()
        bm.edges.ensure_lookup_table()

        bm.to_mesh(mesh)

        bm.clear()
        bm.free()

    @staticmethod
    def get_collection(name):
        if name not in bpy.data.collections:
            bpy.data.collections.new(name)
        return bpy.data.collections[name]

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

            # TODO: LDrawColors.use_alt_colors use f"{face_info.color_code}_alt"
            material = BlenderMaterials.get_material(face_info.color_code, is_slope_material=is_slope_material)
            if material.name not in mesh.materials:
                mesh.materials.append(material)
            f.material_index = mesh.materials.find(material.name)
            f.use_smooth = LDrawNode.shade_smooth

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
                elif params[1].lower() == "name:":
                    self.name = line[7:].lower().strip()
                    # print(self.name)
            else:
                if params[0] == "1":
                    color_code = params[1]

                    (x, y, z, a, b, c, d, e, f, g, h, i) = map(float, params[2:14])
                    matrix = mathutils.Matrix(((a, b, c, x), (d, e, f, y), (g, h, i, z), (0, 0, 0, 1)))

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
                    ldraw_node = LDrawNode(filename, color_code=color_code, matrix=matrix)

                    self.child_nodes.append(ldraw_node)
                elif params[0] in ["2", "3", "4"]:
                    if self.part_type is None:
                        self.part_type = 'part'

                    if params[0] in ["2"]:
                        self.geometry.parse_edge(params)
                    elif params[0] in ["3", "4"]:
                        self.geometry.parse_face(params)
