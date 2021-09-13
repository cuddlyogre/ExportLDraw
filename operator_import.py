import time
import bpy
import os
import json
from bpy_extras.io_utils import ImportHelper
from pathlib import Path

from . import import_options
from . import filesystem
from . import ldraw_colors
from . import ldraw_node
from . import blender_import
from . import special_bricks

import cProfile
import pstats

profiler = cProfile.Profile()

settings = None

# FIXME: error if a new setting key is forgotten
default_settings = {
    'ldraw_path': filesystem.locate_ldraw(),
    'prefer_unofficial': filesystem.defaults['prefer_unofficial'],
    'resolution': filesystem.defaults['resolution'],
    'use_alt_colors': ldraw_colors.defaults['use_alt_colors'],
    'remove_doubles': import_options.defaults['remove_doubles'],
    'merge_distance': import_options.defaults['merge_distance'],
    'shade_smooth': import_options.defaults['shade_smooth'],
    'display_logo': import_options.defaults['display_logo'],
    'chosen_logo': special_bricks.defaults['chosen_logo'],
    'make_gaps': import_options.defaults['make_gaps'],
    'gap_scale': import_options.defaults['gap_scale'],
    'no_studs': import_options.defaults['no_studs'],
    'set_timelime_markers': import_options.defaults['set_timelime_markers'],
    'meta_group': import_options.defaults['meta_group'],
    'meta_print_write': import_options.defaults['meta_print_write'],
    'meta_step': import_options.defaults['meta_step'],
    'meta_clear': import_options.defaults['meta_clear'],
    'meta_pause': import_options.defaults['meta_pause'],
    'meta_save': import_options.defaults['meta_save'],
    'set_end_frame': import_options.defaults['set_end_frame'],
    'frames_per_step': import_options.defaults['frames_per_step'],
    'starting_step_frame': import_options.defaults['starting_step_frame'],
    'smooth_type': import_options.defaults['smooth_type'],
    'import_edges': import_options.defaults['import_edges'],
    'use_freestyle_edges': import_options.defaults['use_freestyle_edges'],
    'import_scale': import_options.defaults['import_scale'],
    'parent_to_empty': import_options.defaults['parent_to_empty'],
    'gap_target': import_options.defaults['gap_target'],
    'gap_scale_strategy': import_options.defaults['gap_scale_strategy'],
    'treat_shortcut_as_model': import_options.defaults['treat_shortcut_as_model'],
    'recalculate_normals': import_options.defaults['recalculate_normals'],
    'triangulate': import_options.defaults['triangulate'],
    'sharpen_edges': import_options.defaults['sharpen_edges'],
    'instancing': import_options.defaults['instancing'],
}


def get_setting(key):
    if settings is None:
        load_settings()

    setting = settings.get(key)
    default = default_settings.get(key)

    # ensure saved type is the same as the default type
    if type(setting) == type(default):
        return setting
    else:
        return default


def load_settings():
    try:
        global settings
        this_script_dir = os.path.dirname(os.path.realpath(__file__))
        config_path = os.path.join(this_script_dir, 'config')
        Path(config_path).mkdir(parents=True, exist_ok=True)
        settings_path = os.path.join(config_path, 'import_options.json')

        if not os.path.isfile(settings_path):
            settings = default_settings
            save_settings()

        if os.path.isfile(settings_path):
            with open(settings_path, 'r') as file:
                settings = json.load(file)
    except Exception as e:
        print(e)
        settings = default_settings


def save_settings():
    try:
        this_script_dir = os.path.dirname(os.path.realpath(__file__))
        config_path = os.path.join(this_script_dir, 'config')
        Path(config_path).mkdir(parents=True, exist_ok=True)
        settings_path = os.path.join(config_path, 'import_options.json')

        with open(settings_path, 'w') as file:
            file.write(json.dumps(settings))
    except Exception as e:
        print(e)


