import os
import string
import glob
from sys import platform
from pathlib import Path


class FileSystem:
    defaults = {}

    defaults['ldraw_path'] = ''
    ldraw_path = defaults['ldraw_path']

    defaults['prefer_unofficial'] = False
    prefer_unofficial = defaults['prefer_unofficial']

    defaults['resolution'] = 'Standard'
    resolution = defaults['resolution']

    __search_paths = []
    __texture_paths = []
    __lowercase_paths = {}

    @classmethod
    def reset_caches(cls):
        cls.__search_paths = []
        cls.__texture_paths = []
        cls.__lowercase_paths = {}

    @staticmethod
    def locate_ldraw():
        ldraw_folder_name = 'ldraw'

        home = str(Path.home())
        ldraw_path = os.path.join(home, ldraw_folder_name)
        if os.path.isdir(ldraw_path):
            return ldraw_path

        if platform == "linux" or platform == "linux2":
            pass
            # linux
        elif platform == "darwin":
            pass
            # OS X
        elif platform == "win32":
            for drive_letter in string.ascii_lowercase:
                ldraw_path = os.path.join(os.path.join(f"{drive_letter}:\\", ldraw_folder_name))
                if os.path.isdir(ldraw_path):
                    return ldraw_path
        return ""

    @classmethod
    def build_search_paths(cls, parent_filepath=None):
        cls.reset_caches()

        # https://forums.ldraw.org/thread-24495-post-40577.html#pid40577
        # append top level file's directory
        if parent_filepath is not None:
            cls.__append_search_path((os.path.dirname(parent_filepath), '**/*'))
            cls.__append_search_path((os.path.dirname(parent_filepath), '*'))

        cls.__append_search_path((os.path.join(cls.ldraw_path), '*'))

        if cls.prefer_unofficial:
            cls.__append_unofficial_paths()
            cls.__append_official_paths()
        else:
            cls.__append_official_paths()
            cls.__append_unofficial_paths()

        cls.__build_lowercase_paths()

    @classmethod
    def locate(cls, filename):
        part_path = filename.replace("\\", os.path.sep).replace("/", os.path.sep)
        part_path = os.path.expanduser(part_path)

        # full path was specified
        if os.path.isfile(part_path):
            return part_path

        for path in cls.__search_paths:
            full_path = os.path.join(path[0], part_path)
            full_path = cls.__path_lowercase(full_path)
            if os.path.isfile(full_path):
                return full_path

        # TODO: requests retrieve missing items from ldraw.org

        print(f"missing {filename}")
        return None

    @classmethod
    def __append_search_path(cls, path):
        if path[0] != "" and os.path.isdir(path[0]):
            cls.__search_paths.append(path)

    @classmethod
    def __build_lowercase_paths(cls):
        cls.__lowercase_paths = {}

        for path in cls.__search_paths:
            for file in glob.glob(os.path.join(path[0], path[1])):
                cls.__lowercase_paths[file.lower()] = file

    @classmethod
    def __append_paths(cls, folder=''):
        cls.__append_search_path((os.path.join(cls.ldraw_path, folder, "models"), '**/*'))
        cls.__append_search_path((os.path.join(cls.ldraw_path, folder, "models"), '*'))

        cls.__append_search_path((os.path.join(cls.ldraw_path, folder, "parts", "textures"), '**/*'))
        cls.__append_search_path((os.path.join(cls.ldraw_path, folder, "parts", "textures"), '*'))

        cls.__append_search_path((os.path.join(cls.ldraw_path, folder, "parts"), '**/*'))
        cls.__append_search_path((os.path.join(cls.ldraw_path, folder, "parts"), '*'))

        if cls.resolution == "High":
            cls.__append_search_path((os.path.join(cls.ldraw_path, folder, "p", "48"), '**/*'))
            cls.__append_search_path((os.path.join(cls.ldraw_path, folder, "p", "48"), '*'))
        elif cls.resolution == "Low":
            cls.__append_search_path((os.path.join(cls.ldraw_path, folder, "p", "8"), '**/*'))
            cls.__append_search_path((os.path.join(cls.ldraw_path, folder, "p", "8"), '*'))

        cls.__append_search_path((os.path.join(cls.ldraw_path, folder, "p"), '**/*'))
        cls.__append_search_path((os.path.join(cls.ldraw_path, folder, "p"), '*'))

    @classmethod
    def __append_official_paths(cls):
        cls.__append_paths()

    @classmethod
    def __append_unofficial_paths(cls):
        cls.__append_paths(folder="unofficial")

    @classmethod
    # https://stackoverflow.com/a/8462613
    def __path_lowercase(cls, path):
        if path.lower() in cls.__lowercase_paths:
            return cls.__lowercase_paths[path.lower()]
        return path
