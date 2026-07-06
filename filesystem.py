import os
import glob

from .filesystem_options import FileSystemOptions

class FileSystem:
    search_dirs = []
    lowercase_paths = {}

    @classmethod
    def reset_caches(cls):
        cls.search_dirs.clear()
        cls.lowercase_paths.clear()

    @classmethod
    def build_search_paths(cls, parent_filepath=None):
        ldraw_roots = []

        # append top level file's directory
        # https://forums.ldraw.org/thread-24495-post-40577.html#pid40577
        # post discussing path order, this order was chosen
        # except that the current file's dir isn't scanned, only the current dir of the top level file
        # https://forums.ldraw.org/thread-24495-post-45340.html#pid45340
        if parent_filepath is not None:
            ldraw_roots.append(os.path.dirname(parent_filepath))

        if FileSystemOptions.prefer_studio:
            if FileSystemOptions.prefer_unofficial:
                ldraw_roots.append(os.path.join(FileSystemOptions.studio_ldraw_path, "unofficial"))
                ldraw_roots.append(os.path.join(FileSystemOptions.ldraw_path, "unofficial"))
                ldraw_roots.append(os.path.join(FileSystemOptions.studio_custom_parts_path))
                ldraw_roots.append(os.path.join(FileSystemOptions.studio_ldraw_path))
                ldraw_roots.append(os.path.join(FileSystemOptions.ldraw_path))
            else:
                ldraw_roots.append(os.path.join(FileSystemOptions.studio_custom_parts_path))
                ldraw_roots.append(os.path.join(FileSystemOptions.studio_ldraw_path))
                ldraw_roots.append(os.path.join(FileSystemOptions.ldraw_path))
                ldraw_roots.append(os.path.join(FileSystemOptions.studio_ldraw_path, "unofficial"))
                ldraw_roots.append(os.path.join(FileSystemOptions.ldraw_path, "unofficial"))
        else:
            if FileSystemOptions.prefer_unofficial:
                ldraw_roots.append(os.path.join(FileSystemOptions.ldraw_path, "unofficial"))
                ldraw_roots.append(os.path.join(FileSystemOptions.studio_ldraw_path, "unofficial"))
                ldraw_roots.append(os.path.join(FileSystemOptions.ldraw_path))
                ldraw_roots.append(os.path.join(FileSystemOptions.studio_custom_parts_path))
                ldraw_roots.append(os.path.join(FileSystemOptions.studio_ldraw_path))
            else:
                ldraw_roots.append(os.path.join(FileSystemOptions.ldraw_path))
                ldraw_roots.append(os.path.join(FileSystemOptions.studio_custom_parts_path))
                ldraw_roots.append(os.path.join(FileSystemOptions.studio_ldraw_path))
                ldraw_roots.append(os.path.join(FileSystemOptions.ldraw_path, "unofficial"))
                ldraw_roots.append(os.path.join(FileSystemOptions.studio_ldraw_path, "unofficial"))

        for root in ldraw_roots:
            path = root
            cls.append_search_path(path, root=True)

            path = os.path.join(root, "p")
            cls.append_search_path(path)

            if FileSystemOptions.resolution_value() == "High":
                path = os.path.join(root, "p", "48")
                cls.append_search_path(path)
            elif FileSystemOptions.resolution_value() == "Low":
                path = os.path.join(root, "p", "8")
                cls.append_search_path(path)

            path = os.path.join(root, "parts")
            cls.append_search_path(path)

            path = os.path.join(root, "parts", "textures")
            cls.append_search_path(path)

            path = os.path.join(root, "models")
            cls.append_search_path(path)

    # build a list of folders to search for parts
    # build a map of lowercase to actual filenames
    @classmethod
    def append_search_path(cls, path, root=False):
        cls.search_dirs.append(path)
        if FileSystemOptions.case_sensitive_filesystem:
            cls.append_lowercase_paths(path, '*')
            if root:
                return
            cls.append_lowercase_paths(path, '**/*')

    @classmethod
    def append_lowercase_paths(cls, path, pattern):
        files = glob.glob(os.path.join(path, pattern))
        for file in files:
            cls.lowercase_paths.setdefault(file.lower(), file)

    @classmethod
    def locate(cls, filename):
        part_path = filename.replace("\\", os.path.sep).replace("/", os.path.sep)
        part_path = os.path.expanduser(part_path)

        # full path was specified
        if os.path.isfile(part_path):
            return part_path

        for dir in cls.search_dirs:
            full_path = os.path.join(dir, part_path)
            if os.path.isfile(full_path):
                return full_path

            lc_path = full_path.lower()
            if lc_path in cls.lowercase_paths:
                full_path = cls.lowercase_paths.get(lc_path)

            if os.path.isfile(full_path):
                return full_path

        # TODO: requests retrieve missing items from ldraw.org

        print(f"missing {filename}")
        return None
