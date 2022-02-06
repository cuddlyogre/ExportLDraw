import os
import sys
from shutil import copytree, ignore_patterns, rmtree

from definitions import APP_ROOT

version = sys.argv[1]
addon_name = sys.argv[2]

app_data_dir = os.path.expandvars(r'%APPDATA%\Blender Foundation\Blender')
addons_dir = r'scripts\addons'
blender_dir = os.path.join(app_data_dir, version, addons_dir)
target = os.path.join(blender_dir, addon_name)

if not os.path.isdir(blender_dir):
    exit(f"{blender_dir} does not exist")

print(f"deploying to {target}")

patterns = {".git", "__pycache__", ".idea", ".test"}

if os.path.isdir(target):
    rmtree(target)

copytree(APP_ROOT, target, dirs_exist_ok=True, ignore=ignore_patterns(*patterns))

pycache_dir = os.path.join(target, "__pycache__")
if os.path.isdir(pycache_dir):
    rmtree(pycache_dir)
