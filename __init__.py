# https://docs.blender.org/api/current/bpy.types.AddonPreferences.html
# https://github.com/blender/blender/blob/9c0bffcc89f174f160805de042b00ae7c201c40b/scripts/startup/bl_ui/space_userpref.py#L2230-L2306
bl_info = {
    "name": "Export LDraw",
    "author": "cuddlyogre",
    "version": (26, 7, 600),
    "blender": (4, 2, 0),
    "location": "File > Import-Export > LDraw (.mpd/.ldr/.l3b/.dat)",
    "description": "Imports and Exports LDraw Models",
    "warning": "",
    "doc_url": "",
    "tracker_url": "https://github.com/cuddlyogre/ExportLDraw",
    "category": "Import-Export",
}

# reloading is detailed here: https://developer.blender.org/docs/handbook/extensions/addon_dev_setup/#reloading-scripts
# but doing it this way dumps the entire addon so it can be reloaded. doing it one by one is a game of wack a mole
if "bpy" in locals():
    import sys


    mods = [m for m in list(sys.modules) if m.startswith(__name__ + ".")]
    print(mods)
    for _mod in mods:
        del sys.modules[_mod]
    print('=' * 20)
    print(f"{__name__} Reloaded")
    print('=' * 20)

import bpy

from . import ldraw_props
from . import operator_import
from . import operator_export
from . import operator_panel_ldraw
from . import ldraw_operators

_modules = (
    ldraw_props,
    operator_import,
    operator_export,
    operator_panel_ldraw,
    ldraw_operators,
)


def register():
    for module in _modules:
        module.register()


def unregister():
    for module in reversed(_modules):
        try:
            module.unregister()
        except Exception as error:
            # keep going so one failed module can't wedge a dev reload half-registered
            print(f"{__name__}: failed to unregister {module.__name__}: {error}")


if __name__ == "__main__":
    register()
