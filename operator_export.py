import time
import bpy
from bpy_extras.io_utils import ExportHelper

from . import options
from . import filesystem
from . import ldraw_export


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
        default=filesystem.locate_ldraw()
    )

    use_alt_colors: bpy.props.BoolProperty(
        name="Use alternate colors",
        description="Use LDCfgalt.ldr",
        default=True,
    )

    selection_only: bpy.props.BoolProperty(
        name="Selection only",
        description="Export selected objects only",
        default=True
    )

    recalculate_normals: bpy.props.BoolProperty(
        name="Recalculate normals",
        description="Recalculate normals",
        default=True
    )

    triangulate: bpy.props.BoolProperty(
        name="Triangulate mesh",
        description="Triangulate the entire mesh",
        default=False
    )

    remove_doubles: bpy.props.BoolProperty(
        name="Remove doubles",
        description="Merge overlapping verices",
        default=True,
    )

    merge_distance: bpy.props.FloatProperty(
        name="Merge Distance",
        description="Maximum distance between elements to merge",
        default=0.05,
        precision=3,
        min=0.0,
    )

    ngon_handling: bpy.props.EnumProperty(
        name="Ngon handling",
        description="What to do with ngons",
        items=[
            ("skip", "Skip", "Don't export ngons at all"),
            ("triangulate", "Triangulate", "Triangulate ngons"),
        ],
        default="triangulate",
    )

    export_precision: bpy.props.IntProperty(
        name="Export precision",
        description="Round vertex coordinates to this number of places",
        default=2,
        min=0,
    )

    def execute(self, context):
        start = time.monotonic()

        options.ldraw_path = self.ldraw_path
        options.use_alt_colors = self.use_alt_colors
        options.selection_only = self.selection_only
        options.export_precision = self.export_precision
        options.remove_doubles = self.remove_doubles
        options.merge_distance = self.merge_distance
        options.recalculate_normals = self.recalculate_normals
        options.triangulate = self.triangulate
        options.ngon_handling = self.ngon_handling

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
        box.prop(self, "use_alt_colors")
        box.prop(self, "export_precision")

        box.label(text="Cleanup Options")
        box.prop(self, "remove_doubles")
        box.prop(self, "merge_distance")
        box.prop(self, "recalculate_normals")
        box.prop(self, "triangulate")
        box.prop(self, "ngon_handling")
