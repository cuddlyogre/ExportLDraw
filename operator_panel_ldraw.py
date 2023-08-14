import bpy


# bpy.context.mode == 'OBJECT'
# bpy.context.mode == 'EDIT_MESH'
# TODO: panel that add color code to face's material
class CO_PT_ldraw_panel(bpy.types.Panel):
    """This is a test panel"""

    # having a friendly name here gives a _PT_ warning message
    # not setting it works
    # bl_idname = 'CO_PT_ldraw_panel'
    bl_label = 'LDraw'
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_context = 'objectmode'
    bl_category = 'LDraw'

    # @classmethod
    # def poll(cls, context):
    #     selected_objects = context.selected_objects
    #     obj = context.object
    #     obj = context.active_object
    #
    #     if len(selected_objects) < 1:
    #         return False
    #     if obj is None:
    #         return False
    #     if obj.type != 'MESH':
    #         return False
    #     return True

    # https://docs.blender.org/api/current/bpy.context.html?highlight=bpy%20context%20mode#bpy.context.mode
    # https://docs.blender.org/api/current/bpy.types.Panel.html
    # https://docs.blender.org/api/current/bpy.types.UILayout.html
    # https://docs.blender.org/api/current/bpy.types.Operator.html
    # https://docs.blender.org/api/current/bpy.props.html
    # https://b3d.interplanety.org/en/class-naming-conventions-in-blender-2-8-python-api/
    # https://blender.stackexchange.com/a/161584
    def draw(self, context):
        scene = context.scene

        selected_objects = context.selected_objects
        obj = context.object
        obj = context.active_object

        picked_obj = len(selected_objects) > 0

        layout = self.layout
        layout.use_property_split = True

        if not picked_obj:
            layout.separator(factor=0.3)
            col = layout.column()
            col.label(text="Header")

            col.prop(scene.ldraw_props, 'description')
            col.prop(scene.ldraw_props, 'name')
            col.prop(scene.ldraw_props, 'author')
            col.prop(scene.ldraw_props, 'part_type')
            col.prop(scene.ldraw_props, 'actual_part_type')
        else:
            layout.separator(factor=0.3)
            col = layout.column()
            col.label(text="Header")

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
            col.label(text="Part Attributes")
            col.prop(obj.ldraw_props, 'color_code')
            col.prop(obj.ldraw_props, 'filename')

            layout.separator(factor=0.3)
            col = layout.column()
            col.label(text="Export Options")
            if obj.type == 'MESH':
                col.prop(obj.ldraw_props, 'export_polygons')
            col.prop(obj.ldraw_props, 'export_precision')


classesToRegister = [
    CO_PT_ldraw_panel,
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
