# https://docs.blender.org/api/current/bpy.types.AddonPreferences.html
# https://github.com/blender/blender/blob/9c0bffcc89f174f160805de042b00ae7c201c40b/scripts/startup/bl_ui/space_userpref.py#L2230-L2306
bl_info = {
    "name": "Export LDraw",
    "author": "cuddlyogre",
    "version": (26, 2, 800),
    "blender": (4,),
    "location": "File > Import-Export > LDraw (.mpd/.ldr/.l3b/.dat)",
    "description": "Imports and Exports LDraw Models",
    "warning": "",
    "doc_url": "",
    "tracker_url": "https://github.com/cuddlyogre/ExportLDraw",
    "category": "Import-Export",
}

if "bpy" in locals():
    import importlib
    importlib.reload(ldraw_props)
    importlib.reload(operator_import)
    importlib.reload(operator_export)
    importlib.reload(operator_panel_ldraw)
    importlib.reload(ldraw_operators)

import bpy

from . import ldraw_props
from . import operator_import
from . import operator_export
from . import operator_panel_ldraw
from . import ldraw_operators


def register():
    ldraw_props.register()
    operator_import.register()
    operator_export.register()
    operator_panel_ldraw.register()
    ldraw_operators.register()


def unregister():
    ldraw_props.unregister()
    operator_import.unregister()
    operator_export.unregister()
    operator_panel_ldraw.unregister()
    ldraw_operators.unregister()


if __name__ == "__main__":
    register()