class IMPORT_OT_do_ldraw_import(bpy.types.Operator, ImportHelper):
    """Import an LDraw model File."""

    bl_idname = "import.ldraw"
    bl_label = "Import LDraw"
    bl_options = {'PRESET', 'UNDO'}
    filename_ext = ""

    filter_glob = bpy.props.StringProperty(
        name="Extensions",
        options={'HIDDEN'},
        default="*.mpd;*.ldr;*.dat",
    )

    ldraw_path = bpy.props.StringProperty(
        name="LDraw path",
        description="Full filepath to the LDraw Parts Library (download from http://www.ldraw.org)",
        default=get_setting('ldraw_path'),
    )

    use_alt_colors = bpy.props.BoolProperty(
        name="Use alternate colors",
        options={'HIDDEN'},
        description="Use LDCfgalt.ldr",
        default=get_setting('use_alt_colors'),
    )

    remove_doubles = bpy.props.BoolProperty(
        name="Remove doubles",
        description="Merge overlapping vertices",
        default=get_setting('remove_doubles'),
    )

    merge_distance = bpy.props.FloatProperty(
        name="Merge distance",
        description="Maximum distance between elements to merge",
        default=get_setting('merge_distance'),
        precision=3,
        min=0.0,
    )

    shade_smooth = bpy.props.BoolProperty(
        name="Shade smooth",
        description="Shade smooth",
        default=get_setting('shade_smooth'),
    )

    resolution = bpy.props.EnumProperty(
        name="Part resolution",
        description="Resolution of part primitives, ie. how much geometry they have",
        default=get_setting('resolution'),
        items=(
            ("Low", "Low resolution primitives", "Import using low resolution primitives."),
            ("Standard", "Standard primitives", "Import using standard resolution primitives."),
            ("High", "High resolution primitives", "Import using high resolution primitives."),
        ),
    )

    display_logo = bpy.props.BoolProperty(
        name="Display logo",
        description="Display logo on studs. Requires unofficial parts library to be downloaded",
        default=get_setting('display_logo'),
    )

    # cast items as list or "EnumProperty(..., default='logo3'): not found in enum members"
    # and a messed up menu
    chosen_logo = bpy.props.EnumProperty(
        name="Chosen logo",
        description="Use this logo on studs",
        default=get_setting('chosen_logo'),
        items=list(((l, l, l) for l in special_bricks.logos)),
    )

    smooth_type = bpy.props.EnumProperty(
        name="Smooth type",
        description="Use this strategy to smooth meshes",
        default=get_setting('smooth_type'),
        items=(
            ("auto_smooth", "Auto smooth", "Use auto smooth"),
            ("edge_split", "Edge split", "Use an edge split modifier"),
        ),
    )

    gap_target = bpy.props.EnumProperty(
        name="Gap target",
        description="Where to apply gap",
        default=get_setting('gap_target'),
        items=(
            ("object", "Object", "Scale the object to create the gap"),
            ("mesh", "Mesh", "Transform the mesh to create the gap"),
        ),
    )

    gap_scale_strategy = bpy.props.EnumProperty(
        name="Gap strategy",
        description="How to scale the object to create the gap",
        default=get_setting('gap_scale_strategy'),
        items=(
            ("object", "Object", "Apply gap directly to the object"),
            ("constraint", "Constraint", "Use a constraint, allowing the gap to easily be adjusted later"),
        ),
    )

    no_studs = bpy.props.BoolProperty(
        name="No studs",
        description="Don't import studs",
        default=get_setting('no_studs'),
    )

    parent_to_empty = bpy.props.BoolProperty(
        name="Parent to empty",
        description="Parent the model to an empty",
        default=get_setting('parent_to_empty'),
    )

    import_scale = bpy.props.FloatProperty(
        name="Import scale",
        description="Scale the entire model by this amount",
        default=get_setting('import_scale'),
        precision=2,
        min=0.01,
        max=1.00,
    )

    make_gaps = bpy.props.BoolProperty(
        name="Make gaps",
        description="Puts small gaps between parts",
        default=get_setting('make_gaps'),
    )

    gap_scale = bpy.props.FloatProperty(
        name="Gap scale",
        description="Scale parts by this value to make gaps",
        default=get_setting('gap_scale'),
        precision=3,
        min=0.0,
        max=1.0,
    )

    meta_print_write = bpy.props.BoolProperty(
        name="PRINT/WRITE",
        description="Process PRINT/WRITE meta command",
        default=get_setting('meta_print_write'),
    )

    meta_group = bpy.props.BoolProperty(
        name="GROUP",
        description="Process GROUP meta commands",
        default=get_setting('meta_group'),
    )

    meta_step = bpy.props.BoolProperty(
        name="STEP",
        description="Process STEP meta command",
        default=get_setting('meta_step'),
    )

    meta_clear = bpy.props.BoolProperty(
        name="CLEAR",
        description="Process CLEAR meta command",
        default=get_setting('meta_clear'),
    )

    meta_pause = bpy.props.BoolProperty(
        name="PAUSE",
        description="Process PAUSE meta command",
        default=get_setting('meta_pause'),
    )

    meta_save = bpy.props.BoolProperty(
        name="SAVE",
        description="Process SAVE meta command",
        default=get_setting('meta_save'),
    )

    set_end_frame = bpy.props.BoolProperty(
        name="Set step end frame",
        description="Set the end frame to the last step",
        default=get_setting('set_end_frame'),
    )

    frames_per_step = bpy.props.IntProperty(
        name="Frames per step",
        description="Frames per step",
        default=get_setting('frames_per_step'),
        min=1,
    )

    starting_step_frame = bpy.props.IntProperty(
        name="Starting step frame",
        options={'HIDDEN'},
        description="Frame to add the first STEP meta command",
        default=get_setting('starting_step_frame'),
        min=1,
    )

    set_timelime_markers = bpy.props.BoolProperty(
        name="Set timeline markers",
        description="Set timeline markers for meta commands",
        default=get_setting('set_timelime_markers'),
    )

    import_edges = bpy.props.BoolProperty(
        name="Import edges",
        description="Import edge meshes",
        default=get_setting('import_edges'),
    )

    use_freestyle_edges = bpy.props.BoolProperty(
        name="Use Freestyle edges",
        description="Render LDraw edges using freestyle",
        default=get_setting('use_freestyle_edges'),
    )

    treat_shortcut_as_model = bpy.props.BoolProperty(
        name="Treat shortcuts as models",
        options={'HIDDEN'},
        description="Split shortcut parts into their constituent pieces as if they were models",
        default=get_setting('treat_shortcut_as_model'),
    )

    prefer_unofficial = bpy.props.BoolProperty(
        name="Prefer unofficial parts",
        description="Search for unofficial parts first",
        default=get_setting('prefer_unofficial'),
    )

    recalculate_normals = bpy.props.BoolProperty(
        name="Recalculate normals",
        description="Recalculate normals",
        default=get_setting('recalculate_normals'),
    )

    triangulate = bpy.props.BoolProperty(
        name="Triangulate faces",
        description="Triangulate all faces",
        default=get_setting('triangulate'),
    )

    sharpen_edges = bpy.props.BoolProperty(
        name="Sharpen edges",
        description="Make imported LDraw edges sharp",
        default=get_setting('sharpen_edges'),
    )

    instancing = bpy.props.BoolProperty(
        name="Instance parts",
        options={'HIDDEN'},
        description="Use collection instancing",
        default=get_setting('instancing'),
    )

    profile = bpy.props.BoolProperty(
        name="Profile",
        description="Profile import performance",
        default=False
    )

    def execute(self, context):
        start = time.monotonic()

        # FIXME: error if a new setting key is forgotten
        global settings
        settings = {
            'ldraw_path': self.ldraw_path,
            'prefer_unofficial': self.prefer_unofficial,
            'resolution': self.resolution,
            'use_alt_colors': self.use_alt_colors,
            'remove_doubles': self.remove_doubles,
            'merge_distance': self.merge_distance,
            'shade_smooth': self.shade_smooth,
            'display_logo': self.display_logo,
            'chosen_logo': self.chosen_logo,
            'make_gaps': self.make_gaps,
            'gap_scale': self.gap_scale,
            'no_studs': self.no_studs,
            'set_timelime_markers': self.set_timelime_markers,
            'meta_group': self.meta_group,
            'meta_print_write': self.meta_print_write,
            'meta_step': self.meta_step,
            'meta_clear': self.meta_clear,
            'meta_pause': self.meta_pause,
            'meta_save': self.meta_save,
            'set_end_frame': self.set_end_frame,
            'frames_per_step': self.frames_per_step,
            'starting_step_frame': self.starting_step_frame,
            'smooth_type': self.smooth_type,
            'import_edges': self.import_edges,
            'use_freestyle_edges': self.use_freestyle_edges,
            'import_scale': self.import_scale,
            'parent_to_empty': self.parent_to_empty,
            'gap_target': self.gap_target,
            'gap_scale_strategy': self.gap_scale_strategy,
            'treat_shortcut_as_model': self.treat_shortcut_as_model,
            'recalculate_normals': self.recalculate_normals,
            'triangulate': self.triangulate,
            'sharpen_edges': self.sharpen_edges,
            'instancing': self.instancing,
        }
        save_settings()

        filesystem.ldraw_path = self.ldraw_path
        filesystem.prefer_unofficial = self.prefer_unofficial
        filesystem.resolution = self.resolution
        ldraw_colors.use_alt_colors = self.use_alt_colors
        import_options.remove_doubles = self.remove_doubles
        import_options.merge_distance = self.merge_distance
        import_options.shade_smooth = self.shade_smooth
        import_options.display_logo = self.display_logo
        import_options.chosen_logo = self.chosen_logo
        import_options.make_gaps = self.make_gaps
        import_options.gap_scale = self.gap_scale
        import_options.no_studs = self.no_studs
        import_options.set_timelime_markers = self.set_timelime_markers
        import_options.meta_group = self.meta_group
        import_options.meta_print_write = self.meta_print_write
        import_options.meta_step = self.meta_step
        import_options.meta_clear = self.meta_clear
        import_options.meta_pause = self.meta_pause
        import_options.meta_save = self.meta_save
        import_options.set_end_frame = self.set_end_frame
        import_options.frames_per_step = self.frames_per_step
        import_options.starting_step_frame = self.starting_step_frame
        import_options.smooth_type = self.smooth_type
        import_options.import_edges = self.import_edges
        import_options.use_freestyle_edges = self.use_freestyle_edges
        import_options.import_scale = self.import_scale
        import_options.parent_to_empty = self.parent_to_empty
        import_options.gap_target = self.gap_target
        import_options.gap_scale_strategy = self.gap_scale_strategy
        import_options.treat_shortcut_as_model = self.treat_shortcut_as_model
        import_options.recalculate_normals = self.recalculate_normals
        import_options.triangulate = self.triangulate
        import_options.sharpen_edges = self.sharpen_edges
        import_options.instancing = self.instancing

        if self.profile:
            profiler.enable()
        blender_import.do_import(bpy.path.abspath(self.filepath))
        if self.profile:
            profiler.disable()
            pstats.Stats(profiler).sort_stats('tottime').print_stats()

        print("")
        print("======Import Complete======")
        print(self.filepath)
        print("Part count: {x}".format(**{"x": ldraw_node.part_count}))
        end = time.monotonic()
        elapsed = (end - start)
        print("elapsed: {elapsed}".format(**{"elapsed": elapsed}))
        print("===========================")
        print("")

        return {'FINISHED'}

    # https://docs.blender.org/api/current/bpy.types.UILayout.html
    def draw(self, context):
        layout = self.layout
        # layout.use_property_split = True

        box = layout.box()

        icons = ('NONE', 'QUESTION', 'ERROR', 'CANCEL', 'TRIA_RIGHT', 'TRIA_DOWN', 'TRIA_LEFT', 'TRIA_UP', 'ARROW_LEFTRIGHT', 'PLUS', 'DISCLOSURE_TRI_DOWN', 'DISCLOSURE_TRI_RIGHT', 'RADIOBUT_OFF', 'RADIOBUT_ON', 'MENU')

        box.label(text="LDraw filepath:", icon='NONE')
        box.prop(self, "ldraw_path")

        box.label(text="Import Options")
        # box.prop(self, "use_alt_colors")
        box.prop(self, "resolution", expand=True)
        box.prop(self, "display_logo")
        box.prop(self, "chosen_logo")
        box.prop(self, "profile")

        box.label(text="Scaling Options")
        box.prop(self, "import_scale")
        box.prop(self, "parent_to_empty")
        box.prop(self, "make_gaps")
        box.prop(self, "gap_scale")
        box.prop(self, "gap_target")
        box.prop(self, "gap_scale_strategy")

        box.label(text="Cleanup Options")
        box.prop(self, "remove_doubles")
        box.prop(self, "merge_distance")
        box.prop(self, "smooth_type")
        box.prop(self, "shade_smooth")
        box.prop(self, "recalculate_normals")
        box.prop(self, "triangulate")

        box.label(text="Meta Commands")
        box.prop(self, "meta_group")
        box.prop(self, "meta_print_write")
        box.prop(self, "meta_step")
        box.prop(self, "frames_per_step")
        box.prop(self, "set_end_frame")
        box.prop(self, "meta_clear")
        # box.prop(self, "meta_pause")
        box.prop(self, "meta_save")
        box.prop(self, "set_timelime_markers")

        box.label(text="Extras")
        box.prop(self, "sharpen_edges")
        box.prop(self, "use_freestyle_edges")
        box.prop(self, "import_edges")
        # box.prop(self, "treat_shortcut_as_model")
        box.prop(self, "prefer_unofficial")
        box.prop(self, "no_studs")
