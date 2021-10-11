bl_info = {
    "name": "Export LDraw",
    "author": "cuddlyogre",
    "version": (0, 1),
    "blender": (2, 80, 0),
    "location": "File > Export > LDraw (.mpd/.ldr/.l3b/.dat)",
    "description": "Imports and Exports LDraw Models",
    "warning": "",
    "wiki_url": "",
    "category": "Import-Export",
}

if "bpy" in locals():
    import importlib

    importlib.reload(blender_camera)
    importlib.reload(blender_materials)
    importlib.reload(blender_import)
    importlib.reload(downloader)
    importlib.reload(filesystem)
    importlib.reload(geometry_data)
    importlib.reload(helpers)
    importlib.reload(ldraw_camera)
    importlib.reload(ldraw_colors)
    importlib.reload(ldraw_export)
    importlib.reload(ldraw_file)
    importlib.reload(ldraw_geometry)
    importlib.reload(ldraw_node)
    importlib.reload(ldraw_part_types)
    importlib.reload(matrices)
    importlib.reload(operator_export)
    importlib.reload(operator_import)
    importlib.reload(import_options)
    importlib.reload(export_options)
    importlib.reload(special_bricks)
    importlib.reload(strings)
    importlib.reload(texmap)
else:
    from . import blender_camera
    from . import blender_materials
    from . import blender_import
    from . import downloader
    from . import filesystem
    from . import geometry_data
    from . import helpers
    from . import ldraw_camera
    from . import ldraw_colors
    from . import ldraw_export
    from . import ldraw_file
    from . import ldraw_geometry
    from . import ldraw_node
    from . import ldraw_part_types
    from . import matrices
    from . import operator_export
    from . import operator_import
    from . import import_options
    from . import export_options
    from . import special_bricks
    from . import strings
    from . import texmap


def register():
    operator_import.register()
    operator_export.register()


def unregister():
    operator_import.unregister()
    operator_export.unregister()


if __name__ == "__main__":
    register()
