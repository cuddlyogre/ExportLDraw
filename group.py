import bpy

import os

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


def get_scene_collection():
    return bpy.context.scene.collection


def get_collection(collection_name, host_collection):
    collection_name = collection_name[:63]
    collection = bpy.data.collections.get(collection_name)
    if collection is None:
        collection = bpy.data.collections.new(collection_name)
        link_child(collection, host_collection)
    return collection


def get_filename_collection(collection_name, host_collection):
    collection_name = os.path.basename(collection_name)
    return get_collection(collection_name, host_collection)


def link_child(collection, host_collection):
    try:
        host_collection.children.link(collection)
    except RuntimeError as e:
        """already in collection"""


def link_obj(collection, obj):
    try:
        collection.objects.link(obj)
    except RuntimeError as e:
        """already in collection"""
