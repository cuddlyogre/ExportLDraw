import os
import string
import glob
from sys import platform
from pathlib import Path

defaults = dict()
defaults['ldraw_path'] = ''
defaults['prefer_unofficial'] = False
defaults['resolution'] = 'Standard'

ldraw_path = defaults['ldraw_path']
prefer_unofficial = defaults['prefer_unofficial']
resolution = defaults['resolution']

search_paths = []
texture_paths = []
lowercase_paths = {}


def reset_caches():
    global search_paths
    global texture_paths
    global lowercase_paths
    search_paths = []
    texture_paths = []
    lowercase_paths = {}


def append_search_path(path):
    if path[0] != "" and os.path.isdir(path[0]):
        search_paths.append(path)


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


def build_lowercase_paths():
    global lowercase_paths
    lowercase_paths = {}

    for path in search_paths:
        for file in glob.glob(os.path.join(path[0], path[1])):
            lowercase_paths[file.lower()] = file


def build_search_paths(parent_filepath=None):
    reset_caches()

    # https://forums.ldraw.org/thread-24495-post-40577.html#pid40577
    # append top level file's directory
    if parent_filepath is not None:
        append_search_path((os.path.dirname(parent_filepath), '**/*'))
        append_search_path((os.path.dirname(parent_filepath), '*'))

    append_search_path((os.path.join(ldraw_path), '*'))

    if prefer_unofficial:
        append_unofficial_paths()
        append_official_paths()
    else:
        append_official_paths()
        append_unofficial_paths()

    build_lowercase_paths()


def append_paths(folder=''):
    append_search_path((os.path.join(ldraw_path, folder, "models"), '**/*'))
    append_search_path((os.path.join(ldraw_path, folder, "models"), '*'))

    append_search_path((os.path.join(ldraw_path, folder, "parts", "textures"), '**/*'))
    append_search_path((os.path.join(ldraw_path, folder, "parts", "textures"), '*'))

    append_search_path((os.path.join(ldraw_path, folder, "parts"), '**/*'))
    append_search_path((os.path.join(ldraw_path, folder, "parts"), '*'))

    if resolution == "High":
        append_search_path((os.path.join(ldraw_path, folder, "p", "48"), '**/*'))
        append_search_path((os.path.join(ldraw_path, folder, "p", "48"), '*'))
    elif resolution == "Low":
        append_search_path((os.path.join(ldraw_path, folder, "p", "8"), '**/*'))
        append_search_path((os.path.join(ldraw_path, folder, "p", "8"), '*'))

    append_search_path((os.path.join(ldraw_path, folder, "p"), '**/*'))
    append_search_path((os.path.join(ldraw_path, folder, "p"), '*'))


def append_official_paths():
    append_paths()


def append_unofficial_paths():
    append_paths(folder="unofficial")


# https://stackoverflow.com/a/8462613
def path_lowercase(path):
    if path.lower() in lowercase_paths:
        return lowercase_paths[path.lower()]
    return path


def locate(filename):
    part_path = filename.replace("\\", os.path.sep).replace("/", os.path.sep)
    part_path = os.path.expanduser(part_path)

    # full path was specified
    if os.path.isfile(part_path):
        return part_path

    for path in search_paths:
        full_path = os.path.join(path[0], part_path)
        full_path = path_lowercase(full_path)
        if os.path.isfile(full_path):
            return full_path

    # TODO: requests retrieve missing items from ldraw.org

    print(f"missing {filename}")
    return None
