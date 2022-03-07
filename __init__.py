bl_info = {
    "name": "Export LDraw",
    "author": "cuddlyogre",
    "version": (0, 1),
    "blender": (2, 82, 0),
    "location": "File > Import-Export > LDraw (.mpd/.ldr/.l3b/.dat)",
    "description": "Imports and Exports LDraw Models",
    "warning": "",
    "wiki_url": "",
    "category": "Import-Export",
}

#############################################
# support reloading sub-modules
_modules = [
    'base64_handler',
    'blender_camera',
    'blender_import',
    'blender_materials',
    'definitions',
    'export_options',
    'filesystem',
    'geometry_data',
    'group',
    'helpers',
    'import_options',
    'import_settings',
    'ldraw_camera',
    'ldraw_colors',
    'ldraw_export',
    'ldraw_file',
    'ldraw_geometry',
    'ldraw_node',
    'ldraw_part_types',
    'ldraw_props',
    'operator_export',
    'operator_import',
    'pe_texmap',
    'import_options',
    'export_options',
    'special_bricks',
    'strings',
    'texmap',
]

# Reload previously loaded modules.prop(
if "bpy" in locals():
    from importlib import reload

    _modules_loaded[:] = [reload(module) for module in _modules_loaded]
    del reload

# First import the modules
__import__(name=__name__, fromlist=_modules)
_namespace = globals()
_modules_loaded = [_namespace[name] for name in _modules]
del _namespace
# support reloading sub-modules
#############################################

import bpy


def register():
    ldraw_props.register()
    operator_import.register()
    operator_export.register()


def unregister():
    ldraw_props.unregister()
    operator_import.unregister()
    operator_export.unregister()


if __name__ == "__main__":
    register()
