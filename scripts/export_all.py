import bpy
import json
import glob
import os
import sys
import sqlite3

from ExportLDraw.geometry_data import FaceData
from ExportLDraw.ldraw_node import LDrawNode
from ExportLDraw.operator_import import IMPORT_OT_do_ldraw_import
from ExportLDraw.operator_export import EXPORT_OT_do_ldraw_export


def process_parts():
    import_times = {}
    export_times = {}

    # Connect to the database (or create it if it doesn't exist)
    conn = sqlite3.connect('ldraw.sqlite')
    cursor = conn.cursor()

    # cursor.execute('DELETE FROM parts')
    cursor.execute('DROP TABLE IF EXISTS parts')
    conn.commit()
    conn.execute('VACUUM')
    cursor.execute("""
                   CREATE TABLE IF NOT EXISTS parts (
                       id       INTEGER PRIMARY KEY AUTOINCREMENT,
                       name     TEXT,
                       contents TEXT
                   );
                   """)

    cursor.execute("""
                   CREATE INDEX IF NOT EXISTS name_index ON parts (name);
                   """)

    paths = glob.glob(r"d:\ldraw\parts\*")
    for path in paths:
        if not os.path.isfile(path): continue
        # bpy.ops.object.select_all(action='DESELECT')

        for obj in list(bpy.data.objects):
            bpy.data.objects.remove(obj, do_unlink=True)
        print("deleting objects")
        for mesh in list(bpy.data.meshes):
            bpy.data.meshes.remove(mesh)
        print("deleting meshes")
        for mat in list(bpy.data.materials):
            bpy.data.materials.remove(mat, do_unlink=True)
        print("deleting materials")
        for tex in list(bpy.data.textures):
            bpy.data.textures.remove(tex, do_unlink=True)
        print("deleting textures")
        for img in list(bpy.data.images):
            bpy.data.images.remove(img, do_unlink=True)
        print("deleting images")
        for node_group in list(bpy.data.node_groups):
            bpy.data.node_groups.remove(node_group, do_unlink=True)
        print("deleting node groups")
        for collection in list(bpy.data.collections):
            if collection != bpy.context.scene.collection:  # Avoid removing the default scene collection
                bpy.data.collections.remove(collection, do_unlink=True)
        print("deleting collections")
        for armature in list(bpy.data.armatures):
            bpy.data.armatures.remove(armature, do_unlink=True)
        print("deleting armatures")
        for camera in list(bpy.data.cameras):
            bpy.data.cameras.remove(camera, do_unlink=True)
        print("deleting cameras")
        for curve in list(bpy.data.curves):
            bpy.data.curves.remove(curve, do_unlink=True)
        print("deleting curves")
        for font in list(bpy.data.fonts):
            bpy.data.fonts.remove(font, do_unlink=True)
        print("deleting fonts")
        for grease_pencil in list(bpy.data.grease_pencils):
            bpy.data.grease_pencils.remove(grease_pencil, do_unlink=True)
        print("deleting grease pencils")
        for lattice in list(bpy.data.lattices):
            bpy.data.lattices.remove(lattice, do_unlink=True)
        print("deleting lattices")
        for light in list(bpy.data.lights):
            bpy.data.lights.remove(light, do_unlink=True)
        print("deleting lights")
        for metaball in list(bpy.data.metaballs):
            bpy.data.metaballs.remove(metaball, do_unlink=True)
        print("deleting metaballs")
        for particle in list(bpy.data.particles):
            bpy.data.particles.remove(particle, do_unlink=True)
        print("deleting particles")
        for pointcloud in list(bpy.data.pointclouds):
            bpy.data.pointclouds.remove(pointcloud, do_unlink=True)
        print("deleting pointclouds")
        for speaker in list(bpy.data.speakers):
            bpy.data.speakers.remove(speaker, do_unlink=True)
        print("deleting speakers")
        for volume in list(bpy.data.volumes):
            bpy.data.volumes.remove(volume, do_unlink=True)
        print("deleting volumes")
        for world in list(bpy.data.worlds):
            bpy.data.worlds.remove(world, do_unlink=True)
        print("deleting worlds")

        # Purge orphaned data
        bpy.ops.outliner.orphans_purge(do_local_ids=True, do_linked_ids=True, do_recursive=True)
        print("purged orphaned data")

        out_root = fr"d:/desktop/heads"
        os.makedirs(out_root, exist_ok=True)

        bpy.ops.ldraw_exporter.import_operator(
            filepath=path,
            ldraw_path=r"d:\ldraw",
            make_gaps=False,
            import_scale=1.0,
        )

        bpy.context.view_layer.objects.active = bpy.context.scene.objects[0]
        for obj in bpy.context.scene.objects:
            obj.ldraw_props.export_polygons = True
            obj.ldraw_props.export_precision = 5
            if not obj.select_get():
                obj.select_set(True)

        bpy.ops.ldraw_exporter.export_operator(
            filepath=fr"{out_root}/{os.path.basename(path)}",
            ldraw_path=r"d:/ldraw",
        )

        insert_query = '''
                       INSERT OR IGNORE INTO parts (name, contents)
                       VALUES (?, ?)
                       '''

        values = EXPORT_OT_do_ldraw_export.exported_string
        cursor.execute(insert_query, values)
        conn.commit()

        import_times[path] = IMPORT_OT_do_ldraw_import.elapsed
        export_times[path] = EXPORT_OT_do_ldraw_export.elapsed

    conn.close()

    with open(fr"d:/desktop/import_times.json", "w", encoding='utf-8') as f:
        s = sorted(import_times.items(), key=lambda ele: ele[1], reverse=True)
        f.write(json.dumps(s, indent=2))

    with open(fr"d:/desktop/export_times.json", "w", encoding='utf-8') as f:
        s = sorted(export_times.items(), key=lambda ele: ele[1], reverse=True)
        f.write(json.dumps(s, indent=2))


def process_file(file):
    print(file)
    if not os.path.isfile(file): return None
    return file
    if not os.path.basename(file).startswith('3626'): return None
    with open(file, "r", encoding='utf-8') as f:
        contents = f.read()
        if contents.startswith('0 Minifig Head ') or contents.startswith("0 Minifig Head\n"):
            return file
            return contents
    return None


def get_parts():
    paths = glob.glob(r"d:\ldraw\parts\*")

    parts = []
    for path in paths:
        p = process_file(path)
        if p is not None:
            parts.append(p)

    filepath = bpy.data.filepath
    dirname = os.path.dirname(filepath)
    with open(f"d:/desktop/parts.json", "w", encoding='utf-8') as f:
        f.write(json.dumps(parts, indent=2))

    print(f"\nTotal parts processed: {len(parts)}")

    return parts


if __name__ == "__main__":
    # parts = get_parts()
    # print(len(parts))

    # p = parts[0:50]
    # p = parts[50:100]
    # p = parts[100:150]
    # p = parts[150:200]
    # p = parts[200:250]
    # p = parts[250:300]
    # p = parts[300:350]
    # p = parts[350:400]

    process_parts()
