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
