import os
import sys
from shutil import copytree, ignore_patterns, rmtree

app_data_dir = os.path.expandvars(r'%APPDATA%\Blender Foundation\Blender')
version = '2.93'
if len(sys.argv) > 1:
    version = sys.argv[1]
addons_dir = r'scripts\addons'
blender_dir = os.path.join(app_data_dir, version, addons_dir)
if not os.path.isdir(blender_dir):
    exit(f"{blender_dir} does not exist")

addon_name = 'ExportLDraw'
target = os.path.join(blender_dir, addon_name)
print(f"deploying to {target}")

this_script_dir = os.path.dirname(os.path.realpath(__file__))
patterns = {".git", "__pycache__", ".idea"}
rmtree(target)
copytree(this_script_dir, target, dirs_exist_ok=True, ignore=ignore_patterns(*patterns))

pycache_dir = os.path.join(target, "__pycache__")
if os.path.isdir(pycache_dir):
    rmtree(pycache_dir)
