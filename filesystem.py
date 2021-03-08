import os
import codecs
import string
import glob
from sys import platform
from pathlib import Path

from . import options

search_paths = []


def reset_caches():
    global search_paths
    search_paths = []


def append_search_path(path):
    if path != "" and os.path.exists(path):
        search_paths.append(path)


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


def build_search_paths():
    reset_caches()

    append_search_path(os.path.join(options.ldraw_path))
    append_search_path(os.path.join(options.ldraw_path, "models"))

    if options.prefer_unofficial:
        append_unofficial()
        append_official()
    else:
        append_official()
        append_unofficial()


def append_official():
    ldraw_path = options.ldraw_path
    append_search_path(os.path.join(ldraw_path, "models"))
    append_search_path(os.path.join(ldraw_path, "parts"))
    append_search_path(os.path.join(ldraw_path, "parts", "textures"))
    if options.resolution == "High":
        append_search_path(os.path.join(ldraw_path, "p", "48"))
    elif options.resolution == "Low":
        append_search_path(os.path.join(ldraw_path, "p", "8"))
    append_search_path(os.path.join(ldraw_path, "p"))


def append_unofficial():
    ldraw_path = options.ldraw_path
    append_search_path(os.path.join(ldraw_path, "unofficial", "models"))
    append_search_path(os.path.join(ldraw_path, "unofficial", "parts"))
    append_search_path(os.path.join(ldraw_path, "unofficial", "parts", "textures"))
    if options.resolution == "High":
        append_search_path(os.path.join(ldraw_path, "unofficial", "p", "48"))
    elif options.resolution == "Low":
        append_search_path(os.path.join(ldraw_path, "unofficial", "p", "8"))
    append_search_path(os.path.join(ldraw_path, "unofficial", "p"))


# https://stackoverflow.com/a/8462613
def path_insensitive(path):
    """
    Get a case-insensitive path for use on a case sensitive system.

    >>> path_insensitive('/Home')
    '/home'
    >>> path_insensitive('/Home/chris')
    '/home/chris'
    >>> path_insensitive('/HoME/CHris/')
    '/home/chris/'
    >>> path_insensitive('/home/CHRIS')
    '/home/chris'
    >>> path_insensitive('/Home/CHRIS/.gtk-bookmarks')
    '/home/chris/.gtk-bookmarks'
    >>> path_insensitive('/home/chris/.GTK-bookmarks')
    '/home/chris/.gtk-bookmarks'
    >>> path_insensitive('/HOME/Chris/.GTK-bookmarks')
    '/home/chris/.gtk-bookmarks'
    >>> path_insensitive("/HOME/Chris/I HOPE this doesn't exist")
    "/HOME/Chris/I HOPE this doesn't exist"
    """

    return _path_insensitive(path) or path


def _path_insensitive(path):
    """
    Recursive part of path_insensitive to do the work.
    """

    if path == "" or os.path.exists(path):
        return path

    base = os.path.basename(path)  # may be a directory or a file
    dirname = os.path.dirname(path)

    suffix = ""
    if not base:  # dir ends with a slash?
        if len(dirname) < len(path):
            suffix = path[:len(path) - len(dirname)]

        base = os.path.basename(dirname)
        dirname = os.path.dirname(dirname)

    if not os.path.exists(dirname):
        dirname = _path_insensitive(dirname)
        if not dirname:
            return

    # at this point, the directory exists but not the file

    try:  # we are expecting dirname to be a directory, but it could be a file
        files = os.listdir(dirname)
    except OSError:
        return

    baselow = base.lower()
    try:
        basefinal = next(fl for fl in files if fl.lower() == baselow)
    except StopIteration:
        return

    if basefinal:
        return os.path.join(dirname, basefinal) + suffix
    else:
        return


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
                    print(fix_string(file.read()))
                except UnicodeDecodeError as e:
                    errors[path] = e
                    # print(e)
                    # print(path)
    print(errors)


def fix_string(string):
    new_string = string
    if type(string) is str:
        new_string = bytes(string.encode())
    for codec in [codecs.BOM_UTF8, codecs.BOM_UTF16, codecs.BOM_UTF32]:
        new_string = new_string.replace(codec, b'')
    new_string = new_string.decode()
    return new_string


def read_file(filepath):
    filepath = path_insensitive(filepath)
    with open(filepath, 'r') as file:
        string = fix_string(file.read())
        return string.strip().splitlines()


def locate(filename, parent_filepath=None):
    part_path = filename.replace("\\", os.path.sep)
    part_path = os.path.expanduser(part_path)

    # full path was specified
    if os.path.exists(part_path):
        return part_path

    # ldraw spec says to search in the current file's directory
    # a path relative to anything in search_paths
    file_search_paths = []
    file_search_paths.append(os.path.dirname(part_path))
    if options.debug_text:
        print(parent_filepath)
    if parent_filepath is not None:
        file_search_paths.append(os.path.dirname(parent_filepath))

    for path in file_search_paths + search_paths:
        full_path = os.path.join(path, part_path)
        if options.debug_text:
            print(full_path)
        full_path = path_insensitive(full_path)
        if os.path.exists(full_path):
            return full_path
    return None
