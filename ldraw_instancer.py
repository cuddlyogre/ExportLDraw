import bpy

from . import group
from . import strings

# Instanced import.
#
# Instead of creating one Blender Object per part instance (which makes the
# viewport crawl once there are tens of thousands of objects, regardless of
# polycount), we collect every placement of each unique part+color and build a
# single Geometry Nodes instancer object per unique part+color. Each instancer
# carries a point cloud (one point per placement) with a FLOAT4X4 "transform"
# attribute, and a shared node group that does Instance on Points -> Set
# Instance Transform. The full LDraw placement matrix is baked into the
# attribute, so mirrored/sheared parts instance correctly (a rotation+scale
# decomposition could not represent those).
#
# This collapses object count from (number of placements) to (number of unique
# part+color combos), which is what keeps the viewport responsive.

instancer_marker_key = "ldraw_instancer"
proto_mesh_key = "ldraw_proto_mesh"
proto_object_key = "ldraw_proto_object"
transform_attr = "transform"

node_group_name = "LDraw Instancer"

# key -> {"mesh": Mesh, "color_code": str, "file_name": str, "matrices": [Matrix]}
_instances = {}
_node_group = None
_proto_socket_id = None


def reset_caches():
    global _node_group
    global _proto_socket_id

    _instances.clear()
    _node_group = None
    _proto_socket_id = None


# matrix sockets / FLOAT4X4 attributes (and Set Instance Transform driven by
# them) require Blender 4.3+
def supported():
    return bpy.app.version >= (4, 3) and hasattr(bpy.types, "GeometryNodeSetInstanceTransform")


def active():
    from .import_options import ImportOptions
    return ImportOptions.instancing and supported()


def add_instance(key, mesh, color_code, file_name, world_matrix):
    bucket = _instances.get(key)
    if bucket is None:
        bucket = {
            "mesh": mesh,
            "color_code": color_code,
            "file_name": file_name,
            "matrices": [],
        }
        _instances[key] = bucket
    bucket["matrices"].append(world_matrix.copy())


def build(host_collection):
    if not _instances:
        return

    node_group = __get_node_group()
    proto_collection = __get_prototype_collection(host_collection)

    for key, bucket in _instances.items():
        __build_instancer(key, bucket, node_group, host_collection, proto_collection)


def __build_instancer(key, bucket, node_group, host_collection, proto_collection):
    mesh = bucket["mesh"]
    matrices = bucket["matrices"]

    # geometry source for the Object Info node, kept out of the view layer so it
    # does not draw or add to the per-object viewport cost
    proto = bpy.data.objects.new(f"proto_{bucket['file_name']}", mesh)
    group.link_obj(proto_collection, proto)

    point_cloud = __build_point_cloud(key, bucket, matrices)

    instancer = bpy.data.objects.new(bucket["file_name"], point_cloud)
    instancer[instancer_marker_key] = True
    instancer[proto_mesh_key] = mesh.name
    instancer[proto_object_key] = proto.name
    instancer[strings.ldraw_filename_key] = bucket["file_name"]
    instancer[strings.ldraw_color_code_key] = bucket["color_code"]

    modifier = instancer.modifiers.new(node_group_name, "NODES")
    modifier.node_group = node_group
    modifier[_proto_socket_id] = proto

    group.link_obj(host_collection, instancer)
    return instancer


def __build_point_cloud(key, bucket, matrices):
    point_cloud = bpy.data.meshes.new(f"pc_{bucket['file_name']}")
    point_cloud.vertices.add(len(matrices))
    # put each point at its instance origin so the instancer has meaningful
    # bounds; Set Instance Transform overrides placement from the attribute
    point_cloud.vertices.foreach_set("co", [c for m in matrices for c in m.translation])
    point_cloud.update()

    attribute = point_cloud.attributes.new(name=transform_attr, type='FLOAT4X4', domain='POINT')
    attribute.data.foreach_set("value", __flatten_matrices(matrices))
    return point_cloud


# column-major flat list of 16 floats per matrix (matches foreach_get readback
# in the realize operator)
def __flatten_matrices(matrices):
    flat = []
    for m in matrices:
        for col in range(4):
            for row in range(4):
                flat.append(m[row][col])
    return flat


def __get_node_group():
    global _node_group
    global _proto_socket_id

    if _node_group is not None:
        return _node_group

    node_group = bpy.data.node_groups.new(node_group_name, "GeometryNodeTree")
    node_group.interface.new_socket("Geometry", in_out='INPUT', socket_type='NodeSocketGeometry')
    proto_socket = node_group.interface.new_socket("Prototype", in_out='INPUT', socket_type='NodeSocketObject')
    node_group.interface.new_socket("Geometry", in_out='OUTPUT', socket_type='NodeSocketGeometry')

    nodes = node_group.nodes
    links = node_group.links

    group_input = nodes.new("NodeGroupInput")
    group_output = nodes.new("NodeGroupOutput")
    instance_on_points = nodes.new("GeometryNodeInstanceOnPoints")
    set_instance_transform = nodes.new("GeometryNodeSetInstanceTransform")
    object_info = nodes.new("GeometryNodeObjectInfo")
    object_info.transform_space = 'ORIGINAL'
    named_attribute = nodes.new("GeometryNodeInputNamedAttribute")
    named_attribute.data_type = 'FLOAT4X4'
    named_attribute.inputs["Name"].default_value = transform_attr

    links.new(group_input.outputs["Geometry"], instance_on_points.inputs["Points"])
    links.new(group_input.outputs["Prototype"], object_info.inputs["Object"])
    links.new(object_info.outputs["Geometry"], instance_on_points.inputs["Instance"])
    links.new(instance_on_points.outputs["Instances"], set_instance_transform.inputs["Instances"])
    links.new(named_attribute.outputs["Attribute"], set_instance_transform.inputs["Transform"])
    links.new(set_instance_transform.outputs["Instances"], group_output.inputs["Geometry"])

    _node_group = node_group
    _proto_socket_id = proto_socket.identifier
    return _node_group


def __get_prototype_collection(host_collection):
    collection_name = f"{host_collection.name} Prototypes"
    collection = group.get_collection(collection_name, host_collection)
    helpers_exclude = __find_layer_collection(bpy.context.view_layer.layer_collection, collection)
    if helpers_exclude is not None:
        helpers_exclude.exclude = True
    return collection


def __find_layer_collection(layer_collection, collection):
    if layer_collection.collection == collection:
        return layer_collection
    for child in layer_collection.children:
        found = __find_layer_collection(child, collection)
        if found is not None:
            return found
    return None
