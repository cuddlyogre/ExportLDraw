import bpy

from .import_settings import ImportSettings
from .import_options import ImportOptions
from . import matrices
from . import blender_import


class VertPrecisionOperator(bpy.types.Operator):
    """Round vertex positions to Vertex precision places"""
    bl_idname = "export_ldraw.set_vert_precision"
    bl_label = "Set vertex positions"
    bl_options = {'UNDO'}

    @classmethod
    def poll(cls, context):
        obj = context.active_object
        return obj is not None and obj.type == 'MESH'

    def execute(self, context):
        self.main(context)
        return {'FINISHED'}

    # bpy.context.object.active_material = bpy.data.materials[0]
    def main(self, context):
        for obj in context.selected_objects:
            if obj.type != 'MESH':
                continue

            mesh = obj.data
            precision = obj.ldraw_props.export_precision

            for vertex in mesh.vertices:
                vertex.co[0] = round(vertex.co[0], precision)
                vertex.co[1] = round(vertex.co[1], precision)
                vertex.co[2] = round(vertex.co[2], precision)


class ResetGridOperator(bpy.types.Operator):
    """Set scene grid to 1"""
    bl_idname = "export_ldraw.reset_grid"
    bl_label = "Reset grid"
    bl_options = {'UNDO'}

    def execute(self, context):
        import_scale = 1
        ldu = 1
        context.space_data.overlay.grid_scale = ldu * import_scale
        return {'FINISHED'}


class SnapToBrickOperator(bpy.types.Operator):
    """Set scene grid to 20 LDU"""
    bl_idname = "export_ldraw.snap_to_brick"
    bl_label = "Set grid to brick"
    bl_options = {'UNDO'}

    def execute(self, context):
        ldu = 20
        import_scale = ImportOptions.import_scale
        context.space_data.overlay.grid_scale = ldu * import_scale
        return {'FINISHED'}


class SnapToPlateOperator(bpy.types.Operator):
    """Set scene grid to 8 LDU"""
    bl_idname = "export_ldraw.snap_to_plate"
    bl_label = "Set grid to plate"
    bl_options = {'UNDO'}

    def execute(self, context):
        ldu = 8
        import_scale = ImportOptions.import_scale
        context.space_data.overlay.grid_scale = ldu * import_scale
        return {'FINISHED'}


class ReimportOperator(bpy.types.Operator):
    """Reimport selected parts"""
    bl_idname = "export_ldraw.reimport_part"
    bl_label = "Reimport"
    bl_options = {'UNDO'}

    def execute(self, context):
        for obj in context.selected_objects:
            if obj.type != 'MESH':
                continue

            mesh = blender_import.do_import(obj.ldraw_props.filename, color_code=obj.ldraw_props.color_code, return_mesh=True)
            obj.data = mesh

        return {'FINISHED'}


class RemoveBevelOperator(bpy.types.Operator):
    """Remove bevel modifier from selected objects"""
    bl_idname = "export_ldraw.remove_bevel"
    bl_label = "Remove bevel"
    bl_options = {'UNDO'}

    def execute(self, context):
        for obj in context.selected_objects:
            if obj.type != 'MESH':
                continue

            for mod in obj.modifiers:
                if mod.type == 'BEVEL':
                    obj.modifiers.remove(mod)

        return {'FINISHED'}


class AddBevelOperator(bpy.types.Operator):
    """Remove existing and add bevel modifier to selected objects"""
    bl_idname = "export_ldraw.add_bevel"
    bl_label = "Add bevel"
    bl_options = {'UNDO'}

    def execute(self, context):
        for obj in context.selected_objects:
            if obj.type != 'MESH':
                continue

            pos = 0
            for mod in obj.modifiers:
                if mod.type == 'BEVEL':
                    obj.modifiers.remove(mod)

            modifier = obj.modifiers.new("Bevel", type='BEVEL')
            modifier.limit_method = 'ANGLE'
            modifier.width = ImportOptions.bevel_width * ImportOptions.import_scale
            modifier.segments = ImportOptions.bevel_segments

            keys = obj.modifiers.keys()
            i = keys.index(modifier.name)
            obj.modifiers.move(i, pos)

        return {'FINISHED'}


class AddEdgeSplitOperator(bpy.types.Operator):
    """Remove existing and add edge split modifier to selected objects"""
    bl_idname = "export_ldraw.add_edge_split"
    bl_label = "Add edge split"
    bl_options = {'UNDO'}

    def execute(self, context):
        for obj in context.selected_objects:
            if obj.type != 'MESH':
                continue

            pos = 0
            ii = 0
            for mod in obj.modifiers:
                if mod.type == 'BEVEL':
                    pos = ii
                elif mod.type == 'EDGE_SPLIT':
                    obj.modifiers.remove(mod)
                ii += 1

            modifier = obj.modifiers.new("Edge Split", type='EDGE_SPLIT')
            modifier.use_edge_sharp = True
            modifier.use_edge_angle = True
            modifier.split_angle = matrices.auto_smooth_angle

            keys = obj.modifiers.keys()
            i = keys.index(modifier.name)
            obj.modifiers.move(i, pos)

        return {'FINISHED'}


classesToRegister = [
    VertPrecisionOperator,
    ResetGridOperator,
    SnapToBrickOperator,
    SnapToPlateOperator,
    ReimportOperator,
    RemoveBevelOperator,
    AddBevelOperator,
    AddEdgeSplitOperator,
]

# https://wiki.blender.org/wiki/Reference/Release_Notes/2.80/Python_API/Addons
registerClasses, unregisterClasses = bpy.utils.register_classes_factory(classesToRegister)


def register():
    """Register addon classes"""

    registerClasses()


def unregister():
    """Unregister addon classes"""

    unregisterClasses()


if __name__ == "__main__":
    register()
