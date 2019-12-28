import bpy
import mathutils
import bmesh

from . import options
from . import matrices

from .ldraw_geometry import LDrawGeometry
from .face_info import FaceInfo
from .blender_materials import BlenderMaterials
from .special_bricks import SpecialBricks


class LDrawNode:
    current_part = 0
    current_step = 0
    last_frame = 0
    face_info_cache = {}
    geometry_cache = {}
    top_group = None

    def __init__(self, file, color_code="16", matrix=matrices.identity):
        self.file = file
        self.color_code = color_code
        self.matrix = matrix
        self.top = False
        self.meta_command = None
        self.meta_args = []

    @classmethod
    def reset(cls):
        cls.current_step = 0
        if options.meta_step:
            LDrawNode.set_step()
        cls.top_group = None

    @classmethod
    def reset_caches(cls):
        cls.face_info_cache = {}
        cls.geometry_cache = {}

    @staticmethod
    def set_step():
        start_frame = options.starting_step_frame
        frame_length = options.frames_per_step
        LDrawNode.last_frame = (start_frame + frame_length) + (frame_length * LDrawNode.current_step)
        if options.set_timelime_markers:
            bpy.context.scene.timeline_markers.new('STEP', frame=LDrawNode.last_frame)

    def load(self, parent_matrix=matrices.identity, parent_color_code="16", geometry=None, is_stud=False, is_edge_logo=False, parent_group=None):
        if self.file is None:
            if self.meta_command == "step":
                LDrawNode.current_step += 1
                LDrawNode.set_step()
            elif self.meta_command == "save":
                if options.set_timelime_markers:
                    bpy.context.scene.timeline_markers.new('SAVE', frame=LDrawNode.last_frame)
            elif self.meta_command == "clear":
                if options.set_timelime_markers:
                    bpy.context.scene.timeline_markers.new('CLEAR', frame=LDrawNode.last_frame)
                if LDrawNode.top_group is not None:
                    for ob in LDrawNode.top_group.all_objects:
                        bpy.context.scene.frame_set(LDrawNode.last_frame)
                        ob.hide_viewport = True
                        ob.hide_render = True
                        ob.keyframe_insert(data_path="hide_render")
                        ob.keyframe_insert(data_path="hide_viewport")
            return

        if options.no_studs and self.file.name.startswith("stud"):
            return

        if self.color_code != "16":
            parent_color_code = self.color_code

        key = []
        key.append(options.resolution)
        key.append(parent_color_code)
        if options.display_logo:
            key.append(options.chosen_logo)
        if options.remove_doubles:
            key.append("rd")
        if options.use_alt_colors:
            key.append("alt")
        if options.curved_walls:
            key.append("c")
        if options.add_subsurface:
            key.append("ss")
        if parent_color_code == "24":
            key.append("edge")
        key.append(self.file.name)
        key = "_".join([k.lower() for k in key])

        model_types = ['model', 'unofficial_model', 'un-official model', 'submodel', None]
        is_model = self.file.part_type in model_types

        part_types = ['part', 'unofficial_part', 'un-official part']
        is_part = self.file.part_type in part_types

        shortcut_types = ['shortcut', 'unofficial_shortcut', 'un-official shortcut']
        is_shortcut = self.file.part_type in shortcut_types

        subpart_types = ['primitive', 'subpart', 'un-official primitive', 'un-official subpart']
        is_subpart = self.file.part_type in subpart_types

        matrix = parent_matrix @ self.matrix

        new_group = parent_group
        if is_model:
            if options.debug_text:
                print("===========")
                print("is_model")
                print(self.file.name)
                print("===========")

            new_group = bpy.data.collections.new(self.file.name)
            if LDrawNode.top_group is None:
                LDrawNode.top_group = new_group
                if options.debug_text:
                    print(LDrawNode.get_top_group().name)

            if parent_group is not None:
                parent_group.children.link(new_group)
        else:
            if geometry is None:
                self.top = True
                geometry = LDrawGeometry()
                matrix = matrices.identity

            if is_part:
                if options.debug_text:
                    print("===========")
                    print("is_part")
                    print(self.file.name)
                    print("===========")
            elif is_shortcut:
                if options.debug_text:
                    print("===========")
                    print("is_shortcut")
                    print(self.file.name)
                    print("===========")
            elif is_subpart:
                if options.debug_text:
                    print("===========")
                    print("is_subpart")
                    print(self.file.name)
                    print("===========")

        if self.top and is_part:
            LDrawNode.current_part += 1

        # if it's a part and already in the cache, reuse it
        # meta commands are not in self.top files which is how they are counted
        if self.top and key in LDrawNode.geometry_cache:
            geometry = LDrawNode.geometry_cache[key]
        else:
            if geometry is not None:
                if self.file.name in ["stud.dat", "stud2.dat"]:
                    is_stud = True

                # ["logo.dat", "logo2.dat", "logo3.dat", "logo4.dat", "logo5.dat"]
                if self.file.name in ["logo.dat", "logo2.dat"]:
                    is_edge_logo = True

                if key not in LDrawNode.face_info_cache:
                    new_face_info = []
                    for face_info in self.file.geometry.face_info:
                        copy = FaceInfo(color_code=parent_color_code,
                                        grain_slope_allowed=not is_stud)
                        if parent_color_code == "24":
                            copy.use_edge_color = True
                        if face_info.color_code != "16":
                            copy.color_code = face_info.color_code
                        new_face_info.append(copy)
                    LDrawNode.face_info_cache[key] = new_face_info
                new_face_info = LDrawNode.face_info_cache[key]

                vertices = [matrix @ e for e in self.file.geometry.vertices]
                geometry.vertices.extend(vertices)

                geometry.faces.extend(self.file.geometry.faces)
                geometry.face_info.extend(new_face_info)

                if (not is_edge_logo) or (is_edge_logo and options.display_logo):
                    for edge in self.file.geometry.edges:
                        geometry.edges.append((matrix @ edge[0], matrix @ edge[1]))

            for child in self.file.child_nodes:
                child.load(parent_matrix=matrix,
                           parent_color_code=parent_color_code,
                           geometry=geometry,
                           is_stud=is_stud,
                           is_edge_logo=is_edge_logo,
                           parent_group=new_group)

        if self.top:
            if key not in LDrawNode.geometry_cache:
                LDrawNode.geometry_cache[key] = geometry

            if key not in bpy.data.meshes:
                mesh = self.create_mesh(key, geometry)  # combine with apply_materials
                mesh.use_auto_smooth = options.shade_smooth
                self.apply_materials(mesh, geometry, self.file.name)  # combine with create_mesh
                self.bmesh_ops(mesh, geometry)
                if options.make_gaps:
                    self.do_gaps(mesh)
            mesh = bpy.data.meshes[key]

            obj = bpy.data.objects.new(key, mesh)
            # obj.matrix_world = parent_matrix @ self.matrix
            obj.matrix_world = matrices.rotation @ parent_matrix @ self.matrix

            # https://docs.blender.org/api/current/bpy.types.bpy_struct.html#bpy.types.bpy_struct.keyframe_insert
            # https://docs.blender.org/api/current/bpy.types.Scene.html?highlight=frame_set#bpy.types.Scene.frame_set
            # https://docs.blender.org/api/current/bpy.types.Object.html?highlight=rotation_quaternion#bpy.types.Object.rotation_quaternion
            if options.meta_step:
                if options.debug_text:
                    print(LDrawNode.current_step)

                bpy.context.scene.frame_set(options.starting_step_frame)
                obj.hide_viewport = True
                obj.hide_render = True
                obj.keyframe_insert(data_path="hide_render")
                obj.keyframe_insert(data_path="hide_viewport")

                bpy.context.scene.frame_set(LDrawNode.last_frame)
                obj.hide_viewport = False
                obj.hide_render = False
                obj.keyframe_insert(data_path="hide_render")
                obj.keyframe_insert(data_path="hide_viewport")

                if options.debug_text:
                    print(LDrawNode.last_frame)

            if new_group is not None:
                new_group.objects.link(obj)
            else:
                bpy.context.scene.collection.objects.link(obj)

            if False:
                edge_modifier = obj.modifiers.new("Edge Split", type='EDGE_SPLIT')
                edge_modifier.use_edge_angle = False
                edge_modifier.use_edge_sharp = True

            if options.bevel_edges:
                bevel_modifier = obj.modifiers.new("Bevel", type='BEVEL')
                bevel_modifier.width = 0.10
                bevel_modifier.segments = 4
                bevel_modifier.profile = 0.5
                bevel_modifier.limit_method = 'WEIGHT'
                bevel_modifier.use_clamp_overlap = True

            # for m in obj.modifiers:
            #     if m.type == 'EDGE_SPLIT':
            #         obj.modifiers.remove(m)

    @staticmethod
    def get_top_group():
        return LDrawNode.top_group

    @staticmethod
    def create_mesh(key, geometry):
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
    def bmesh_ops(mesh, geometry):
        if options.bevel_edges:
            mesh.use_customdata_edge_bevel = True

        bm = bmesh.new()
        bm.from_mesh(mesh)

        bm.faces.ensure_lookup_table()
        bm.verts.ensure_lookup_table()
        bm.edges.ensure_lookup_table()

        weld_distance = 0.10
        if options.remove_doubles:
            bmesh.ops.remove_doubles(bm, verts=bm.verts[:], dist=weld_distance)

        bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])

        # Create kd tree for fast "find nearest points" calculation
        kd = mathutils.kdtree.KDTree(len(bm.verts))
        for i, v in enumerate(bm.verts):
            kd.insert(v.co, i)
        kd.balance()
        # Create edgeIndices dictionary, which is the list of edges as pairs of indicies into our bm.verts array
        edge_indices = {}
        for edge in geometry.edges:
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
    @staticmethod
    def apply_materials(mesh, geometry, filename):
        # bpy.context.object.active_material.use_backface_culling = True
        # bpy.context.object.active_material.use_screen_refraction = True

        for i, f in enumerate(mesh.polygons):
            face_info = geometry.face_info[i]

            is_slope_material = False
            if face_info.grain_slope_allowed:
                is_slope_material = SpecialBricks.is_slope_face(filename, f)

            material = BlenderMaterials.get_material(face_info.color_code, use_edge_color=face_info.use_edge_color, is_slope_material=is_slope_material)
            if material.name not in mesh.materials:
                mesh.materials.append(material)
            f.material_index = mesh.materials.find(material.name)
            f.use_smooth = options.shade_smooth

    @staticmethod
    def do_gaps(mesh):
        scale = options.gap_scale
        gaps_scale_matrix = mathutils.Matrix((
            (scale, 0.0, 0.0, 0.0),
            (0.0, scale, 0.0, 0.0),
            (0.0, 0.0, scale, 0.0),
            (0.0, 0.0, 0.0, 1.0)
        ))
        mesh.transform(gaps_scale_matrix)
