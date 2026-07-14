import bpy

import re

from . import group
from . import strings

# matches a zero-padded index prefix added during consolidation, so it can be
# stripped before re-prefixing on a re-consolidate
_index_prefix_re = re.compile(r"^\d{6}_")

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
merged_marker_key = "ldraw_merged_instancer"
proto_mesh_key = "ldraw_proto_mesh"
proto_object_key = "ldraw_proto_object"
transform_attr = "transform"
index_attr = "instance_index"

# scene custom-property flags recording realtime-toggle state
consolidated_key = "ldraw_consolidated"

node_group_name = "LDraw Instancer"
merged_node_group_name = "LDraw Merged Instancer"

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


# ---------------------------------------------------------------------------
# Consolidation: merge the per-part-color instancers into ONE whole-model
# instancer. Per-part instancing already gives a fast solid viewport, but EEVEE
# pays a per-object cost every redraw, so thousands of instancer objects still
# lag. Collapsing them to a single object (heterogeneous instancing via
# Collection Info + Pick Instance by a per-point index) removes that per-object
# cost. The per-part instancers are hidden, not deleted, so it can be undone.
# ---------------------------------------------------------------------------

def __active_per_part_instancers():
    return [o for o in bpy.data.objects
            if o.get(instancer_marker_key) and not o.get(merged_marker_key)]


def consolidate():
    if not supported():
        return []

    # group by prototype collection so a scene with several models gets one
    # merged instancer per model. Skip hidden per-part instancers -- those were
    # already consolidated, so re-running must not build a duplicate merged object
    groups = {}
    for inst in __active_per_part_instancers():
        if inst.hide_viewport:
            continue
        proto = bpy.data.objects.get(inst.get(proto_object_key, ""))
        if proto is None or not proto.users_collection:
            continue
        groups.setdefault(proto.users_collection[0], []).append(inst)

    merged_objects = []
    for proto_collection, per_parts in groups.items():
        merged = __consolidate_group(proto_collection, per_parts)
        if merged is not None:
            merged_objects.append(merged)
    return merged_objects


def __consolidate_group(proto_collection, per_parts):
    # Collection Info "Separate Children" feeds Pick Instance in name-sorted
    # order, and Blender's name sort is natural (numeric-aware), not the plain
    # lexicographic order Python's sorted() gives -- so part names like
    # "proto_2.dat" vs "proto_10.dat" would map to the wrong child. Rename every
    # prototype with a fixed-width zero-padded index prefix so the name sort,
    # whatever its exact rules, equals the index we assign. Resolve each
    # per-part's prototype first, since the stored names change on rename.
    resolved = []
    for inst in per_parts:
        proto = bpy.data.objects.get(inst.get(proto_object_key, ""))
        if proto is not None:
            resolved.append((inst, proto))

    obj_index = {}
    for i, proto in enumerate(proto_collection.objects):
        proto.name = f"{i:06d}_{_index_prefix_re.sub('', proto.name)}"
        obj_index[proto] = i

    # keep the stored prototype names in sync for future toggles
    for inst, proto in resolved:
        inst[proto_object_key] = proto.name

    positions = []
    transforms = []
    indices = []
    for inst, proto in resolved:
        index = obj_index.get(proto)
        if index is None:
            continue
        point_cloud = inst.data
        count = len(point_cloud.vertices)

        pos = [0.0] * (3 * count)
        point_cloud.vertices.foreach_get("co", pos)
        positions.extend(pos)

        buffer = [0.0] * (16 * count)
        point_cloud.attributes[transform_attr].data.foreach_get("value", buffer)
        transforms.extend(buffer)

        indices.extend([index] * count)

    if not indices:
        return None

    merged_pc = bpy.data.meshes.new("pc_merged")
    merged_pc.vertices.add(len(indices))
    merged_pc.vertices.foreach_set("co", positions)
    merged_pc.update()
    merged_pc.attributes.new(name=transform_attr, type='FLOAT4X4', domain='POINT').data.foreach_set("value", transforms)
    merged_pc.attributes.new(name=index_attr, type='INT', domain='POINT').data.foreach_set("value", indices)

    merged = bpy.data.objects.new("LDraw Merged", merged_pc)
    merged[instancer_marker_key] = True
    merged[merged_marker_key] = True

    modifier = merged.modifiers.new(merged_node_group_name, "NODES")
    modifier.node_group = __build_merged_node_group(proto_collection)

    group.link_obj(per_parts[0].users_collection[0], merged)

    for inst in per_parts:
        inst.hide_viewport = True
        inst.hide_render = True

    return merged


def unconsolidate():
    for merged in [o for o in bpy.data.objects if o.get(merged_marker_key)]:
        point_cloud = merged.data
        node_groups = [m.node_group for m in merged.modifiers if m.type == 'NODES' and m.node_group]
        bpy.data.objects.remove(merged, do_unlink=True)
        if point_cloud is not None and point_cloud.users == 0:
            bpy.data.meshes.remove(point_cloud)
        for ng in node_groups:
            if ng.users == 0:
                bpy.data.node_groups.remove(ng)

    for inst in __active_per_part_instancers():
        inst.hide_viewport = False
        inst.hide_render = False


def __build_merged_node_group(proto_collection):
    node_group = bpy.data.node_groups.new(merged_node_group_name, "GeometryNodeTree")
    node_group.interface.new_socket("Geometry", in_out='INPUT', socket_type='NodeSocketGeometry')
    node_group.interface.new_socket("Geometry", in_out='OUTPUT', socket_type='NodeSocketGeometry')

    nodes = node_group.nodes
    links = node_group.links

    group_input = nodes.new("NodeGroupInput")
    group_output = nodes.new("NodeGroupOutput")
    collection_info = nodes.new("GeometryNodeCollectionInfo")
    collection_info.inputs["Collection"].default_value = proto_collection
    for socket in collection_info.inputs:
        if socket.name in ("Separate Children", "Reset Children"):
            socket.default_value = True

    instance_on_points = nodes.new("GeometryNodeInstanceOnPoints")
    instance_on_points.inputs["Pick Instance"].default_value = True
    set_instance_transform = nodes.new("GeometryNodeSetInstanceTransform")

    index_attribute = nodes.new("GeometryNodeInputNamedAttribute")
    index_attribute.data_type = 'INT'
    index_attribute.inputs["Name"].default_value = index_attr
    transform_attribute = nodes.new("GeometryNodeInputNamedAttribute")
    transform_attribute.data_type = 'FLOAT4X4'
    transform_attribute.inputs["Name"].default_value = transform_attr

    links.new(group_input.outputs["Geometry"], instance_on_points.inputs["Points"])
    links.new(collection_info.outputs["Instances"], instance_on_points.inputs["Instance"])
    links.new(index_attribute.outputs["Attribute"], instance_on_points.inputs["Instance Index"])
    links.new(instance_on_points.outputs["Instances"], set_instance_transform.inputs["Instances"])
    links.new(transform_attribute.outputs["Attribute"], set_instance_transform.inputs["Transform"])
    links.new(set_instance_transform.outputs["Instances"], group_output.inputs["Geometry"])

    return node_group
