import os
import codecs

from . import options

search_paths = []


def reset_caches():
    global search_paths
    search_paths = []


def append_search_path(path):
    if path != "" and os.path.exists(path):
        search_paths.append(path)


def append_search_paths():
    ldraw_path = options.ldraw_path

    append_search_path(os.path.join(ldraw_path))
    append_search_path(os.path.join(ldraw_path, "models"))
    append_search_path(os.path.join(ldraw_path, "unofficial", "lsynth"))

    if options.prefer_unofficial:
        append_unofficial(ldraw_path)
        append_official(ldraw_path)
    else:
        append_official(ldraw_path)
        append_unofficial(ldraw_path)


def append_official(ldraw_path):
    append_search_path(os.path.join(ldraw_path, "parts"))
    if options.resolution == "High":
        append_search_path(os.path.join(ldraw_path, "p", "48"))
    elif options.resolution == "Low":
        append_search_path(os.path.join(ldraw_path, "p", "8"))
    append_search_path(os.path.join(ldraw_path, "p"))


def append_unofficial(ldraw_path):
    append_search_path(os.path.join(ldraw_path, "unofficial", "parts"))
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

    if path == '' or os.path.exists(path):
        return path

    base = os.path.basename(path)  # may be a directory or a file
    dirname = os.path.dirname(path)

    suffix = ''
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
    for path in search_paths:
        full_path = os.path.join(path, part_path)
        if options.debug_text:
            print(full_path)
        full_path = path_insensitive(full_path)
        if os.path.exists(full_path):
            return full_path
    return None
