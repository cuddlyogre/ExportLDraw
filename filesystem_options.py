import os
import string
from sys import platform
from pathlib import Path
import tempfile


LDRAW_FOLDER_NAME = 'ldraw'


def locate_ldraw():
    # home = os.path.expanduser("~")
    home = str(Path.home())
    ldraw_path = os.path.join(home, LDRAW_FOLDER_NAME)
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
            ldraw_path = os.path.join(os.path.join(f"{drive_letter}:\\", LDRAW_FOLDER_NAME))
            if os.path.isdir(ldraw_path):
                return ldraw_path
    return ""


def locate_studio_ldraw():
    if platform == "linux" or platform == "linux2":
        pass
        # linux
    elif platform == "darwin":
        pass
        # OS X
    elif platform == "win32":
        for root in [os.environ["ProgramFiles"], os.environ["ProgramFiles(x86)"]]:
            studio_path = os.path.join(root, 'Studio 2.0', LDRAW_FOLDER_NAME)
            if os.path.isdir(studio_path):
                return studio_path

    return ""


def locate_studio_custom_parts():
    if platform == "linux" or platform == "linux2":
        pass
        # linux
    elif platform == "darwin":
        pass
        # OS X
    elif platform == "win32":
        path = os.path.join(os.getenv('LOCALAPPDATA'), 'Stud.io', 'CustomParts')
        if os.path.isdir(path):
            return path

    return ""


def is_case_sensitive_filesystem():
    # By default mkstemp() creates a file with
    # a name that begins with 'tmp' (lowercase)
    tmphandle, tmppath = tempfile.mkstemp()
    if os.path.exists(tmppath.upper()):
        return False
    else:
        return True


class FileSystemOptions:
    defaults = {}

    defaults["ldraw_path"] = locate_ldraw()
    ldraw_path = defaults["ldraw_path"]

    defaults["studio_ldraw_path"] = locate_studio_ldraw()
    studio_ldraw_path = defaults["studio_ldraw_path"]

    defaults["studio_custom_parts_path"] = locate_studio_custom_parts()
    studio_custom_parts_path = defaults["studio_custom_parts_path"]

    defaults["prefer_studio"] = False
    prefer_studio = defaults["prefer_studio"]

    defaults["prefer_unofficial"] = False
    prefer_unofficial = defaults["prefer_unofficial"]

    defaults["case_sensitive_filesystem"] = is_case_sensitive_filesystem()
    case_sensitive_filesystem = defaults["case_sensitive_filesystem"]

    resolution_choices = (
        ("Low", "Low resolution primitives", "Import using low resolution primitives."),
        ("Standard", "Standard primitives", "Import using standard resolution primitives."),
        ("High", "High resolution primitives", "Import using high resolution primitives."),
    )

    defaults["resolution"] = 1
    resolution = defaults["resolution"]

    @staticmethod
    def resolution_value():
        return FileSystemOptions.resolution_choices[FileSystemOptions.resolution][0]
