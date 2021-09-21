import os
import string
import glob
from sys import platform
from pathlib import Path

from . import helpers

defaults = dict()
defaults['ldraw_path'] = ''
defaults['prefer_unofficial'] = False
defaults['resolution'] = 'Standard'

ldraw_path = defaults['ldraw_path']
prefer_unofficial = defaults['prefer_unofficial']
resolution = defaults['resolution']

search_paths = []
texture_paths = []
all_files = {}


def reset_caches():
    global search_paths
    global texture_paths
    global all_files
    search_paths = []
    texture_paths = []
    all_files = {}


def get_search_paths(texture=False):
    if texture:
        return texture_paths + search_paths
    else:
        return search_paths


def append_search_path(path):
    if path != "" and os.path.isdir(path):
        search_paths.append(path)


def append_texture_paths(path):
    if path != "" and os.path.exists(path):
        texture_paths.append(path)


def locate_ldraw():
    home = str(Path.home())
    ldraw_path = os.path.join(home, 'ldraw')
    if os.path.isdir(ldraw_path):
        return ldraw_path

    if platform == "linux" or platform == "linux2":
        pass
        # linux
    elif platform == "darwin":
        pass
        # OS X
    elif platform == "win32":
        drive_letters = list(string.ascii_lowercase)
        for drive_letter in drive_letters:
            ldraw_path = os.path.join(os.path.join(f"{drive_letter}:\\", 'ldraw'))
            if os.path.isdir(ldraw_path):
                return ldraw_path

    return ""


def build_search_paths(parent_filepath=None):
    reset_caches()

    # https://forums.ldraw.org/thread-24495-post-40577.html#pid40577
    # append top level file's directory
    if parent_filepath is not None:
        append_search_path(os.path.dirname(parent_filepath))

    append_search_path(os.path.join(ldraw_path))
    append_search_path(os.path.join(ldraw_path, "models"))

    if prefer_unofficial:
        append_unofficial()
        append_official()
    else:
        append_official()
        append_unofficial()

    append_textures()
    build_lowercase_paths()


def build_lowercase_paths():
    global all_files
    all_files = {}

    for path in get_search_paths(texture=True):
        for file in glob.glob(os.path.join(path, '*')):
            all_files[file.lower()] = file


def append_official():
    append_search_path(os.path.join(ldraw_path, "models"))
    append_search_path(os.path.join(ldraw_path, "parts"))
    if resolution == "High":
        append_search_path(os.path.join(ldraw_path, "p", "48"))
    elif resolution == "Low":
        append_search_path(os.path.join(ldraw_path, "p", "8"))
    append_search_path(os.path.join(ldraw_path, "p"))


def append_unofficial():
    append_search_path(os.path.join(ldraw_path, "unofficial", "models"))
    append_search_path(os.path.join(ldraw_path, "unofficial", "parts"))
    if resolution == "High":
        append_search_path(os.path.join(ldraw_path, "unofficial", "p", "48"))
    elif resolution == "Low":
        append_search_path(os.path.join(ldraw_path, "unofficial", "p", "8"))
    append_search_path(os.path.join(ldraw_path, "unofficial", "p"))


def append_textures():
    if prefer_unofficial:
        append_texture_paths(os.path.join(ldraw_path, "unofficial", "parts", "textures"))
        append_texture_paths(os.path.join(ldraw_path, "parts", "textures"))
    else:
        append_texture_paths(os.path.join(ldraw_path, "parts", "textures"))
        append_texture_paths(os.path.join(ldraw_path, "unofficial", "parts", "textures"))


# https://stackoverflow.com/a/8462613
def path_insensitive(path):
    if path.lower() in all_files:
        return all_files[path.lower()]
    return path


def read_file(filepath):
    lines = []
    try:
        with open(filepath, mode='r', encoding='utf-8') as file:
            while True:
                line = file.readline()
                if not line:
                    break
                clean_line = line.strip()
                lines.append(clean_line)
    except Exception as e:
        print(e)
    return lines


def locate(filename, texture=False):
    part_path = filename.replace("\\", os.path.sep)
    part_path = os.path.expanduser(part_path)

    # full path was specified
    if os.path.isfile(part_path):
        return part_path

    full_path = None
    for path in get_search_paths(texture):
        full_path = os.path.join(path, part_path)
        full_path = path_insensitive(full_path)
        if os.path.isfile(full_path):
            return full_path

    if full_path is None:
        # TODO: requests retrieve missing items from ldraw.org
        # full_path = downloader.download_texture(part_path)
        return full_path

    return full_path


def test_fix_string():
    build_search_paths()
    errors = {}
    for path in search_paths:
        paths = glob.glob(os.path.join(path, '**', '*'), recursive=True)
        for path in paths:
            if not os.path.isfile(path):
                continue
            with open(path, 'r') as file:
                try:
                    print(helpers.fix_string_encoding(file.read()))
                except UnicodeDecodeError as e:
                    errors[path] = e
                    # print(e)
                    # print(path)
    print(errors)
