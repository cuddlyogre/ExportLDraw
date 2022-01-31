from .import_options import ImportOptions
from .filesystem import FileSystem
from .ldraw_colors import LDrawColor
from . import helpers


class ImportSettings:
    settings = None

    filesystem_defaults = {
        'ldraw_path': FileSystem.locate_ldraw(),
        'prefer_unofficial': FileSystem.defaults['prefer_unofficial'],
        'resolution': FileSystem.defaults['resolution'],
    }

    ldraw_color_defaults = {
        'use_alt_colors': LDrawColor.defaults['use_alt_colors'],
    }

    import_options_defaults = {
        'remove_doubles': ImportOptions.defaults['remove_doubles'],
        'merge_distance': ImportOptions.defaults['merge_distance'],
        'shade_smooth': ImportOptions.defaults['shade_smooth'],
        'display_logo': ImportOptions.defaults['display_logo'],
        'chosen_logo': ImportOptions.defaults['chosen_logo'],
        'make_gaps': ImportOptions.defaults['make_gaps'],
        'gap_scale': ImportOptions.defaults['gap_scale'],
        'no_studs': ImportOptions.defaults['no_studs'],
        'set_timeline_markers': ImportOptions.defaults['set_timeline_markers'],
        'meta_group': ImportOptions.defaults['meta_group'],
        'meta_print_write': ImportOptions.defaults['meta_print_write'],
        'meta_step': ImportOptions.defaults['meta_step'],
        'meta_step_groups': ImportOptions.defaults['meta_step_groups'],
        'meta_clear': ImportOptions.defaults['meta_clear'],
        'meta_pause': ImportOptions.defaults['meta_pause'],
        'meta_save': ImportOptions.defaults['meta_save'],
        'set_end_frame': ImportOptions.defaults['set_end_frame'],
        'frames_per_step': ImportOptions.defaults['frames_per_step'],
        'starting_step_frame': ImportOptions.defaults['starting_step_frame'],
        'smooth_type': ImportOptions.defaults['smooth_type'],
        'import_edges': ImportOptions.defaults['import_edges'],
        'use_freestyle_edges': ImportOptions.defaults['use_freestyle_edges'],
        'import_scale': ImportOptions.defaults['import_scale'],
        'parent_to_empty': ImportOptions.defaults['parent_to_empty'],
        'gap_target': ImportOptions.defaults['gap_target'],
        'gap_scale_strategy': ImportOptions.defaults['gap_scale_strategy'],
        'treat_shortcut_as_model': ImportOptions.defaults['treat_shortcut_as_model'],
        'recalculate_normals': ImportOptions.defaults['recalculate_normals'],
        'triangulate': ImportOptions.defaults['triangulate'],
        'sharpen_edges': ImportOptions.defaults['sharpen_edges'],
        'instancing': ImportOptions.defaults['instancing'],
    }

    default_settings = {**filesystem_defaults, **ldraw_color_defaults, **import_options_defaults}

    @classmethod
    def get_setting(cls, key):
        if cls.settings is None:
            cls.load_settings()

        setting = cls.settings.get(key)
        default = cls.default_settings.get(key)

        # ensure saved type is the same as the default type
        if type(setting) == type(default):
            return setting
        else:
            return default

    @classmethod
    def load_settings(cls):
        cls.settings = helpers.read_json('config', 'ImportOptions.json', cls.default_settings)

    @classmethod
    def save_settings(cls, has_settings):
        cls.settings = {}
        for k, v in cls.default_settings.items():
            cls.settings[k] = getattr(has_settings, k, v)
        helpers.write_json('config', 'ImportOptions.json', cls.settings)

    @classmethod
    def apply_settings(cls):
        for k, v in cls.filesystem_defaults.items():
            setattr(FileSystem, k, cls.settings[k])

        for k, v in cls.ldraw_color_defaults.items():
            setattr(LDrawColor, k, cls.settings[k])

        for k, v in cls.import_options_defaults.items():
            setattr(ImportOptions, k, cls.settings[k])
