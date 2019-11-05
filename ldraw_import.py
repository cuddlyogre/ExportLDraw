import os
import bpy
import pathlib

from . import filesystem
from . import matrices
from .ldraw_file import LDrawNode
from .ldraw_colors import LDrawColors
from .blender_materials import BlenderMaterials

mesh_data_cache = {}
reuse_mesh_data = not True


# rotation matrix is default because the only node that would receive that matrix is the root node
def traverse_node(node, parent_matrix=matrices.rotation, indent=0, arr=None, join_list=None, parent_color_code="16"):
    node.traversed += 1

    string = f"{'-' * indent}{node.filename}"
    string += f", traversed: {node.traversed}"
    print(string)

    if arr is not None:
        arr.append(string)

    matrix = parent_matrix @ node.matrix

    if node.file.is_part:
        parent_color_code = node.color_code
        join_list = []

    if node.filename in mesh_data_cache and reuse_mesh_data:
        obj = bpy.data.objects.new(node.filename, mesh_data_cache[node.filename])
        obj.matrix_world = matrix
        bpy.context.scene.collection.objects.link(obj)
    else:
        points = [p.to_tuple() for p in node.file.geometry.verts]
        faces = node.file.geometry.faces
        mesh = bpy.data.meshes.new(node.filename)
        mesh.from_pydata(points, [], faces)
        mesh.validate()
        mesh.update()

        obj = bpy.data.objects.new(node.filename, mesh)

        if node.file.is_part:
            obj.matrix_world = matrix
        else:
            obj.data.transform(matrix)

        for i, f in enumerate(obj.data.polygons):
            face_info = node.file.geometry.face_info[i]

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

        for child_node in node.file.child_nodes:
            traverse_node(child_node, matrix, indent + 1, arr, join_list, parent_color_code=parent_color_code)

        if node.file.is_part:
            # https://blender.stackexchange.com/a/133021
            c = {}
            c["object"] = c["active_object"] = join_list[0]
            c['active_object'] = join_list[0]
            c["selected_objects"] = c["selected_editable_objects"] = join_list
            bpy.ops.object.join(c)
            bpy.context.scene.collection.objects.link(join_list[0])
            if join_list[0].name not in mesh_data_cache:
                mesh_data_cache[node.filename] = join_list[0].data

    # this is done here after the merge
    # linking the material to the object before merge appears to make the material linked to data
    # for mat_slot in join_list[0].material_slots:
    #     mat = mat_slot.material
    #     mat_slot.link = 'OBJECT'
    #     mat_slot.material = mat


def do_import(filepath, ldraw_path, resolution):
    filesystem.search_paths.clear()
    LDrawNode.cache.clear()
    LDrawColors.colors.clear()
    BlenderMaterials.material_list.clear()

    filesystem.append_search_paths(ldraw_path, resolution)
    LDrawColors.read_color_table(ldraw_path)
    BlenderMaterials.create_blender_node_groups()

    root_node = LDrawNode(filepath)
    root_node.load()

    arr = []
    traverse_node(root_node, arr=arr)

    write_tree = True
    if write_tree:
        path = os.path.join(ldraw_path, 'trees')
        pathlib.Path(path).mkdir(parents=True, exist_ok=True)
        trees_path = os.path.join(path, f"{os.path.basename(filepath).split('.')[0]}.txt")
        with open(trees_path, 'w') as file:
            file.write("\n".join(arr))
