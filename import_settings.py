import os.path

from .import_options import ImportOptions
from .filesystem import FileSystem
from .ldraw_color import LDrawColor
from . import helpers


class ImportSettings:
    settings_path = os.path.join('config', 'ImportOptions.json')
    settings = None

    filesystem_defaults = FileSystem.defaults
    ldraw_color_defaults = LDrawColor.defaults
    import_options_defaults = ImportOptions.defaults

    default_settings = {
        **filesystem_defaults,
        **ldraw_color_defaults,
        **import_options_defaults
    }

    @classmethod
    def settings_dict(cls, key):
        return {
            "get": lambda self: cls.get_setting(key),
            "set": lambda self, value: cls.set_setting(key, value),
        }

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
    def __setattr__(cls, key, value):
        cls.settings[key] = value

    @classmethod
    def set_setting(cls, k, v):
        cls.settings[k] = v

    @classmethod
    def load_settings(cls):
        cls.settings = helpers.read_json(cls.settings_path, cls.default_settings)

    @classmethod
    def save_settings(cls):
        helpers.write_json(cls.settings_path, cls.settings)

    @classmethod
    def apply_settings(cls):
        for k, v in cls.filesystem_defaults.items():
            setattr(FileSystem, k, cls.settings[k])

        for k, v in cls.ldraw_color_defaults.items():
            setattr(LDrawColor, k, cls.settings[k])

        for k, v in cls.import_options_defaults.items():
            setattr(ImportOptions, k, cls.settings[k])
