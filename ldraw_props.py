import bpy
import getpass


def set_props(ldraw_node, obj, color_code):
    obj.ldraw_props.description = ldraw_node.file.description or ""
    obj.ldraw_props.name = ldraw_node.file.name or ""
    obj.ldraw_props.author = ldraw_node.file.author or ""
    try:
        obj.ldraw_props.part_type = ldraw_node.file.actual_part_type or ""
    except TypeError as e:
        obj.ldraw_props.part_type = 'Unknown'
    obj.ldraw_props.actual_part_type = ldraw_node.file.actual_part_type or ""
    obj.ldraw_props.color_code = color_code


class LDrawProps(bpy.types.PropertyGroup):
    description: bpy.props.StringProperty(
        name="Description",
        description="LDraw description",
        default="",
    )

    name: bpy.props.StringProperty(
        name="Name",
        description="LDraw part name",
        default="",
    )

    author: bpy.props.StringProperty(
        name="Author",
        description="LDraw author",
        default=getpass.getuser(),
    )

    part_type_items = (
        ('Model', 'Model', ''),
        ('Unofficial_Model', 'Unofficial Model', ''),
        ('Part', 'Part', ''),
        ('Unofficial_Part', 'Unofficial Part', ''),
        ('Shortcut', 'Shortcut', ''),
        ('Unofficial_Shortcut', 'Unofficial Shortcut', ''),
        ('Subpart', 'Subpart', ''),
        ('Unofficial_Subpart', 'Unofficial Subpart', ''),
        ('Primitive', 'Primitive', ''),
        ('Unofficial_Primitive', 'Unofficial Primitive', ''),
        ('Unknown', 'Unknown', ''),
    )
    part_type: bpy.props.EnumProperty(
        name="Part type",
        description="LDraw part type",
        items=part_type_items,
        default=part_type_items[-1][0],
    )

    actual_part_type: bpy.props.StringProperty(
        name="Actual part type",
        description="LDraw part type specified in the file",
        default="",
    )

    def test_update(self, context):
        if context.object is None:
            return
        # print(context.object.name)

    color_code: bpy.props.StringProperty(
        name="Color code",
        description="LDraw color code",
        default="16",
        update=test_update
    )

    export_polygons: bpy.props.BoolProperty(
        name="Export polygons",
        description="If true, export object as polygons. If false, export as line type 1.",
        default=False
    )

    export_precision: bpy.props.IntProperty(
        name="Export precision",
        description="Round vertex coordinates to this number of places",
        default=2,
        min=0,
    )

    # color: bpy.props.FloatVectorProperty(
    #     name="Hex Value",
    #     subtype='COLOR',
    #     default=[0.0, 0.0, 0.0],
    # )


classesToRegister = [
    LDrawProps,
]

# https://wiki.blender.org/wiki/Reference/Release_Notes/2.80/Python_API/Addons
registerClasses, unregisterClasses = bpy.utils.register_classes_factory(classesToRegister)


def register():
    """Register addon classes"""

    registerClasses()
    bpy.types.Object.ldraw_props = bpy.props.PointerProperty(type=LDrawProps)


def unregister():
    """Unregister addon classes"""

    unregisterClasses()
    del bpy.types.Object.ldraw_props


if __name__ == "__main__":
    register()
