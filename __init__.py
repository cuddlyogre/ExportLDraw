bl_info = {
    "name": "Export LDraw",
    "author": "cuddlyogre",
    "version": (0, 1),
    "blender": (2, 80, 0),
    "location": "File > Export > LDraw (.mpd/.ldr/.l3b/.dat)",
    "description": "Exports LDraw Models",
    "warning": "",
    "wiki_url": "",
    "category": "Import-Export",
}

if "bpy" in locals():
    import importlib

    importlib.reload(face_info)
    importlib.reload(filesystem)
    importlib.reload(ldraw_export)
    importlib.reload(ldraw_file)
    importlib.reload(ldraw_geometry)
    importlib.reload(ldraw_import)
    importlib.reload(ldraw_colors)
    importlib.reload(blender_materials)
    importlib.reload(matrices)
    importlib.reload(special_bricks)
else:
    from . import face_info
    from . import filesystem
    from . import ldraw_export
    from . import ldraw_file
    from . import ldraw_geometry
    from . import ldraw_import
    from . import ldraw_colors
    from . import blender_materials
    from . import matrices
    from . import special_bricks

import bpy
from bpy_extras.io_utils import ImportHelper, ExportHelper


class IMPORT_OT_do_ldraw_import(bpy.types.Operator, ImportHelper):
    bl_idname = "import.ldraw"
    bl_label = "Import LDraw"
    bl_options = {'PRESET'}
    filename_ext = ""

    filter_glob: bpy.props.StringProperty(
        default="*.mpd;*.ldr;*.l3b;*.dat",
        options={'HIDDEN'},
    )

    ldraw_path: bpy.props.StringProperty(
        name="",
        description="Full filepath to the LDraw Parts Library (download from http://www.ldraw.org)",
        default="d:\\ldraw"
    )

    resolution: bpy.props.EnumProperty(
        name="Resolution of part primitives",
        description="Resolution of part primitives, ie. how much geometry they have",
        default="Standard",
        items=(
            ("Standard", "Standard primitives", "Import using standard resolution primitives."),
            ("High", "High resolution primitives", "Import using high resolution primitives."),
            ("Low", "Low resolution primitives", "Import using low resolution primitives.")
        )
    )

    display_logo: bpy.props.BoolProperty(
        name="Display logo",
        description="Display logo on studs",
        default=False
    )

    chosen_logo: bpy.props.EnumProperty(
        name="Logo to use on studs",
        description="Use this logo on studs",
        default=special_bricks.SpecialBricks.logos[2],
        items=((l, l, l) for l in special_bricks.SpecialBricks.logos[2:])
    )

    def execute(self, context):
        import time
        start = time.monotonic()

        ldraw_file.LDrawFile.display_logo = self.display_logo
        ldraw_file.LDrawFile.chosen_logo = self.chosen_logo

        ldraw_import.do_import(bpy.path.abspath(self.filepath), self.ldraw_path, self.resolution)

        end = time.monotonic()
        elapsed = (end - start)
        print(elapsed)

        return {'FINISHED'}

    def draw(self, context):
        layout = self.layout
        layout.use_property_split = True
        box = layout.box()
        box.label(text="LDraw filepath:", icon='FILEBROWSER')
        box.prop(self, "ldraw_path")
        box.prop(self, "display_logo")
        box.prop(self, "chosen_logo")
        box.prop(self, "resolution", expand=True)


class EXPORT_OT_do_ldraw_export(bpy.types.Operator, ExportHelper):
    bl_idname = "export.ldraw"
    bl_label = "Export LDraw"
    bl_options = {'PRESET'}
    filename_ext = ""

    filter_glob: bpy.props.StringProperty(
        default="*.mpd;*.ldr;*.l3b;*.dat",
        options={'HIDDEN'},
    )

    ldraw_path: bpy.props.StringProperty(
        name="",
        description="Full filepath to the LDraw Parts Library (download from http://www.ldraw.org)",
        default="d:\\ldraw"
    )

    selection_only: bpy.props.BoolProperty(
        name="Selection Only",
        description="Export selected objects only",
        default=True
    )

    recalculate_normals: bpy.props.BoolProperty(
        name="Recalculate Normals",
        description="Recalculate Normals",
        default=True
    )

    triangulate: bpy.props.BoolProperty(
        name="Triangulate Mesh",
        description="Triangulate the entire mesh",
        default=False
    )

    ngon_handling: bpy.props.EnumProperty(
        name="Ngon Handling",
        description="What to do with ngons",
        items=[
            ("skip", "Skip", "Don't export ngons at all"),
            ("triangulate", "Triangulate", "Triangulate ngons"),
        ],
        default="triangulate",
    )

    def execute(self, context):
        ldraw_export.triangulate = self.triangulate
        ldraw_export.selection_only = self.selection_only
        ldraw_export.recalculate_normals = self.recalculate_normals
        ldraw_export.ngon_handling = self.ngon_handling

        ldraw_export.do_export(bpy.path.abspath(self.filepath), self.ldraw_path)

        return {'FINISHED'}


def build_import_menu(self, context):
    self.layout.operator(IMPORT_OT_do_ldraw_import.bl_idname, text="Basic LDraw (.mpd/.ldr/.l3b/.dat)")


def build_export_menu(self, context):
    self.layout.operator(EXPORT_OT_do_ldraw_export.bl_idname, text="LDraw (.mpd/.ldr/.l3b/.dat)")


def register():
    bpy.utils.register_class(IMPORT_OT_do_ldraw_import)
    bpy.types.TOPBAR_MT_file_import.append(build_import_menu)

    bpy.utils.register_class(EXPORT_OT_do_ldraw_export)
    bpy.types.TOPBAR_MT_file_export.append(build_export_menu)


def unregister():
    bpy.utils.unregister_class(IMPORT_OT_do_ldraw_import)
    bpy.types.TOPBAR_MT_file_import.remove(build_import_menu)

    bpy.utils.unregister_class(EXPORT_OT_do_ldraw_export)
    bpy.types.TOPBAR_MT_file_export.remove(build_export_menu)


if __name__ == "__main__":
    register()
