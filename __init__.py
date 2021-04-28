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
    importlib.reload(blender_materials)
    importlib.reload(blender_mesh)
    importlib.reload(downloader)
    importlib.reload(face_info)
    importlib.reload(filesystem)
    importlib.reload(helpers)
    importlib.reload(ldraw_camera)
    importlib.reload(ldraw_colors)
    importlib.reload(ldraw_export)
    importlib.reload(ldraw_file)
    importlib.reload(ldraw_geometry)
    importlib.reload(ldraw_import)
    importlib.reload(ldraw_node)
    importlib.reload(ldraw_part_types)
    importlib.reload(matrices)
    importlib.reload(operator_export)
    importlib.reload(operator_import)
    importlib.reload(options)
    importlib.reload(special_bricks)
    importlib.reload(strings)
    importlib.reload(texmap)
else:
    from . import operator_export
    from . import operator_import

import bpy


def build_import_menu(self, context):
    self.layout.operator(operator_import.IMPORT_OT_do_ldraw_import.bl_idname, text="LDraw (.mpd/.ldr/.l3b/.dat)")


def build_export_menu(self, context):
    self.layout.operator(operator_export.EXPORT_OT_do_ldraw_export.bl_idname, text="LDraw (.mpd/.ldr/.l3b/.dat)")


def register():
    bpy.utils.register_class(operator_import.IMPORT_OT_do_ldraw_import)
    bpy.types.TOPBAR_MT_file_import.append(build_import_menu)

    bpy.utils.register_class(operator_export.EXPORT_OT_do_ldraw_export)
    bpy.types.TOPBAR_MT_file_export.append(build_export_menu)


def unregister():
    bpy.utils.unregister_class(operator_import.IMPORT_OT_do_ldraw_import)
    bpy.types.TOPBAR_MT_file_import.remove(build_import_menu)

    bpy.utils.unregister_class(operator_export.EXPORT_OT_do_ldraw_export)
    bpy.types.TOPBAR_MT_file_export.remove(build_export_menu)


if __name__ == "__main__":
    register()
