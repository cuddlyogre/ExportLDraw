import bpy
import mathutils

from . import strings
from . import import_options
from . import matrices

from . import blender_materials
from . import ldraw_colors


# https://blender.stackexchange.com/a/91687
# for f in bm.faces:
#     f.smooth = True
# mesh = context.object.data
# for f in mesh.polygons:
#     f.use_smooth = True
# values = [True] * len(mesh.polygons)
# mesh.polygons.foreach_set("use_smooth", values)
# bpy.context.object.active_material.use_backface_culling = True
# bpy.context.object.active_material.use_screen_refraction = True
# apply materials to mesh
# then mesh cleanup
# then apply slope materials
# this order is important because bmesh_ops causes
# mesh.polygons to get out of sync geometry.face_info
# which causes materials and slope materials to be applied incorrectly
# https://blender.stackexchange.com/questions/414/how-to-use-bmesh-to-add-verts-faces-and-edges-to-existing-geometry
# bm.verts.index_update()

# https://youtu.be/cQ0qtcSymDI?t=356
# https://www.youtube.com/watch?v=cQ0qtcSymDI&t=0s
# https://www.blenderguru.com/articles/cycles-input-encyclopedia
# https://blenderscripting.blogspot.com/2011/05/blender-25-python-moving-object-origin.html
# https://blenderartists.org/t/how-to-set-origin-to-center/687111
# https://blenderartists.org/t/modifying-object-origin-with-python/507305/3
# https://blender.stackexchange.com/questions/414/how-to-use-bmesh-to-add-verts-faces-and-edges-to-existing-geometry
# https://devtalk.blender.org/t/bmesh-adding-new-verts/11108/2
# f1 = Vector((rand(-5, 5),rand(-5, 5),rand(-5, 5)))
# f2 = Vector((rand(-5, 5),rand(-5, 5),rand(-5, 5)))
# f3 = Vector((rand(-5, 5),rand(-5, 5),rand(-5, 5)))
# f = [f1, f2, f3]
# for f in enumerate(faces):
#     this_vert = bm.verts.new(f)
# used_indexes = list(indexes.values())
# bigger = []
# smaller = []
# remaining = (collections.Counter(bigger) - collections.Counter(smaller)).elements()
# unused_indexes = list(remaining)
# print(list(indexes.values()))
# print(len(used_vertices))
# if index is not referenced in vertices. remove from vertices
# apply_materials
# len(faces) do not always match len(mesh.polygons)
# print(len(faces))
# print(len(mesh.polygons))
# if you validate here, the polygon count changes,
# which causes polygon count and geometry.face_info count to get out of sync, causing missing face colors
# mesh.validate()
# mesh.update(calc_edges=True)
# print(len(mesh.polygons))
# slower than bmesh.ops.remove_doubles but necessary if importing to a system without a remove doubles function
