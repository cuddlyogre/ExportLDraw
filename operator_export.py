import time
import bpy
from bpy_extras.io_utils import ExportHelper

from . import export_options
from . import filesystem
from . import ldraw_colors
from . import ldraw_export


class EXPORT_OT_do_ldraw_export(bpy.types.Operator, ExportHelper):
    """Export an LDraw model File."""

    bl_idname = "export.ldraw"
    bl_label = "Export LDraw"
    bl_options = {'PRESET'}
    filename_ext = ""

    filter_glob: bpy.props.StringProperty(
        name="Extensions",
        options={'HIDDEN'},
        default="*.mpd;*.ldr;*.dat",
    )

    ldraw_path: bpy.props.StringProperty(
        name="LDraw path",
        description="Full filepath to the LDraw Parts Library (download from http://www.ldraw.org)",
        default=filesystem.locate_ldraw(),
    )

    use_alt_colors: bpy.props.BoolProperty(
        name="Use alternate colors",
        options={'HIDDEN'},
        description="Use LDCfgalt.ldr",
        default=True,
    )

    selection_only: bpy.props.BoolProperty(
        name="Selection only",
        description="Export selected objects only",
        default=True,
    )

    recalculate_normals: bpy.props.BoolProperty(
        name="Recalculate normals",
        description="Recalculate normals",
        default=True,
    )

    triangulate: bpy.props.BoolProperty(
        name="Triangulate faces",
        description="Triangulate all faces",
        default=False,
    )

    remove_doubles: bpy.props.BoolProperty(
        name="Remove doubles",
        description="Merge overlapping verices",
        default=True,
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

    export_precision: bpy.props.IntProperty(
        name="Export precision",
        description="Round vertex coordinates to this number of places",
        default=2,
        min=0,
    )

    resolution: bpy.props.EnumProperty(
        name="Part resolution",
        options={'HIDDEN'},
        description="Resolution of part primitives, ie. how much geometry they have",
        default="Standard",
        items=(
            ("Low", "Low resolution primitives", "Import using low resolution primitives."),
            ("Standard", "Standard primitives", "Import using standard resolution primitives."),
            ("High", "High resolution primitives", "Import using high resolution primitives."),
        ),
    )

    prefer_unofficial: bpy.props.BoolProperty(
        name="Prefer unofficial parts",
        options={'HIDDEN'},
        description="Search for unofficial parts first",
        default=False,
    )

    def execute(self, context):
        start = time.monotonic()

        filesystem.ldraw_path = self.ldraw_path
        filesystem.prefer_unofficial = self.prefer_unofficial
        filesystem.resolution = self.resolution
        ldraw_colors.use_alt_colors = self.use_alt_colors

        export_options.selection_only = self.selection_only
        export_options.export_precision = self.export_precision
        export_options.remove_doubles = self.remove_doubles
        export_options.merge_distance = self.merge_distance
        export_options.recalculate_normals = self.recalculate_normals
        export_options.triangulate = self.triangulate
        export_options.ngon_handling = self.ngon_handling

        ldraw_export.do_export(bpy.path.abspath(self.filepath))

        print("")
        print("======Export Complete======")
        print(self.filepath)
        end = time.monotonic()
        elapsed = (end - start)
        print(f"elapsed: {elapsed}")
        print("===========================")
        print("")

        return {'FINISHED'}

    def draw(self, context):
        layout = self.layout
        layout.use_property_split = True

        box = layout.box()

        box.label(text="LDraw filepath:", icon='FILEBROWSER')
        box.prop(self, "ldraw_path")

        box.label(text="Export Options")
        box.prop(self, "selection_only")
        # box.prop(self, "use_alt_colors")
        box.prop(self, "export_precision")
        box.prop(self, "prefer_unofficial")

        box.label(text="Cleanup Options")
        box.prop(self, "remove_doubles")
        box.prop(self, "merge_distance")
        box.prop(self, "recalculate_normals")
        box.prop(self, "triangulate")
        box.prop(self, "ngon_handling")
