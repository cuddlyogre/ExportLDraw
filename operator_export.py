import bpy
from bpy_extras.io_utils import ExportHelper

import time

from .export_options import ExportOptions
from .import_settings import ImportSettings
from .filesystem import FileSystem
from .ldraw_color import LDrawColor
from . import ldraw_export


class EXPORT_OT_do_ldraw_export(bpy.types.Operator, ExportHelper):
    """Export an LDraw model File."""

    bl_idname = "ldraw_exporter.export_operator"
    bl_label = "Export LDraw"
    bl_options = {'PRESET'}

    filename_ext: bpy.props.EnumProperty(
        name='File extension',
        description='Choose File Format:',
        items=(
            ('.dat', 'dat', 'Export as part'),
            ('.ldr', 'ldr', 'Export as model'),
            # ('.mpd', 'mpd', 'Export as multi-part document'),
        ),
        default='.dat',
    )

    filter_glob: bpy.props.StringProperty(
        name="Extensions",
        options={'HIDDEN'},
        default="*.mpd;*.ldr;*.dat",
    )

    ldraw_path: bpy.props.StringProperty(
        name="LDraw path",
        description="Full filepath to the LDraw Parts Library (download from https://www.ldraw.org)",
        default=ImportSettings.get_setting('ldraw_path'),
    )

    studio_ldraw_path: bpy.props.StringProperty(
        name="Stud.io LDraw path",
        description="Full filepath to the Stud.io LDraw Parts Library (download from https://www.bricklink.com/v3/studio/download.page)",
        default=ImportSettings.get_setting('studio_ldraw_path'),
    )

    use_alt_colors: bpy.props.BoolProperty(
        name="Use alternate colors",
        # options={'HIDDEN'},
        description="Use LDCfgalt.ldr",
        default=True,
    )

    selection_only: bpy.props.BoolProperty(
        name="Selection only",
        description="Export selected objects only",
        default=ExportOptions.selection_only,
    )

    recalculate_normals: bpy.props.BoolProperty(
        name="Recalculate normals",
        description="Recalculate normals",
        default=ExportOptions.recalculate_normals,
    )

    triangulate: bpy.props.BoolProperty(
        name="Triangulate faces",
        description="Triangulate all faces",
        default=ExportOptions.triangulate,
    )

    remove_doubles: bpy.props.BoolProperty(
        name="Remove doubles",
        description="Merge overlapping vertices",
        default=ExportOptions.remove_doubles,
    )

    merge_distance: bpy.props.FloatProperty(
        name="Merge distance",
        description="Maximum distance between elements to merge",
        default=0.05,
        precision=3,
        min=0.0,
    )

    ngon_handling: bpy.props.EnumProperty(
        name="Ngon handling",
        description="What to do with ngons",
        default="triangulate",
        items=[
            ("skip", "Skip", "Don't export ngons at all"),
            ("triangulate", "Triangulate", "Triangulate ngons"),
        ],
    )

    # resolution: bpy.props.EnumProperty(
    #     name="Part resolution",
    #     options={'HIDDEN'},
    #     description="Resolution of part primitives, ie. how much geometry they have",
    #     default="Standard",
    #     items=(
    #         ("Low", "Low resolution primitives", "Import using low resolution primitives."),
    #         ("Standard", "Standard primitives", "Import using standard resolution primitives."),
    #         ("High", "High resolution primitives", "Import using high resolution primitives."),
    #     ),
    # )

    def execute(self, context):
        start = time.perf_counter()

        # bpy.ops.object.mode_set(mode='OBJECT')

        FileSystem.ldraw_path = self.ldraw_path
        FileSystem.studio_ldraw_path = self.studio_ldraw_path
        # FileSystem.resolution = self.resolution
        LDrawColor.use_alt_colors = self.use_alt_colors

        ExportOptions.selection_only = self.selection_only
        ExportOptions.remove_doubles = self.remove_doubles
        ExportOptions.merge_distance = self.merge_distance
        ExportOptions.recalculate_normals = self.recalculate_normals
        ExportOptions.triangulate = self.triangulate
        ExportOptions.ngon_handling = self.ngon_handling

        ldraw_export.do_export(bpy.path.abspath(self.filepath))

        print("")
        print("======Export Complete======")
        print(self.filepath)
        end = time.perf_counter()
        elapsed = (end - start)
        print(f"elapsed: {elapsed}")
        print("===========================")
        print("")

        return {'FINISHED'}

    def draw(self, context):
        space_factor = 0.3

        layout = self.layout

        col = layout.column()
        col.prop(self, "ldraw_path")

        layout.separator(factor=space_factor)
        row = layout.row()
        row.label(text="File Format:")
        row.prop(self, "filename_ext", expand=True)

        layout.separator(factor=space_factor)
        col = layout.column()
        col.label(text="Export Options")
        col.prop(self, "selection_only")
        col.prop(self, "use_alt_colors")

        layout.separator(factor=space_factor)
        col = layout.column()
        col.label(text="Cleanup Options")
        col.prop(self, "remove_doubles")
        col.prop(self, "merge_distance")
        col.prop(self, "recalculate_normals")
        col.prop(self, "triangulate")
        col.prop(self, "ngon_handling")


def build_export_menu(self, context):
    self.layout.operator(EXPORT_OT_do_ldraw_export.bl_idname, text="LDraw (.mpd/.ldr/.l3b/.dat)")


classesToRegister = [
    EXPORT_OT_do_ldraw_export,
]

# https://wiki.blender.org/wiki/Reference/Release_Notes/2.80/Python_API/Addons
registerClasses, unregisterClasses = bpy.utils.register_classes_factory(classesToRegister)


def register():
    bpy.utils.register_class(EXPORT_OT_do_ldraw_export)
    bpy.types.TOPBAR_MT_file_export.append(build_export_menu)


def unregister():
    bpy.utils.unregister_class(EXPORT_OT_do_ldraw_export)
    bpy.types.TOPBAR_MT_file_export.remove(build_export_menu)


if __name__ == "__main__":
    register()
