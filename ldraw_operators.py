import bpy
import os

from .definitions import APP_ROOT
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


class RigMinifigOperator(bpy.types.Operator):
    """Rig selected minifig"""
    bl_idname = "export_ldraw.rig_minifig"
    bl_label = "Rig minifigure"
    bl_options = {'UNDO'}

    def execute(self, context):
        name = "minifig_armature"

        path = os.path.join(APP_ROOT, 'inc', 'walk_cycle.blend')
        with bpy.data.libraries.load(path) as (data_from, data_to):
            for obj in data_from.objects:
                if obj == name:
                    data_to.objects.append(obj)
                    break

        target = context.scene.cursor.location.copy()
        selected_objects = context.selected_objects
        for obj in selected_objects:
            if '3815' in obj.ldraw_props.name:
                target[0] = obj.location[0]
                target[1] = obj.location[1] - 0.02  # * ImportOptions.import_scale
                target[2] = obj.location[2] - 0.80  # * ImportOptions.import_scale

        arm_obj = bpy.data.objects.get(name).copy()
        arm_obj.data = bpy.data.armatures[-1]
        arm_obj.location = target
        arm_obj.rotation_euler[0] = 0
        arm_obj.rotation_euler[1] = 0
        arm_obj.rotation_euler[2] = 0
        context.scene.collection.objects.link(arm_obj)

        hand_objs = []
        foot_objs = []

        self.show_bone_groups(arm_obj)

        # deselect or else any parts that are missed will be assigned to the most recent bone
        bpy.ops.object.select_all(action='DESELECT')

        for obj in selected_objects:
            if "Minifig Leg Left" in obj.ldraw_props.description:
                self.parent(arm_obj, obj, 'leg.l')

            if "Minifig Leg Right" in obj.ldraw_props.description:
                self.parent(arm_obj, obj, 'leg.r')

            #    if "Minifig Footwear" in obj.ldraw_props.category:
            #        foot_objs.append(obj)

            if "Minifig Arm Left" in obj.ldraw_props.description:
                self.parent(arm_obj, obj, 'arm.l')

            if "Minifig Arm Right" in obj.ldraw_props.description:
                self.parent(arm_obj, obj, 'arm.r')

            if "Minifig Head" in obj.ldraw_props.description:
                self.parent(arm_obj, obj, 'head')

            if "Minifig Hips" in obj.ldraw_props.description:
                self.parent(arm_obj, obj, 'torso')

            if "Minifig Torso" in obj.ldraw_props.description:
                self.parent(arm_obj, obj, 'torso_rock')

            if "Minifig Hand" in obj.ldraw_props.description:
                hand_objs.append(obj)

            #    if "Minifig Accessory" in obj.ldraw_props.category:
            #        hand_objs.append(obj)

            if "Minifig Headwear" in obj.ldraw_props.category:
                self.parent(arm_obj, obj, 'head_accessory')

            if "Minifig Hipwear" in obj.ldraw_props.category:
                self.parent(arm_obj, obj, 'torso')

            if "Minifig Neckwear" in obj.ldraw_props.category:
                self.parent(arm_obj, obj, 'torso_rock')

        collection = hand_objs
        l_bone_name = 'hand.l'
        r_bone_name = 'hand.r'
        self.rig_twins(arm_obj, collection, l_bone_name, r_bone_name)

        self.hide_bone_groups(arm_obj)

        # for obj in bpy.data.objects:
        #    selected = obj.name in selected_names
        #    obj.select_set(selected)

        return {'FINISHED'}

    def parent(self, arm, obj, bone_name):
        obj.select_set(True)

        arm.select_set(True)
        bpy.context.view_layer.objects.active = arm
        arm.data.bones.active = arm.data.bones[bone_name]

        bpy.ops.object.parent_set(type='BONE', keep_transform=True)
        bpy.ops.object.select_all(action='DESELECT')

    def set_bone_layer(self, bone, layer):
        for x in range(0, 32):
            if x == layer:
                bone.layers[x] = True
            else:
                bone.layers[x] = False

    def rig_twins(self, arm_obj, collection, l_bone_name, r_bone_name):
        l_bone = arm_obj.data.bones[l_bone_name]
        r_bone = arm_obj.data.bones[r_bone_name]
        l_bone_loc = arm_obj.location + l_bone.head
        r_bone_loc = arm_obj.location + r_bone.head
        if len(collection) == 1:
            # if there is one hand, assign it to the closest hand bone

            obj1 = collection[0]

            d1l = obj1.location - l_bone_loc
            d1r = obj1.location - r_bone_loc

            if d1l < d1r:
                self.parent(arm_obj, obj1, l_bone_name)
            else:
                self.parent(arm_obj, obj1, r_bone_name)
        elif len(collection) == 2:
            # if there are two hands, assign the first one to the closest hand bone
            # and assign the other hand to the other hand bone

            obj1 = collection[0]
            obj2 = collection[1]

            d1l = obj1.location - l_bone_loc
            d1r = obj1.location - r_bone_loc

            if d1l < d1r:
                self.parent(arm_obj, obj1, r_bone_name)
                self.parent(arm_obj, obj2, l_bone_name)
            else:
                self.parent(arm_obj, obj1, l_bone_name)
                self.parent(arm_obj, obj2, r_bone_name)

    def show_bone_groups(self, arm_obj):
        if bpy.app.version >= (4,):
            # make all used bone groups visible so they can be used here
            # can't select bones in hidden groups
            arm_obj.data.collections["Bones"].is_visible = True
            arm_obj.data.collections["rock"].is_visible = True

    # if the collection is not visible, we can't select the bones
    # so show them all at the start then hide them when we're done
    def hide_bone_groups(self, arm_obj):
        if bpy.app.version >= (4,):
            arm_obj.data.collections["rock"].is_visible = False
        else:
            # bpy.ops.object.mode_set(mode='OBJECT', toggle=False)
            bpy.ops.object.mode_set(mode='EDIT', toggle=False)

            rock_bones_layer = 3
            # for bone in arm_obj.data.edit_bones:
            for bone_name in ['torso_rock', 'body_rock', 'body_rock.l', 'body_rock.r', 'body_rock.fr', 'body_rock.bk']:
                bone = arm_obj.data.edit_bones[bone_name]
                # do it twice or else they aren't moved from 0
                self.set_bone_layer(bone, rock_bones_layer)
                self.set_bone_layer(bone, rock_bones_layer)
            arm_obj.data.layers[rock_bones_layer] = False

            bpy.ops.object.mode_set(mode='OBJECT', toggle=False)
            # bpy.ops.object.mode_set(mode='POSE', toggle=False)


classesToRegister = [
    VertPrecisionOperator,
    ResetGridOperator,
    SnapToBrickOperator,
    SnapToPlateOperator,
    ReimportOperator,
    RemoveBevelOperator,
    AddBevelOperator,
    AddEdgeSplitOperator,
    RigMinifigOperator,
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
