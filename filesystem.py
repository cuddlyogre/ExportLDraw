import os
import codecs
import string
import glob
from sys import platform
from pathlib import Path

if __name__ == "__main__":
    import options
else:
    from . import options

search_paths = []
texture_paths = []
all_files = {}


def reset_caches():
    global search_paths
    global texture_paths
    search_paths = []
    texture_paths = []


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

    ldraw_path = options.ldraw_path

    # https://forums.ldraw.org/thread-24495-post-40577.html#pid40577
    # append top level file's directory
    if parent_filepath is not None:
        append_search_path(os.path.dirname(parent_filepath))

    append_search_path(os.path.join(ldraw_path))
    append_search_path(os.path.join(ldraw_path, "models"))

    if options.prefer_unofficial:
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
    ldraw_path = options.ldraw_path
    append_search_path(os.path.join(ldraw_path, "models"))
    append_search_path(os.path.join(ldraw_path, "parts"))
    if options.resolution == "High":
        append_search_path(os.path.join(ldraw_path, "p", "48"))
    elif options.resolution == "Low":
        append_search_path(os.path.join(ldraw_path, "p", "8"))
    append_search_path(os.path.join(ldraw_path, "p"))


def append_unofficial():
    ldraw_path = options.ldraw_path
    append_search_path(os.path.join(ldraw_path, "unofficial", "models"))
    append_search_path(os.path.join(ldraw_path, "unofficial", "parts"))
    if options.resolution == "High":
        append_search_path(os.path.join(ldraw_path, "unofficial", "p", "48"))
    elif options.resolution == "Low":
        append_search_path(os.path.join(ldraw_path, "unofficial", "p", "8"))
    append_search_path(os.path.join(ldraw_path, "unofficial", "p"))


def append_textures():
    ldraw_path = options.ldraw_path
    if options.prefer_unofficial:
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


def fix_string_encoding(string):
    new_string = string
    if type(string) is str:
        new_string = bytes(string.encode())
    for codec in [codecs.BOM_UTF8, codecs.BOM_UTF16, codecs.BOM_UTF32]:
        new_string = new_string.replace(codec, b'')
    new_string = new_string.decode()
    return new_string


def read_file(filepath):
    lines = []
    filepath = path_insensitive(filepath)
    if os.path.isfile(filepath):
        with open(filepath, 'r') as file:
            for line in file.readlines():
                fixed_line = fix_string_encoding(line).strip()
                lines.append(fixed_line)
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
        if options.debug_text:
            print(full_path)
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
                    print(fix_string_encoding(file.read()))
                except UnicodeDecodeError as e:
                    errors[path] = e
                    # print(e)
                    # print(path)
    print(errors)


# http://www.holly-wood.it/ldview-en.html
def export_index(texture=False):
    # 'https://www.ldraw.org/library/official/images/parts/3001.png'
    # 'https://www.ldraw.org/library/unofficial/images/parts/6003.png'

    this_script_dir = os.path.dirname(os.path.realpath(__file__))

    thumbs = os.path.join(this_script_dir, 'thumbs')
    Path(thumbs).mkdir(parents=True, exist_ok=True)

    if __name__ == "__main__":
        options.ldraw_path = locate_ldraw()
        options.ldview_path = 'C:\\"Program Files (x86)"\\LDView\\LDView.exe'

    build_search_paths()

    width = 64
    height = 64
    default_zoom = 1
    default_matrix = "".join([str(x) for x in [
        0.707107, 0, 0.707107,
        0.353553, 0.866025, -0.353553,
        -0.612372, 0.5, 0.612372
    ]])

    for path in get_search_paths(texture):
        paths = glob.glob(os.path.join(path, '**', '*'), recursive=True)
        for path in paths:
            if os.path.isfile(path) and Path(path).suffix in ['.dat', '.ldr', '.mpd']:
                thumb_file_path = f"{os.path.join(thumbs, path.replace(os.path.join(options.ldraw_path, ''), ''))}.bmp"
                Path(os.path.dirname(thumb_file_path)).mkdir(parents=True, exist_ok=True)
                command = fr""" {options.ldview_path} "{path}" -SaveSnapshot="{thumb_file_path}" -SaveWidth={width} -SaveHeight={height} -DefaultMatrix={default_matrix} -DefaultZoom={default_zoom} """
                print(command)
                os.system(command)
            # print(path)

# if __name__ == "__main__":
#     export_index()
