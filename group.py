import bpy
import os
from . import helpers
from .import_options import ImportOptions

top_collection = None
parts_collection = None
groups_collection = None
ungrouped_collection = None
next_collections = []
next_collection = None
end_next_collection = False
current_step_group = None
collection_id_map = {}


def reset_caches():
    global top_collection
    global parts_collection
    global groups_collection
    global ungrouped_collection
    global next_collections
    global next_collection
    global end_next_collection
    global current_step_group
    global collection_id_map

    top_collection = None
    parts_collection = None
    groups_collection = None
    ungrouped_collection = None
    next_collections.clear()
    next_collection = None
    end_next_collection = False
    current_step_group = None
    collection_id_map.clear()


def groups_setup(ldraw_node):
    global top_collection
    global parts_collection
    global groups_collection
    global ungrouped_collection

    collection_name = ldraw_node.file.name
    host_collection = get_scene_collection()
    collection = get_filename_collection(collection_name, host_collection)
    top_collection = collection

    collection_name = f"{top_collection.name} Parts"
    host_collection = top_collection
    collection = get_collection(collection_name, host_collection)
    parts_collection = collection
    helpers.hide_obj(parts_collection)

    if ImportOptions.meta_group:
        collection_name = f"{top_collection.name} Groups"
        host_collection = top_collection
        collection = get_collection(collection_name, host_collection)
        groups_collection = collection
        helpers.hide_obj(groups_collection)

        collection_name = f"{top_collection.name} Ungrouped"
        host_collection = top_collection
        collection = get_collection(collection_name, host_collection)
        ungrouped_collection = collection
        helpers.hide_obj(ungrouped_collection)


def get_scene_collection():
    return bpy.context.scene.collection


def get_collection(collection_name, host_collection):
    collection_name = collection_name[:63]
    collection = bpy.data.collections.get(collection_name)
    if collection is None:
        collection = bpy.data.collections.new(collection_name)
        if host_collection is not None:
            link_child(collection, host_collection)
    return collection


def get_filename_collection(collection_name, host_collection):
    collection_name = os.path.basename(collection_name)
    return get_collection(collection_name, host_collection)


def link_child(collection, host_collection):
    try:
        host_collection.children.link(collection)
    except RuntimeError as e:
        print(e)
        import traceback
        print(traceback.format_exc())
        """already in collection"""


def link_obj(collection, obj):
    try:
        collection.objects.link(obj)
    except RuntimeError as e:
        print(e)
        import traceback
        print(traceback.format_exc())
        """already in collection"""
