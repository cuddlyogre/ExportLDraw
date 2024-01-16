import bpy

from . import ldraw_operators


# TODO: panel that add color code to face's material
class CO_PT_ldraw_panel(bpy.types.Panel):
    """LDraw part header panel"""

    # having a friendly name here gives a _PT_ warning message
    # not setting it works
    # bl_idname = 'CO_PT_ldraw_panel'
    bl_label = 'Header'
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_context = 'objectmode'
    bl_category = 'LDraw'

    @classmethod
    def poll(cls, context):
        selected_objects = context.selected_objects
        return len(selected_objects) > 0

    def draw(self, context):
        scene = context.scene

        selected_objects = context.selected_objects
        obj = context.object
        obj = context.active_object

        picked_obj = len(selected_objects) > 0

        layout = self.layout
        layout.use_property_split = True
        layout.use_property_decorate = False

        layout.separator(factor=0.3)
        col = layout.column()

        col.prop(obj.ldraw_props, 'description')
        col.prop(obj.ldraw_props, 'name')
        col.prop(obj.ldraw_props, 'author')
        col.prop(obj.ldraw_props, 'part_type')
        col.prop(obj.ldraw_props, 'actual_part_type')
        col.prop(obj.ldraw_props, 'optional_qualifier')
        col.prop(obj.ldraw_props, 'update_date')
        # col.prop(obj.ldraw_props, 'category')
        # col.prop(obj.ldraw_props, 'keywords')
        # col.prop(obj.ldraw_props, 'history')

        layout.separator(factor=0.3)
        col = layout.column()
        col.prop(obj.ldraw_props, 'color_code')
        col.prop(obj.ldraw_props, 'filename')


class CO_PT_ldraw_eo_panel(bpy.types.Panel):
    """LDraw editing tools panel"""

    bl_label = 'Tools'
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_context = 'objectmode'
    bl_category = 'LDraw'

    def draw(self, context):
        scene = context.scene

        selected_objects = context.selected_objects
        obj = context.object
        obj = context.active_object

        picked_obj = len(selected_objects) > 0

        layout = self.layout
        # layout.use_property_split = True
        layout.use_property_decorate = False

        layout.separator(factor=0.3)
        col = layout.column()
        col.operator(ldraw_operators.SnapToBrickOperator.bl_idname)
        col.operator(ldraw_operators.SnapToPlateOperator.bl_idname)
        col.operator(ldraw_operators.ResetGridOperator.bl_idname)

        layout.separator(factor=0.3)
        col = layout.column()
        if picked_obj:
            col.operator(ldraw_operators.AddBevelOperator.bl_idname)
            col.operator(ldraw_operators.RemoveBevelOperator.bl_idname)
            col.operator(ldraw_operators.AddEdgeSplitOperator.bl_idname)
            col.operator(ldraw_operators.ReimportOperator.bl_idname)


class CO_PT_ldraw_cu_panel(bpy.types.Panel):
    """LDraw cleanup panel"""

    bl_label = 'Cleanup'
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_context = 'objectmode'
    bl_category = 'LDraw'

    @classmethod
    def poll(cls, context):
        selected_objects = context.selected_objects
        return len(selected_objects) > 0

    def draw(self, context):
        scene = context.scene

        selected_objects = context.selected_objects
        obj = context.object
        obj = context.active_object

        picked_obj = len(selected_objects) > 0

        layout = self.layout
        # layout.use_property_split = True
        layout.use_property_decorate = False

        col = layout.column()
        col.prop(obj.ldraw_props, 'export_precision')
        col.operator(ldraw_operators.VertPrecisionOperator.bl_idname)


class CO_PT_ldraw_ex_panel(bpy.types.Panel):
    """LDraw export panel"""

    bl_label = 'Export Options'
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_context = 'objectmode'
    bl_category = 'LDraw'

    @classmethod
    def poll(cls, context):
        selected_objects = context.selected_objects
        return len(selected_objects) > 0

    def draw(self, context):
        scene = context.scene

        selected_objects = context.selected_objects
        obj = context.object
        obj = context.active_object

        picked_obj = len(selected_objects) > 0

        layout = self.layout
        # layout.use_property_split = True
        layout.use_property_decorate = False

        col = layout.column()
        col.prop(obj.ldraw_props, 'export_polygons')
        col.prop(obj.ldraw_props, 'export_shade_smooth')
        col.prop(obj.ldraw_props, 'invert_import_scale_matrix')
        col.prop(obj.ldraw_props, 'invert_gap_scale_matrix')


classesToRegister = [
    CO_PT_ldraw_eo_panel,
    CO_PT_ldraw_panel,
    CO_PT_ldraw_cu_panel,
    CO_PT_ldraw_ex_panel,
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

# bpy.context.mode == 'OBJECT'
# bpy.context.mode == 'EDIT_MESH'
# https://docs.blender.org/api/current/bpy.context.html?highlight=bpy%20context%20mode#bpy.context.mode
# https://docs.blender.org/api/current/bpy.types.Panel.html
# https://docs.blender.org/api/current/bpy.types.UILayout.html
# https://docs.blender.org/api/current/bpy.types.Operator.html
# https://docs.blender.org/api/current/bpy.props.html
# https://b3d.interplanety.org/en/class-naming-conventions-in-blender-2-8-python-api/
# https://blender.stackexchange.com/a/161584
