import os
import codecs
import string
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
    append_search_path(os.path.join(options.ldraw_path, "parts"))
    append_search_path(os.path.join(options.ldraw_path, "parts", "textures"))
    if options.resolution == "High":
        append_search_path(os.path.join(options.ldraw_path, "p", "48"))
    elif options.resolution == "Low":
        append_search_path(os.path.join(options.ldraw_path, "p", "8"))
    append_search_path(os.path.join(options.ldraw_path, "p"))


def append_unofficial():
    append_search_path(os.path.join(options.ldraw_path, "unofficial", "parts"))
    append_search_path(os.path.join(options.ldraw_path, "unofficial", "parts", "textures"))
    if options.resolution == "High":
        append_search_path(os.path.join(options.ldraw_path, "unofficial", "p", "48"))
    elif options.resolution == "Low":
        append_search_path(os.path.join(options.ldraw_path, "unofficial", "p", "8"))
    append_search_path(os.path.join(options.ldraw_path, "unofficial", "p"))


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


def read_file(filepath):
    filepath = path_insensitive(filepath)
    with open(filepath, 'rb') as file:
        string = file.read()
        for c in [codecs.BOM_UTF8, codecs.BOM_UTF16, codecs.BOM_UTF32]:
            string = string.replace(c, b'')
        # print(string)
        return string.decode('utf-8').strip().splitlines()


def locate(filename):
    part_path = filename.replace("\\", os.path.sep)
    part_path = os.path.expanduser(part_path)

    # full path was specified
    if os.path.exists(part_path):
        return part_path

    # ldraw spec says to search in the current file's directory
    # a path relative to anything in search_paths
    filename_folder = os.path.dirname(part_path)
    file_search_paths = [filename_folder]

    for path in search_paths + file_search_paths:
        full_path = os.path.join(path, part_path)
        if options.debug_text:
            print(full_path)
        full_path = path_insensitive(full_path)
        if os.path.exists(full_path):
            return full_path
    return None
