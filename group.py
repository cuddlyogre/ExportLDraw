import bpy
import os


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
