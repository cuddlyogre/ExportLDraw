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

import bpy


def import_menu(self, context):
    self.layout.operator(operator_import.IMPORT_OT_do_ldraw_import.bl_idname, text="LDraw (.mpd/.ldr/.l3b/.dat)")


def export_menu(self, context):
    self.layout.operator(operator_export.EXPORT_OT_do_ldraw_export.bl_idname, text="LDraw (.mpd/.ldr/.l3b/.dat)")


def register():
    bpy.utils.register_class(operator_import.IMPORT_OT_do_ldraw_import)
    if hasattr(bpy.types, 'TOPBAR_MT_file_import'):
        bpy.types.TOPBAR_MT_file_import.append(import_menu)
    else:
        bpy.types.INFO_MT_file_import.append(import_menu)

    bpy.utils.register_class(operator_export.EXPORT_OT_do_ldraw_export)
    if hasattr(bpy.types, 'TOPBAR_MT_file_import'):
        bpy.types.TOPBAR_MT_file_export.append(export_menu)
    else:
        bpy.types.INFO_MT_file_export.append(import_menu)


def unregister():
    bpy.utils.unregister_class(operator_import.IMPORT_OT_do_ldraw_import)
    if hasattr(bpy.types, 'TOPBAR_MT_file_import'):
        bpy.types.TOPBAR_MT_file_import.remove(import_menu)
    else:
        bpy.types.INFO_MT_file_import.remove(import_menu)

    bpy.utils.unregister_class(operator_export.EXPORT_OT_do_ldraw_export)
    if hasattr(bpy.types, 'TOPBAR_MT_file_import'):
        bpy.types.TOPBAR_MT_file_export.remove(export_menu)
    else:
        bpy.types.INFO_MT_file_export.remove(import_menu)


if __name__ == "__main__":
    register()
