import time
import bpy
import os

from .import_settings import ImportSettings
from .ldraw_node import LDrawNode
from . import blender_import
from . import ldraw_part_types


class IMPORT_OT_do_ldraw_import(bpy.types.Operator):
    """Import an LDraw model File."""

    bl_idname = "ldraw_exporter.import_operator"
    bl_label = "Import LDraw"
    bl_options = {'PRESET', 'UNDO'}
    filename_ext = ""

    filepath: bpy.props.StringProperty(
        name="File Path",
        description="Filepath used for importing the file",
        maxlen=1024,
        subtype='FILE_PATH',
    )

    filter_glob: bpy.props.StringProperty(
        name="Extensions",
        options={'HIDDEN'},
        default="*.mpd;*.ldr;*.dat",
    )

    ldraw_path: bpy.props.StringProperty(
        name="LDraw path",
        description="Full filepath to the LDraw Parts Library (download from http://www.ldraw.org)",
        default=ImportSettings.get_setting('ldraw_path'),
    )

    use_alt_colors: bpy.props.BoolProperty(
        name="Use alternate colors",
        # options={'HIDDEN'},
        description="Use LDCfgalt.ldr",
        default=ImportSettings.get_setting('use_alt_colors'),
    )

    remove_doubles: bpy.props.BoolProperty(
        name="Remove doubles",
        description="Merge overlapping vertices",
        default=ImportSettings.get_setting('remove_doubles'),
    )

    merge_distance: bpy.props.FloatProperty(
        name="Merge distance",
        description="Maximum distance between elements to merge",
        default=ImportSettings.get_setting('merge_distance'),
        precision=3,
        min=0.0,
    )

    shade_smooth: bpy.props.BoolProperty(
        name="Shade smooth",
        description="Shade smooth",
        default=ImportSettings.get_setting('shade_smooth'),
    )

    resolution: bpy.props.EnumProperty(
        name="Part resolution",
        description="Resolution of part primitives, ie. how much geometry they have",
        default=ImportSettings.get_setting('resolution'),
        items=(
            ("Low", "Low resolution primitives", "Import using low resolution primitives."),
            ("Standard", "Standard primitives", "Import using standard resolution primitives."),
            ("High", "High resolution primitives", "Import using high resolution primitives."),
        ),
    )

    display_logo: bpy.props.BoolProperty(
        name="Display logo",
        description="Display logo on studs. Requires unofficial parts library to be downloaded",
        default=ImportSettings.get_setting('display_logo'),
    )

    # cast items as list or "EnumProperty(..., default='logo3'): not found in enum members"
    # and a messed up menu
    chosen_logo: bpy.props.EnumProperty(
        name="Chosen logo",
        description="Use this logo on studs",
        default=ImportSettings.get_setting('chosen_logo'),
        items=list(((logo, logo, logo) for logo in ldraw_part_types.logos)),
    )

    smooth_type: bpy.props.EnumProperty(
        name="Smooth type",
        description="Use this strategy to smooth meshes",
        default=ImportSettings.get_setting('smooth_type'),
        items=(
            ("auto_smooth", "Auto smooth", "Use auto smooth"),
            ("edge_split", "Edge split", "Use an edge split modifier"),
        ),
    )

    gap_target: bpy.props.EnumProperty(
        name="Gap target",
        description="Where to apply gap",
        default=ImportSettings.get_setting('gap_target'),
        items=(
            ("object", "Object", "Scale the object to create the gap"),
            ("mesh", "Mesh", "Transform the mesh to create the gap"),
        ),
    )

    gap_scale_strategy: bpy.props.EnumProperty(
        name="Gap strategy",
        description="How to scale the object to create the gap",
        default=ImportSettings.get_setting('gap_scale_strategy'),
        items=(
            ("object", "Object", "Apply gap directly to the object"),
            ("constraint", "Constraint", "Use a constraint, allowing the gap to easily be adjusted later"),
        ),
    )

    no_studs: bpy.props.BoolProperty(
        name="No studs",
        description="Don't import studs",
        default=ImportSettings.get_setting('no_studs'),
    )

    parent_to_empty: bpy.props.BoolProperty(
        name="Parent to empty",
        description="Parent the model to an empty",
        default=ImportSettings.get_setting('parent_to_empty'),
    )

    import_scale: bpy.props.FloatProperty(
        name="Import scale",
        description="Scale the entire model by this amount",
        default=ImportSettings.get_setting('import_scale'),
        precision=2,
        min=0.01,
        max=1.00,
    )

    make_gaps: bpy.props.BoolProperty(
        name="Make gaps",
        description="Puts small gaps between parts",
        default=ImportSettings.get_setting('make_gaps'),
    )

    gap_scale: bpy.props.FloatProperty(
        name="Gap scale",
        description="Scale parts by this value to make gaps",
        default=ImportSettings.get_setting('gap_scale'),
        precision=3,
        min=0.0,
        max=1.0,
    )

    meta_print_write: bpy.props.BoolProperty(
        name="PRINT/WRITE",
        description="Process PRINT/WRITE meta command",
        default=ImportSettings.get_setting('meta_print_write'),
    )

    meta_group: bpy.props.BoolProperty(
        name="GROUP",
        description="Process GROUP meta commands",
        default=ImportSettings.get_setting('meta_group'),
    )

    meta_step: bpy.props.BoolProperty(
        name="STEP",
        description="Process STEP meta command",
        default=ImportSettings.get_setting('meta_step'),
    )

    meta_step_groups: bpy.props.BoolProperty(
        name="STEP Groups",
        description="Create collections for individual steps",
        default=ImportSettings.get_setting('meta_step_groups'),
    )

    meta_clear: bpy.props.BoolProperty(
        name="CLEAR",
        description="Process CLEAR meta command",
        default=ImportSettings.get_setting('meta_clear'),
    )

    meta_pause: bpy.props.BoolProperty(
        name="PAUSE",
        description="Process PAUSE meta command",
        default=ImportSettings.get_setting('meta_pause'),
    )

    meta_save: bpy.props.BoolProperty(
        name="SAVE",
        description="Process SAVE meta command",
        default=ImportSettings.get_setting('meta_save'),
    )

    set_end_frame: bpy.props.BoolProperty(
        name="Set step end frame",
        description="Set the end frame to the last step",
        default=ImportSettings.get_setting('set_end_frame'),
    )

    frames_per_step: bpy.props.IntProperty(
        name="Frames per step",
        description="Frames per step",
        default=ImportSettings.get_setting('frames_per_step'),
        min=1,
    )

    starting_step_frame: bpy.props.IntProperty(
        name="Starting step frame",
        options={'HIDDEN'},
        description="Frame to add the first STEP meta command",
        default=ImportSettings.get_setting('starting_step_frame'),
        min=1,
    )

    set_timeline_markers: bpy.props.BoolProperty(
        name="Set timeline markers",
        description="Set timeline markers for meta commands",
        default=ImportSettings.get_setting('set_timeline_markers'),
    )

    import_edges: bpy.props.BoolProperty(
        name="Import edges",
        description="Import edge meshes",
        default=ImportSettings.get_setting('import_edges'),
    )

    use_freestyle_edges: bpy.props.BoolProperty(
        name="Use Freestyle edges",
        description="Render LDraw edges using freestyle",
        default=ImportSettings.get_setting('use_freestyle_edges'),
    )

    treat_shortcut_as_model: bpy.props.BoolProperty(
        name="Treat shortcuts as models",
        options={'HIDDEN'},
        description="Split shortcut parts into their constituent pieces as if they were models",
        default=ImportSettings.get_setting('treat_shortcut_as_model'),
    )

    prefer_unofficial: bpy.props.BoolProperty(
        name="Prefer unofficial parts",
        description="Search for unofficial parts first",
        default=ImportSettings.get_setting('prefer_unofficial'),
    )

    recalculate_normals: bpy.props.BoolProperty(
        name="Recalculate normals",
        description="Recalculate normals",
        default=ImportSettings.get_setting('recalculate_normals'),
    )

    triangulate: bpy.props.BoolProperty(
        name="Triangulate faces",
        description="Triangulate all faces",
        default=ImportSettings.get_setting('triangulate'),
    )

    sharpen_edges: bpy.props.BoolProperty(
        name="Sharpen edges",
        description="Make imported LDraw edges sharp",
        default=ImportSettings.get_setting('sharpen_edges'),
    )

    instancing: bpy.props.BoolProperty(
        name="Instance parts",
        options={'HIDDEN'},
        description="Use collection instancing",
        default=ImportSettings.get_setting('instancing'),
    )

    profile: bpy.props.BoolProperty(
        name="Profile",
        description="Profile import performance",
        default=False
    )

    def invoke(self, context, _event):
        context.window_manager.fileselect_add(self)
        ImportSettings.load_settings()
        return {'RUNNING_MODAL'}

    def execute(self, context):
        start = time.perf_counter()

        ImportSettings.save_settings(self)
        ImportSettings.apply_settings()

        # https://docs.python.org/3/library/profile.html
        if self.profile:
            import cProfile
            import pstats

            from pathlib import Path
            this_script_dir = os.path.dirname(os.path.realpath(__file__))
            prof_output = os.path.join(Path.home(), 'export_ldraw_import.prof')

            with cProfile.Profile() as profiler:
                blender_import.do_import(bpy.path.abspath(self.filepath))
            stats = pstats.Stats(profiler)
            stats.sort_stats(pstats.SortKey.TIME)
            stats.print_stats()
            stats.dump_stats(filename=prof_output)
        else:
            blender_import.do_import(bpy.path.abspath(self.filepath))

        print("")
        print("======Import Complete======")
        print(self.filepath)
        print(f"Part count: {LDrawNode.part_count}")
        end = time.perf_counter()
        elapsed = (end - start)
        print(f"elapsed: {elapsed}")
        print("===========================")
        print("")

        return {'FINISHED'}

    # https://docs.blender.org/api/current/bpy.types.UILayout.html
    def draw(self, context):
        space_factor = 0.3

        layout = self.layout

        col = layout.column()
        col.prop(self, "ldraw_path")

        layout.separator(factor=space_factor)
        col = layout.column()
        col.label(text="Import Options")
        col.prop(self, "use_alt_colors")
        col.prop(self, "resolution")
        col.prop(self, "display_logo")
        col.prop(self, "chosen_logo")
        col.prop(self, "profile")

        layout.separator(factor=space_factor)
        col = layout.column()
        col.label(text="Scaling Options")
        col.prop(self, "import_scale")
        col.prop(self, "parent_to_empty")
        col.prop(self, "make_gaps")
        col.prop(self, "gap_scale")
        col.prop(self, "gap_target")
        col.prop(self, "gap_scale_strategy")

        layout.separator(factor=space_factor)
        col = layout.column()
        col.label(text="Cleanup Options")
        col.prop(self, "remove_doubles")
        col.prop(self, "merge_distance")
        col.prop(self, "smooth_type")
        col.prop(self, "shade_smooth")
        col.prop(self, "recalculate_normals")
        col.prop(self, "triangulate")

        layout.separator(factor=space_factor)
        col = layout.column()
        col.label(text="Meta Commands")
        col.prop(self, "meta_group")
        col.prop(self, "meta_print_write")
        col.prop(self, "meta_step")
        col.prop(self, "meta_step_groups")
        col.prop(self, "frames_per_step")
        col.prop(self, "set_end_frame")
        col.prop(self, "meta_clear")
        # col.prop(self, "meta_pause")
        col.prop(self, "meta_save")
        col.prop(self, "set_timeline_markers")

        layout.separator(factor=space_factor)
        col = layout.column()
        col.label(text="Extras")
        col.prop(self, "sharpen_edges")
        col.prop(self, "use_freestyle_edges")
        col.prop(self, "import_edges")
        # col.prop(self, "treat_shortcut_as_model")
        col.prop(self, "prefer_unofficial")
        col.prop(self, "no_studs")


def build_import_menu(self, context):
    self.layout.operator(IMPORT_OT_do_ldraw_import.bl_idname, text="LDraw (.mpd/.ldr/.l3b/.dat)")


classesToRegister = [
    IMPORT_OT_do_ldraw_import,
]

# https://wiki.blender.org/wiki/Reference/Release_Notes/2.80/Python_API/Addons
registerClasses, unregisterClasses = bpy.utils.register_classes_factory(classesToRegister)


def register():
    bpy.utils.register_class(IMPORT_OT_do_ldraw_import)
    bpy.types.TOPBAR_MT_file_import.append(build_import_menu)


def unregister():
    bpy.utils.unregister_class(IMPORT_OT_do_ldraw_import)
    bpy.types.TOPBAR_MT_file_import.remove(build_import_menu)


if __name__ == "__main__":
    register()
