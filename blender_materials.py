import bpy
import mathutils

from .ldraw_colors import LDrawColors


class BlenderMaterials:
    """Creates and stores a cache of materials for Blender"""

    material_cache = {}
    curved_walls = False
    add_subsurface = False

    @classmethod
    def reset_caches(cls):
        cls.material_cache = {}

    @classmethod
    def create_blender_node_groups(cls):
        cls.__create_blender_distance_to_center_node_group()
        cls.__create_blender_vector_element_power_node_group()
        cls.__create_blender_convert_to_normals_node_group()
        cls.__create_blender_concave_walls_node_group()
        cls.__create_blender_slope_texture_node_group()

        # Originally based on ideas from https://www.youtube.com/watch?v=V3wghbZ-Vh4
        # "Create your own PBR Material [Fixed!]" by BlenderGuru
        # Updated with Principled Shader, if available
        cls.__create_blender_fresnel_node_group()
        cls.__create_blender_reflection_node_group()
        cls.__create_blender_dielectric_node_group()

        cls.__create_blender_lego_standard_node_group()
        cls.__create_blender_lego_transparent_node_group()
        cls.__create_blender_lego_glass_node_group()
        cls.__create_blender_lego_transparent_fluorescent_node_group()
        cls.__create_blender_lego_rubber_node_group()
        cls.__create_blender_lego_rubber_translucent_node_group()
        cls.__create_blender_lego_emission_node_group()
        cls.__create_blender_lego_chrome_node_group()
        cls.__create_blender_lego_pearlescent_node_group()
        cls.__create_blender_lego_metal_node_group()
        cls.__create_blender_lego_glitter_node_group()
        cls.__create_blender_lego_speckle_node_group()
        cls.__create_blender_lego_milky_white_node_group()

    @classmethod
    def get_material(cls, color_code, is_slope_material=False):
        pure_color_code = color_code
        if is_slope_material:
            color_code = color_code + "_s"

        # If it's already in the cache, use that
        if color_code in cls.material_cache:
            result = cls.material_cache[color_code]
            return result

        # Create a name for the material based on the color
        if cls.curved_walls and not is_slope_material:
            blender_name = "Material_{0}_c".format(color_code)
        else:
            blender_name = "Material_{0}".format(color_code)

        # Create new material
        col = LDrawColors.get_color(pure_color_code)
        material = cls.__create_node_based_material(blender_name, col, is_slope_material)

        # Add material to cache
        cls.material_cache[color_code] = material
        return material

    @staticmethod
    def __get_diffuse_color(color):
        return color + (1.0,)

    @classmethod
    def __create_node_based_material(cls, blender_name, col, is_slope_material=False):
        """Set Cycles Material Values."""

        # Reuse current material if it exists, otherwise create a new material
        if bpy.data.materials.get(blender_name) is None:
            material = bpy.data.materials.new(blender_name)
        else:
            material = bpy.data.materials[blender_name]

        # Use nodes
        material.use_nodes = True

        nodes = material.node_tree.nodes
        links = material.node_tree.links

        # Remove any existing nodes
        for n in nodes:
            nodes.remove(n)

        if col is not None:
            color = col["color"] + (1.0,)
            material.diffuse_color = cls.__get_diffuse_color(col["color"])

            is_transparent = col["alpha"] < 1.0

            if is_transparent:
                material.blend_method = 'BLEND'
                material.refraction_depth = 0.1
                material.use_screen_refraction = True

            if col["name"] == "Milky_White":
                cls.__create_cycles_milky_white(nodes, links, color)
            elif col["luminance"] > 0:
                cls.__create_cycles_emission(nodes, links, color, col["alpha"], col["luminance"])
            elif col["material"] == "CHROME":
                cls.__create_cycles_chrome(nodes, links, color)
            elif col["material"] == "PEARLESCENT":
                cls.__create_cycles_pearlescent(nodes, links, color)
            elif col["material"] == "METAL":
                cls.__create_cycles_metal(nodes, links, color)
            elif col["material"] == "GLITTER":
                cls.__create_cycles_glitter(nodes, links, color, col["secondary_color"])
            elif col["material"] == "SPECKLE":
                cls.__create_cycles_speckle(nodes, links, color, col["secondary_color"])
            elif col["material"] == "RUBBER":
                cls.__create_cycles_rubber(nodes, links, color, col["alpha"])
            else:
                cls.__create_cycles_basic(nodes, links, color, col["alpha"], col["name"])

            if is_slope_material:
                cls.__create_cycles_slope_texture(nodes, links, 0.6)
            elif cls.curved_walls:
                cls.__create_cycles_concave_walls(nodes, links, 0.2)

            material["Lego.isTransparent"] = is_transparent
            return material

        cls.__create_cycles_basic(nodes, links, (1.0, 1.0, 0.0, 1.0), 1.0, "")
        material["Lego.isTransparent"] = False
        return material

    @staticmethod
    def __node_concave_walls(nodes, strength, x, y):
        node = nodes.new('ShaderNodeGroup')
        node.node_tree = bpy.data.node_groups['Concave Walls']
        node.location = x, y
        node.inputs['Strength'].default_value = strength
        return node

    @staticmethod
    def __node_slope_texture(nodes, strength, x, y):
        node = nodes.new('ShaderNodeGroup')
        node.node_tree = bpy.data.node_groups['Slope Texture']
        node.location = x, y
        node.inputs['Strength'].default_value = strength
        return node

    @staticmethod
    def __node_lego_standard(nodes, color, x, y):
        node = nodes.new('ShaderNodeGroup')
        node.node_tree = bpy.data.node_groups['Lego Standard']
        node.location = x, y
        node.inputs['Color'].default_value = color
        return node

    @staticmethod
    def __node_lego_transparent_fluorescent(nodes, color, x, y):
        node = nodes.new('ShaderNodeGroup')
        node.node_tree = bpy.data.node_groups['Lego Transparent Fluorescent']
        node.location = x, y
        node.inputs['Color'].default_value = color
        return node

    @staticmethod
    def __node_lego_transparent(nodes, color, x, y):
        node = nodes.new('ShaderNodeGroup')
        node.node_tree = bpy.data.node_groups['Lego Transparent']
        node.location = x, y
        node.inputs['Color'].default_value = color
        return node

    @staticmethod
    def __node_lego_glass(nodes, color, x, y):
        node = nodes.new('ShaderNodeGroup')
        node.node_tree = bpy.data.node_groups['Lego Glass']
        node.location = x, y
        node.inputs['Color'].default_value = color
        return node

    @staticmethod
    def __node_lego_rubber_solid(nodes, color, x, y):
        node = nodes.new('ShaderNodeGroup')
        node.node_tree = bpy.data.node_groups['Lego Rubber Solid']
        node.location = x, y
        node.inputs['Color'].default_value = color
        return node

    @staticmethod
    def __node_lego_rubber_translucent(nodes, color, x, y):
        node = nodes.new('ShaderNodeGroup')
        node.node_tree = bpy.data.node_groups['Lego Rubber Translucent']
        node.location = x, y
        node.inputs['Color'].default_value = color
        return node

    @staticmethod
    def __node_lego_emission(nodes, color, luminance, x, y):
        node = nodes.new('ShaderNodeGroup')
        node.node_tree = bpy.data.node_groups['Lego Emission']
        node.location = x, y
        node.inputs['Color'].default_value = color
        node.inputs['Luminance'].default_value = luminance
        return node

    @staticmethod
    def __node_lego_chrome(nodes, color, x, y):
        node = nodes.new('ShaderNodeGroup')
        node.node_tree = bpy.data.node_groups['Lego Chrome']
        node.location = x, y
        node.inputs['Color'].default_value = color
        return node

    @staticmethod
    def __node_lego_pearlescent(nodes, color, x, y):
        node = nodes.new('ShaderNodeGroup')
        node.node_tree = bpy.data.node_groups['Lego Pearlescent']
        node.location = x, y
        node.inputs['Color'].default_value = color
        return node

    @staticmethod
    def __node_lego_metal(nodes, color, x, y):
        node = nodes.new('ShaderNodeGroup')
        node.node_tree = bpy.data.node_groups['Lego Metal']
        node.location = x, y
        node.inputs['Color'].default_value = color
        return node

    @staticmethod
    def __node_lego_glitter(nodes, color, glittercolor, x, y):
        node = nodes.new('ShaderNodeGroup')
        node.node_tree = bpy.data.node_groups['Lego Glitter']
        node.location = x, y
        node.inputs['Color'].default_value = color
        node.inputs['Glitter Color'].default_value = glittercolor
        return node

    @staticmethod
    def __node_lego_speckle(nodes, color, specklecolor, x, y):
        node = nodes.new('ShaderNodeGroup')
        node.node_tree = bpy.data.node_groups['Lego Speckle']
        node.location = x, y
        node.inputs['Color'].default_value = color
        node.inputs['Speckle Color'].default_value = specklecolor
        return node

    @staticmethod
    def __node_lego_milky_white(nodes, color, x, y):
        node = nodes.new('ShaderNodeGroup')
        node.node_tree = bpy.data.node_groups['Lego Milky White']
        node.location = x, y
        node.inputs['Color'].default_value = color
        return node

    @staticmethod
    def __node_mix(nodes, factor, x, y):
        node = nodes.new('ShaderNodeMixShader')
        node.location = x, y
        node.inputs['Fac'].default_value = factor
        return node

    @staticmethod
    def __node_output(nodes, x, y):
        node = nodes.new('ShaderNodeOutputMaterial')
        node.location = x, y
        return node

    @staticmethod
    def __node_dielectric(nodes, roughness, reflection, transparency, ior, x, y):
        node = nodes.new('ShaderNodeGroup')
        node.node_tree = bpy.data.node_groups['PBR-Dielectric']
        node.location = x, y
        node.inputs['Roughness'].default_value = roughness
        node.inputs['Reflection'].default_value = reflection
        node.inputs['Transparency'].default_value = transparency
        node.inputs['IOR'].default_value = ior
        return node

    @classmethod
    def __node_principled(cls, nodes, subsurface, sub_rad, metallic, roughness, clearcoat, clearcoat_roughness, ior, transmission, x, y):
        node = nodes.new('ShaderNodeBsdfPrincipled')
        node.location = x, y
        if cls.add_subsurface:
            node.inputs['Subsurface'].default_value = subsurface
            node.inputs['Subsurface Radius'].default_value = mathutils.Vector((sub_rad, sub_rad, sub_rad))
        node.inputs['Metallic'].default_value = metallic
        node.inputs['Roughness'].default_value = roughness
        node.inputs['Clearcoat'].default_value = clearcoat
        node.inputs['Clearcoat Roughness'].default_value = clearcoat_roughness
        node.inputs['IOR'].default_value = ior
        node.inputs['Transmission'].default_value = transmission
        return node

    @staticmethod
    def __node_hsv(nodes, h, s, v, x, y):
        node = nodes.new('ShaderNodeHueSaturation')
        node.location = x, y
        node.inputs[0].default_value = h
        node.inputs[1].default_value = s
        node.inputs[2].default_value = v
        return node

    @staticmethod
    def __node_separate_hsv(nodes, x, y):
        node = nodes.new('ShaderNodeSeparateHSV')
        node.location = x, y
        return node

    @staticmethod
    def __node_combine_hsv(nodes, x, y):
        node = nodes.new('ShaderNodeCombineHSV')
        node.location = x, y
        return node

    @staticmethod
    def __node_tex_coord(nodes, x, y):
        node = nodes.new('ShaderNodeTexCoord')
        node.location = x, y
        return node

    @staticmethod
    def __node_tex_wave(nodes, wave_type, wave_profile, scale, distortion, detail, detail_scale, x, y):
        node = nodes.new('ShaderNodeTexWave')
        node.wave_type = wave_type
        node.wave_profile = wave_profile
        node.inputs[1].default_value = scale
        node.inputs[2].default_value = distortion
        node.inputs[3].default_value = detail
        node.inputs[4].default_value = detail_scale
        node.location = x, y
        return node

    @staticmethod
    def __node_diffuse(nodes, roughness, x, y):
        node = nodes.new('ShaderNodeBsdfDiffuse')
        node.location = x, y
        node.inputs['Color'].default_value = (1, 1, 1, 1)
        node.inputs['Roughness'].default_value = roughness
        return node

    @staticmethod
    def __node_glass(nodes, roughness, ior, distribution, x, y):
        node = nodes.new('ShaderNodeBsdfGlass')
        node.location = x, y
        node.distribution = distribution
        node.inputs['Color'].default_value = (1, 1, 1, 1)
        node.inputs['Roughness'].default_value = roughness
        node.inputs['IOR'].default_value = ior
        return node

    @staticmethod
    def __node_fresnel(nodes, ior, x, y):
        node = nodes.new('ShaderNodeFresnel')
        node.location = x, y
        node.inputs['IOR'].default_value = ior
        return node

    @staticmethod
    def __node_glossy(nodes, color, roughness, distribution, x, y):
        node = nodes.new('ShaderNodeBsdfGlossy')
        node.location = x, y
        node.distribution = distribution
        node.inputs['Color'].default_value = color
        node.inputs['Roughness'].default_value = roughness
        return node

    @staticmethod
    def __node_translucent(nodes, x, y):
        node = nodes.new('ShaderNodeBsdfTranslucent')
        node.location = x, y
        return node

    @staticmethod
    def __node_transparent(nodes, x, y):
        node = nodes.new('ShaderNodeBsdfTransparent')
        node.location = x, y
        return node

    @staticmethod
    def __node_add_shader(nodes, x, y):
        node = nodes.new('ShaderNodeAddShader')
        node.location = x, y
        return node

    @staticmethod
    def __node_volume(nodes, density, x, y):
        node = nodes.new('ShaderNodeVolumeAbsorption')
        node.inputs['Density'].default_value = density
        node.location = x, y
        return node

    @staticmethod
    def __node_light_path(nodes, x, y):
        node = nodes.new('ShaderNodeLightPath')
        node.location = x, y
        return node

    @staticmethod
    def __node_math(nodes, operation, x, y):
        node = nodes.new('ShaderNodeMath')
        node.operation = operation
        node.location = x, y
        return node

    @staticmethod
    def __node_vector_math(nodes, operation, x, y):
        node = nodes.new('ShaderNodeVectorMath')
        node.operation = operation
        node.location = x, y
        return node

    @staticmethod
    def __node_emission(nodes, x, y):
        node = nodes.new('ShaderNodeEmission')
        node.location = x, y
        return node

    @staticmethod
    def __node_voronoi(nodes, scale, x, y):
        node = nodes.new('ShaderNodeTexVoronoi')
        node.location = x, y
        node.inputs['Scale'].default_value = scale
        return node

    @staticmethod
    def __node_gamma(nodes, gamma, x, y):
        node = nodes.new('ShaderNodeGamma')
        node.location = x, y
        node.inputs['Gamma'].default_value = gamma
        return node

    @staticmethod
    def __node_color_ramp(nodes, pos1, color1, pos2, color2, x, y):
        node = nodes.new('ShaderNodeValToRGB')
        node.location = x, y
        node.color_ramp.elements[0].position = pos1
        node.color_ramp.elements[0].color = color1
        node.color_ramp.elements[1].position = pos2
        node.color_ramp.elements[1].color = color2
        return node

    @staticmethod
    def __node_noise_texture(nodes, scale, detail, distortion, x, y):
        node = nodes.new('ShaderNodeTexNoise')
        node.location = x, y
        node.inputs['Scale'].default_value = scale
        node.inputs['Detail'].default_value = detail
        node.inputs['Distortion'].default_value = distortion
        return node

    @staticmethod
    def __node_bump_shader(nodes, strength, distance, x, y):
        node = nodes.new('ShaderNodeBump')
        node.location = x, y
        node.inputs[0].default_value = strength
        node.inputs[1].default_value = distance
        return node

    @staticmethod
    def __node_refraction(nodes, roughness, ior, x, y):
        node = nodes.new('ShaderNodeBsdfRefraction')
        node.inputs['Roughness'].default_value = roughness
        node.inputs['IOR'].default_value = ior
        node.location = x, y
        return node

    @staticmethod
    def __get_group(nodes):
        for x in nodes:
            if x.type == 'GROUP':
                return x
        return None

    @classmethod
    def __create_cycles_concave_walls(cls, nodes, links, strength):
        """Concave wall normals for Cycles render engine"""
        node = cls.__node_concave_walls(nodes, strength, -200, 5)
        out = cls.__get_group(nodes)
        if out is not None:
            links.new(node.outputs['Normal'], out.inputs['Normal'])

    @classmethod
    def __create_cycles_slope_texture(cls, nodes, links, strength):
        """Slope face normals for Cycles render engine"""
        node = cls.__node_slope_texture(nodes, strength, -200, 5)
        out = cls.__get_group(nodes)
        if out is not None:
            links.new(node.outputs['Normal'], out.inputs['Normal'])

    @classmethod
    def __create_cycles_basic(cls, nodes, links, diff_color, alpha, col_name):
        """Basic Material for Cycles render engine."""

        if alpha < 1:
            if LDrawColors.is_fluorescent_transparent(col_name):
                node = cls.__node_lego_transparent_fluorescent(nodes, diff_color, 0, 5)
            else:
                # node = cls.__node_lego_transparent(nodes, diff_color, 0, 5)
                node = cls.__node_lego_glass(nodes, diff_color, 0, 5)
        else:
            node = cls.__node_lego_standard(nodes, diff_color, 0, 5)

        out = cls.__node_output(nodes, 200, 0)
        links.new(node.outputs['Shader'], out.inputs[0])

    @classmethod
    def __create_cycles_emission(cls, nodes, links, diff_color, alpha, luminance):
        """Emission material for Cycles render engine."""

        node = cls.__node_lego_emission(nodes, diff_color, luminance / 100.0, 0, 5)
        out = cls.__node_output(nodes, 200, 0)
        links.new(node.outputs['Shader'], out.inputs[0])

    @classmethod
    def __create_cycles_chrome(cls, nodes, links, diff_color):
        """Chrome material for Cycles render engine."""

        node = cls.__node_lego_chrome(nodes, diff_color, 0, 5)
        out = cls.__node_output(nodes, 200, 0)
        links.new(node.outputs['Shader'], out.inputs[0])

    @classmethod
    def __create_cycles_pearlescent(cls, nodes, links, diff_color):
        """Pearlescent material for Cycles render engine."""

        node = cls.__node_lego_pearlescent(nodes, diff_color, 0, 5)
        out = cls.__node_output(nodes, 200, 0)
        links.new(node.outputs['Shader'], out.inputs[0])

    @classmethod
    def __create_cycles_metal(cls, nodes, links, diff_color):
        """Metal material for Cycles render engine."""

        node = cls.__node_lego_metal(nodes, diff_color, 0, 5)
        out = cls.__node_output(nodes, 200, 0)
        links.new(node.outputs['Shader'], out.inputs[0])

    @classmethod
    def __create_cycles_glitter(cls, nodes, links, diff_color, glitter_color):
        """Glitter material for Cycles render engine."""

        glitter_color = LDrawColors.lighten_rgba(glitter_color, 0.5)
        node = cls.__node_lego_glitter(nodes, diff_color, glitter_color, 0, 5)
        out = cls.__node_output(nodes, 200, 0)
        links.new(node.outputs['Shader'], out.inputs[0])

    @classmethod
    def __create_cycles_speckle(cls, nodes, links, diff_color, speckle_color):
        """Speckle material for Cycles render engine."""

        speckle_color = LDrawColors.lighten_rgba(speckle_color, 0.5)
        node = cls.__node_lego_speckle(nodes, diff_color, speckle_color, 0, 5)
        out = cls.__node_output(nodes, 200, 0)
        links.new(node.outputs['Shader'], out.inputs[0])

    @classmethod
    def __create_cycles_rubber(cls, nodes, links, diff_color, alpha):
        """Rubber material colors for Cycles render engine."""

        out = cls.__node_output(nodes, 200, 0)

        if alpha < 1.0:
            rubber = cls.__node_lego_rubber_translucent(nodes, diff_color, 0, 5)
        else:
            rubber = cls.__node_lego_rubber_solid(nodes, diff_color, 0, 5)

        links.new(rubber.outputs[0], out.inputs[0])

    @classmethod
    def __create_cycles_milky_white(cls, nodes, links, diff_color):
        """Milky White material for Cycles render engine."""

        node = cls.__node_lego_milky_white(nodes, diff_color, 0, 5)
        out = cls.__node_output(nodes, 200, 0)
        links.new(node.outputs['Shader'], out.inputs[0])

    @staticmethod
    def __create_group(name, x1, y1, x2, y2, create_shader_output):
        group = bpy.data.node_groups.new(name, 'ShaderNodeTree')

        # create input node
        node_input = group.nodes.new('NodeGroupInput')
        node_input.location = (x1, y1)

        # create output node
        node_output = group.nodes.new('NodeGroupOutput')
        node_output.location = (x2, y2)
        if create_shader_output:
            group.outputs.new('NodeSocketShader', 'Shader')
        return group, node_input, node_output

    @classmethod
    def __create_blender_distance_to_center_node_group(cls):
        if bpy.data.node_groups.get('Distance-To-Center') is None:
            print("createBlenderDistanceToCenterNodeGroup #create")
            # create a group
            group, node_input, node_output = cls.__create_group('Distance-To-Center', -930, 0, 240, 0, False)
            group.outputs.new('NodeSocketVectorDirection', 'Vector')

            # create nodes
            node_texture_coordinate = cls.__node_tex_coord(group.nodes, -730, 0)

            node_vector_subtraction1 = cls.__node_vector_math(group.nodes, 'SUBTRACT', -535, 0)
            node_vector_subtraction1.inputs[1].default_value[0] = 0.5
            node_vector_subtraction1.inputs[1].default_value[1] = 0.5
            node_vector_subtraction1.inputs[1].default_value[2] = 0.5

            node_normalize = cls.__node_vector_math(group.nodes, 'NORMALIZE', -535, -245)
            node_dot_product = cls.__node_vector_math(group.nodes, 'DOT_PRODUCT', -340, -125)

            node_multiply = group.nodes.new('ShaderNodeMixRGB')
            node_multiply.blend_type = 'MULTIPLY'
            node_multiply.inputs['Fac'].default_value = 1.0
            node_multiply.location = -145, -125

            node_vector_subtraction2 = cls.__node_vector_math(group.nodes, 'SUBTRACT', 40, 0)

            # link nodes together
            group.links.new(node_texture_coordinate.outputs['Generated'], node_vector_subtraction1.inputs[0])
            group.links.new(node_texture_coordinate.outputs['Normal'], node_normalize.inputs[0])
            group.links.new(node_vector_subtraction1.outputs['Vector'], node_dot_product.inputs[0])
            group.links.new(node_normalize.outputs['Vector'], node_dot_product.inputs[1])
            group.links.new(node_dot_product.outputs['Value'], node_multiply.inputs['Color1'])
            group.links.new(node_normalize.outputs['Vector'], node_multiply.inputs['Color2'])
            group.links.new(node_vector_subtraction1.outputs['Vector'], node_vector_subtraction2.inputs[0])
            group.links.new(node_multiply.outputs['Color'], node_vector_subtraction2.inputs[1])
            group.links.new(node_vector_subtraction2.outputs['Vector'], node_output.inputs['Vector'])

    @classmethod
    def __create_blender_vector_element_power_node_group(cls):
        if bpy.data.node_groups.get('Vector-Element-Power') is None:
            print("createBlenderVectorElementPowerNodeGroup #create")
            # create a group
            group, node_input, node_output = cls.__create_group('Vector-Element-Power', -580, 0, 400, 0, False)
            group.inputs.new('NodeSocketFloat', 'Exponent')
            group.inputs.new('NodeSocketVectorDirection', 'Vector')
            group.outputs.new('NodeSocketVectorDirection', 'Vector')

            # create nodes
            node_separate_xyz = group.nodes.new('ShaderNodeSeparateXYZ')
            node_separate_xyz.location = -385, -140

            node_abs_x = cls.__node_math(group.nodes, 'ABSOLUTE', -180, 180)
            node_abs_y = cls.__node_math(group.nodes, 'ABSOLUTE', -180, 0)
            node_abs_z = cls.__node_math(group.nodes, 'ABSOLUTE', -180, -180)

            node_power_x = cls.__node_math(group.nodes, 'POWER', 20, 180)
            node_power_y = cls.__node_math(group.nodes, 'POWER', 20, 0)
            node_power_z = cls.__node_math(group.nodes, 'POWER', 20, -180)

            node_combine_xyz = group.nodes.new('ShaderNodeCombineXYZ')
            node_combine_xyz.location = 215, 0

            # link nodes together
            group.links.new(node_input.outputs['Vector'], node_separate_xyz.inputs[0])
            group.links.new(node_separate_xyz.outputs['X'], node_abs_x.inputs[0])
            group.links.new(node_separate_xyz.outputs['Y'], node_abs_y.inputs[0])
            group.links.new(node_separate_xyz.outputs['Z'], node_abs_z.inputs[0])
            group.links.new(node_abs_x.outputs['Value'], node_power_x.inputs[0])
            group.links.new(node_input.outputs['Exponent'], node_power_x.inputs[1])
            group.links.new(node_abs_y.outputs['Value'], node_power_y.inputs[0])
            group.links.new(node_input.outputs['Exponent'], node_power_y.inputs[1])
            group.links.new(node_abs_z.outputs['Value'], node_power_z.inputs[0])
            group.links.new(node_input.outputs['Exponent'], node_power_z.inputs[1])
            group.links.new(node_power_x.outputs['Value'], node_combine_xyz.inputs['X'])
            group.links.new(node_power_y.outputs['Value'], node_combine_xyz.inputs['Y'])
            group.links.new(node_power_z.outputs['Value'], node_combine_xyz.inputs['Z'])
            group.links.new(node_combine_xyz.outputs['Vector'], node_output.inputs[0])

    @classmethod
    def __create_blender_convert_to_normals_node_group(cls):
        if bpy.data.node_groups.get('Convert-To-Normals') is None:
            print("createBlenderConvertToNormalsNodeGroup #create")
            # create a group
            group, node_input, node_output = cls.__create_group('Convert-To-Normals', -490, 0, 400, 0, False)
            group.inputs.new('NodeSocketFloat', 'Vector Length')
            group.inputs.new('NodeSocketFloat', 'Smoothing')
            group.inputs.new('NodeSocketFloat', 'Strength')
            group.inputs.new('NodeSocketVectorDirection', 'Normal')
            group.outputs.new('NodeSocketVectorDirection', 'Normal')

            # create nodes
            node_power = cls.__node_math(group.nodes, 'POWER', -290, 150)

            node_colorramp = group.nodes.new('ShaderNodeValToRGB')
            node_colorramp.color_ramp.color_mode = 'RGB'
            node_colorramp.color_ramp.interpolation = 'EASE'
            node_colorramp.color_ramp.elements[0].color = (1, 1, 1, 1)
            node_colorramp.color_ramp.elements[1].color = (0, 0, 0, 1)
            node_colorramp.color_ramp.elements[1].position = 0.45
            node_colorramp.location = -95, 150

            node_bump = group.nodes.new('ShaderNodeBump')
            node_bump.inputs['Distance'].default_value = 0.02
            node_bump.location = 200, 0

            # link nodes together
            group.links.new(node_input.outputs['Vector Length'], node_power.inputs[0])
            group.links.new(node_input.outputs['Smoothing'], node_power.inputs[1])
            group.links.new(node_power.outputs['Value'], node_colorramp.inputs[0])
            group.links.new(node_input.outputs['Strength'], node_bump.inputs['Strength'])
            group.links.new(node_colorramp.outputs['Color'], node_bump.inputs['Height'])
            group.links.new(node_input.outputs['Normal'], node_bump.inputs['Normal'])
            group.links.new(node_bump.outputs['Normal'], node_output.inputs[0])

    @classmethod
    def __create_blender_concave_walls_node_group(cls):
        if bpy.data.node_groups.get('Concave Walls') is None:
            print("createBlenderConcaveWallsNodeGroup #create")
            # create a group
            group, node_input, node_output = cls.__create_group('Concave Walls', -530, 0, 300, 0, False)
            group.inputs.new('NodeSocketFloat', 'Strength')
            group.inputs.new('NodeSocketVectorDirection', 'Normal')
            group.outputs.new('NodeSocketVectorDirection', 'Normal')

            # create nodes
            node_distance_to_center = group.nodes.new('ShaderNodeGroup')
            node_distance_to_center.node_tree = bpy.data.node_groups['Distance-To-Center']
            node_distance_to_center.location = (-340, 105)

            node_vector_elements_power = group.nodes.new('ShaderNodeGroup')
            node_vector_elements_power.node_tree = bpy.data.node_groups['Vector-Element-Power']
            node_vector_elements_power.location = (-120, 105)
            node_vector_elements_power.inputs['Exponent'].default_value = 4.0

            node_convert_to_normals = group.nodes.new('ShaderNodeGroup')
            node_convert_to_normals.node_tree = bpy.data.node_groups['Convert-To-Normals']
            node_convert_to_normals.location = (90, 0)
            node_convert_to_normals.inputs['Strength'].default_value = 0.2
            node_convert_to_normals.inputs['Smoothing'].default_value = 0.3

            # link nodes together
            group.links.new(node_distance_to_center.outputs['Vector'], node_vector_elements_power.inputs['Vector'])
            group.links.new(node_vector_elements_power.outputs['Vector'], node_convert_to_normals.inputs['Vector Length'])
            group.links.new(node_input.outputs['Strength'], node_convert_to_normals.inputs['Strength'])
            group.links.new(node_input.outputs['Normal'], node_convert_to_normals.inputs['Normal'])
            group.links.new(node_convert_to_normals.outputs['Normal'], node_output.inputs['Normal'])

    @classmethod
    def __create_blender_slope_texture_node_group(cls):
        if bpy.data.node_groups.get('Slope Texture') is None:
            print("createBlenderSlopeTextureNodeGroup #create")
            # create a group
            group, node_input, node_output = cls.__create_group('Slope Texture', -530, 0, 300, 0, False)
            group.inputs.new('NodeSocketFloat', 'Strength')
            group.inputs.new('NodeSocketVectorDirection', 'Normal')
            group.outputs.new('NodeSocketVectorDirection', 'Normal')

            # create nodes
            node_texture_coordinate = cls.__node_tex_coord(group.nodes, -300, 240)
            node_voronoi = cls.__node_voronoi(group.nodes, 6.2, -100, 155)
            node_bump = cls.__node_bump_shader(group.nodes, 0.3, 1.0, 90, 50)
            node_bump.invert = True

            # link nodes together
            group.links.new(node_texture_coordinate.outputs['Object'], node_voronoi.inputs['Vector'])
            group.links.new(node_voronoi.outputs['Distance'], node_bump.inputs['Height'])
            group.links.new(node_input.outputs['Strength'], node_bump.inputs['Strength'])
            group.links.new(node_input.outputs['Normal'], node_bump.inputs['Normal'])
            group.links.new(node_bump.outputs['Normal'], node_output.inputs['Normal'])

    @classmethod
    def __create_blender_fresnel_node_group(cls):
        if bpy.data.node_groups.get('PBR-Fresnel-Roughness') is None:
            print("createBlenderFresnelNodeGroup #create")
            # create a group
            group, node_input, node_output = cls.__create_group('PBR-Fresnel-Roughness', -530, 0, 300, 0, False)
            group.inputs.new('NodeSocketFloatFactor', 'Roughness')
            group.inputs.new('NodeSocketFloat', 'IOR')
            group.inputs.new('NodeSocketVectorDirection', 'Normal')
            group.outputs.new('NodeSocketFloatFactor', 'Fresnel Factor')

            # create nodes
            node_fres = group.nodes.new('ShaderNodeFresnel')
            node_fres.location = (110, 0)

            node_mix = group.nodes.new('ShaderNodeMixRGB')
            node_mix.location = (-80, -75)

            node_bump = group.nodes.new('ShaderNodeBump')
            node_bump.location = (-320, -172)
            # node_bump.hide = True

            node_geom = group.nodes.new('ShaderNodeNewGeometry')
            node_geom.location = (-320, -360)
            # node_geom.hide = True

            # link nodes together
            group.links.new(node_input.outputs['Roughness'], node_mix.inputs['Fac'])  # Input Roughness -> Mix Fac
            group.links.new(node_input.outputs['IOR'], node_fres.inputs['IOR'])  # Input IOR -> Fres IOR
            group.links.new(node_input.outputs['Normal'], node_bump.inputs['Normal'])  # Input Normal -> Bump Normal
            group.links.new(node_bump.outputs['Normal'], node_mix.inputs['Color1'])  # Bump Normal -> Mix Color1
            group.links.new(node_geom.outputs['Incoming'], node_mix.inputs['Color2'])  # Geom Incoming -> Mix color2
            group.links.new(node_mix.outputs['Color'], node_fres.inputs['Normal'])  # Mix Color -> Fres Normal
            group.links.new(node_fres.outputs['Fac'], node_output.inputs['Fresnel Factor'])  # Fres Fac -> Group Output Fresnel Factor

    @classmethod
    def __create_blender_reflection_node_group(cls):
        if bpy.data.node_groups.get('PBR-Reflection') is None:
            print("createBlenderReflectionNodeGroup #create")
            # create a group
            group, node_input, node_output = cls.__create_group('PBR-Reflection', -530, 0, 300, 0, True)
            group.inputs.new('NodeSocketShader', 'Shader')
            group.inputs.new('NodeSocketFloatFactor', 'Roughness')
            group.inputs.new('NodeSocketFloatFactor', 'Reflection')
            group.inputs.new('NodeSocketFloat', 'IOR')
            group.inputs.new('NodeSocketVectorDirection', 'Normal')

            node_fresnel_roughness = group.nodes.new('ShaderNodeGroup')
            node_fresnel_roughness.node_tree = bpy.data.node_groups['PBR-Fresnel-Roughness']
            node_fresnel_roughness.location = (-290, 145)

            node_mixrgb = group.nodes.new('ShaderNodeMixRGB')
            node_mixrgb.location = (-80, 115)
            node_mixrgb.inputs['Color2'].default_value = (0.0, 0.0, 0.0, 1.0)

            node_mix_shader = group.nodes.new('ShaderNodeMixShader')
            node_mix_shader.location = (100, 0)

            node_glossy = group.nodes.new('ShaderNodeBsdfGlossy')
            node_glossy.inputs['Color'].default_value = (1.0, 1.0, 1.0, 1.0)
            node_glossy.location = (-290, -95)

            # link nodes together
            group.links.new(node_input.outputs['Shader'], node_mix_shader.inputs[1])
            group.links.new(node_input.outputs['Roughness'], node_fresnel_roughness.inputs['Roughness'])
            group.links.new(node_input.outputs['Roughness'], node_glossy.inputs['Roughness'])
            group.links.new(node_input.outputs['Reflection'], node_mixrgb.inputs['Color1'])
            group.links.new(node_input.outputs['IOR'], node_fresnel_roughness.inputs['IOR'])
            group.links.new(node_input.outputs['Normal'], node_fresnel_roughness.inputs['Normal'])
            group.links.new(node_input.outputs['Normal'], node_glossy.inputs['Normal'])
            group.links.new(node_fresnel_roughness.outputs[0], node_mixrgb.inputs[0])
            group.links.new(node_mixrgb.outputs[0], node_mix_shader.inputs[0])
            group.links.new(node_glossy.outputs[0], node_mix_shader.inputs[2])
            group.links.new(node_mix_shader.outputs[0], node_output.inputs['Shader'])

    @classmethod
    def __create_blender_dielectric_node_group(cls):
        if bpy.data.node_groups.get('PBR-Dielectric') is None:
            print("createBlenderDielectricNodeGroup #create")
            # create a group
            group, node_input, node_output = cls.__create_group('PBR-Dielectric', -530, 70, 500, 0, True)
            group.inputs.new('NodeSocketColor', 'Color')
            group.inputs.new('NodeSocketFloatFactor', 'Roughness')
            group.inputs.new('NodeSocketFloatFactor', 'Reflection')
            group.inputs.new('NodeSocketFloatFactor', 'Transparency')
            group.inputs.new('NodeSocketFloat', 'IOR')
            group.inputs.new('NodeSocketVectorDirection', 'Normal')
            group.inputs['IOR'].default_value = 1.46
            group.inputs['IOR'].min_value = 0.0
            group.inputs['IOR'].max_value = 100.0
            group.inputs['Roughness'].default_value = 0.2
            group.inputs['Roughness'].min_value = 0.0
            group.inputs['Roughness'].max_value = 1.0
            group.inputs['Reflection'].default_value = 0.1
            group.inputs['Reflection'].min_value = 0.0
            group.inputs['Reflection'].max_value = 1.0
            group.inputs['Transparency'].default_value = 0.0
            group.inputs['Transparency'].min_value = 0.0
            group.inputs['Transparency'].max_value = 1.0

            node_diffuse = group.nodes.new('ShaderNodeBsdfDiffuse')
            node_diffuse.location = (-110, 145)

            node_reflection = group.nodes.new('ShaderNodeGroup')
            node_reflection.node_tree = bpy.data.node_groups['PBR-Reflection']
            node_reflection.location = (100, 115)

            node_power = cls.__node_math(group.nodes, 'POWER', -330, -105)
            node_power.inputs[1].default_value = 2.0

            node_glass = group.nodes.new('ShaderNodeBsdfGlass')
            node_glass.location = (100, -105)

            node_mix_shader = group.nodes.new('ShaderNodeMixShader')
            node_mix_shader.location = (300, 5)

            # link nodes together
            group.links.new(node_input.outputs['Color'], node_diffuse.inputs['Color'])
            group.links.new(node_input.outputs['Roughness'], node_power.inputs[0])
            group.links.new(node_input.outputs['Reflection'], node_reflection.inputs['Reflection'])
            group.links.new(node_input.outputs['IOR'], node_reflection.inputs['IOR'])
            group.links.new(node_input.outputs['Normal'], node_diffuse.inputs['Normal'])
            group.links.new(node_input.outputs['Normal'], node_reflection.inputs['Normal'])
            group.links.new(node_power.outputs[0], node_diffuse.inputs['Roughness'])
            group.links.new(node_power.outputs[0], node_reflection.inputs['Roughness'])
            group.links.new(node_diffuse.outputs[0], node_reflection.inputs['Shader'])
            group.links.new(node_reflection.outputs['Shader'], node_mix_shader.inputs['Shader'])
            group.links.new(node_input.outputs['Color'], node_glass.inputs['Color'])
            group.links.new(node_input.outputs['IOR'], node_glass.inputs['IOR'])
            group.links.new(node_input.outputs['Normal'], node_glass.inputs['Normal'])
            group.links.new(node_power.outputs[0], node_glass.inputs['Roughness'])
            group.links.new(node_input.outputs['Transparency'], node_mix_shader.inputs[0])
            group.links.new(node_glass.outputs[0], node_mix_shader.inputs[2])
            group.links.new(node_mix_shader.outputs['Shader'], node_output.inputs['Shader'])

    @classmethod
    def __create_blender_lego_standard_node_group(cls):
        group_name = 'Lego Standard'
        if bpy.data.node_groups.get(group_name) is None:
            print("createBlenderLegoStandardNodeGroup #create")
            # create a group
            group, node_input, node_output = cls.__create_group(group_name, -250, 0, 250, 0, True)
            group.inputs.new('NodeSocketColor', 'Color')
            group.inputs.new('NodeSocketVectorDirection', 'Normal')

            node_main = cls.__node_principled(group.nodes, 0.05, 0.05, 0.0, 0.1, 0.0, 0.0, 1.45, 0.0, 0, 0)
            output_name = 'BSDF'
            color_name = 'Base Color'
            if cls.add_subsurface:
                group.links.new(node_input.outputs['Color'], node_main.inputs['Subsurface Color'])

            # link nodes together
            group.links.new(node_input.outputs['Color'], node_main.inputs[color_name])
            group.links.new(node_input.outputs['Normal'], node_main.inputs['Normal'])
            group.links.new(node_main.outputs[output_name], node_output.inputs['Shader'])

    @classmethod
    def __create_blender_lego_transparent_node_group(cls):
        group_name = 'Lego Transparent'
        if bpy.data.node_groups.get(group_name) is None:
            print("createBlenderLegoTransparentNodeGroup #create")
            # create a group
            group, node_input, node_output = cls.__create_group(group_name, -250, 0, 250, 0, True)
            group.inputs.new('NodeSocketColor', 'Color')
            group.inputs.new('NodeSocketVectorDirection', 'Normal')

            node_principled = cls.__node_principled(group.nodes, 0.0, 0.0, 0.0, 0.05, 0.0, 0.0, 1.585, 1.0, 45, 340)

            # link nodes together
            group.links.new(node_input.outputs['Color'], node_principled.inputs['Base Color'])
            group.links.new(node_input.outputs['Normal'], node_principled.inputs['Normal'])
            group.links.new(node_principled.outputs['BSDF'], node_output.inputs['Shader'])

    @classmethod
    # https://blenderartists.org/t/realistic-glass-in-eevee/1149937/19
    def __create_blender_lego_glass_node_group(cls):
        group_name = 'Lego Glass'
        if bpy.data.node_groups.get(group_name) is None:
            print("createBlenderLegoGlassNodeGroup #create")

            group = bpy.data.node_groups.new(group_name, 'ShaderNodeTree')

            i1 = group.nodes.new("NodeGroupInput")
            i1.location = (-465.2269, 27.7136)
            # i1.label = "i1"

            if "Color" not in group.inputs:
                group.inputs.new('NodeSocketColor', "Color")
            is1 = group.inputs["Color"]

            if "Normal" not in group.inputs:
                group.inputs.new('NodeSocketVectorDirection', "Normal")
            is2 = group.inputs["Normal"]

            s1 = group.nodes.new("ShaderNodeBsdfGlass")
            s1.location = (-94.0096, -123.3116)
            s1.inputs[1].default_value = 0.0
            s1.inputs[2].default_value = 1.45
            # s1.label = "s1"

            s2 = group.nodes.new("ShaderNodeBsdfGlossy")
            s2.location = (295.1122, -79.7802)
            s2.inputs[1].default_value = 0.5
            # s2.label = "s2"

            s3 = group.nodes.new("ShaderNodeFresnel")
            s3.location = (-487.2804, 202.5795)
            s3.inputs[0].default_value = 1.4
            # s3.label = "s3"

            s8 = group.nodes.new("ShaderNodeBsdfGlossy")
            s8.location = (-94.9641, -396.0273)
            s8.inputs[1].default_value = 0.5
            # s8.label = "s8"

            s4 = group.nodes.new("ShaderNodeRGBCurve")
            s4.location = (-137.4662, 390.0757)
            s4.inputs[0].default_value = 0.5
            # s4.label = "s4"
            c = 3
            r = 0
            g = 1
            b = 2
            c = s4.mapping.curves[c]
            c.points.new(0.0000, 0.0000)
            c.points.new(0.6227, 0.2438)
            c.points.new(1.0000, 1.0000)

            s5 = group.nodes.new("ShaderNodeMixShader")
            s5.location = (293.4988, 100.1442)
            s5.inputs[0].default_value = 0.25
            # s5.label = "s5"

            s6 = group.nodes.new("ShaderNodeFresnel")
            s6.location = (289.9015, 280.8444)
            s6.inputs[0].default_value = 1.4
            # s6.label = "s6"

            s7 = group.nodes.new("ShaderNodeMixShader")
            s7.location = (583.3330, 104.1106)
            s7.inputs[0].default_value = 0.5
            # s7.label = "s7"

            o1 = group.nodes.new("NodeGroupOutput")
            o1.location = (783.3330, 0.0000)
            # o1.label = "o1"

            if "Shader" not in group.outputs:
                group.outputs.new('NodeSocketShader', "Shader")
            os1 = group.outputs["Shader"]

            group.links.new(i1.outputs[0], s1.inputs[0])
            group.links.new(i1.outputs[1], s1.inputs[3])
            group.links.new(i1.outputs[0], s2.inputs[0])
            group.links.new(s1.outputs[0], s5.inputs[1])
            group.links.new(s8.outputs[0], s5.inputs[2])
            group.links.new(s2.outputs[0], s7.inputs[2])
            group.links.new(s5.outputs[0], s7.inputs[1])
            group.links.new(s7.outputs[0], o1.inputs[0])
            group.links.new(s3.outputs[0], s4.inputs[1])
            group.links.new(s4.outputs[0], s5.inputs[0])
            group.links.new(s6.outputs[0], s7.inputs[0])

    @classmethod
    def __create_blender_lego_transparent_fluorescent_node_group(cls):
        group_name = 'Lego Transparent Fluorescent'
        if bpy.data.node_groups.get(group_name) is None:
            print("createBlenderLegoTransparentFluorescentNodeGroup #create")
            # create a group
            group, node_input, node_output = cls.__create_group(group_name, -250, 0, 250, 0, True)
            group.inputs.new('NodeSocketColor', 'Color')
            group.inputs.new('NodeSocketVectorDirection', 'Normal')

            node_principled = cls.__node_principled(group.nodes, 0.0, 0.0, 0.0, 0.05, 0.0, 0.0, 1.585, 1.0, 45, 340)
            node_emission = cls.__node_emission(group.nodes, 45, -160)
            node_mix = cls.__node_mix(group.nodes, 0.03, 300, 290)

            node_output.location = 500, 290

            # link nodes together
            group.links.new(node_input.outputs['Color'], node_principled.inputs['Base Color'])
            group.links.new(node_input.outputs['Color'], node_emission.inputs['Color'])
            group.links.new(node_input.outputs['Normal'], node_principled.inputs['Normal'])
            group.links.new(node_principled.outputs['BSDF'], node_mix.inputs[1])
            group.links.new(node_emission.outputs['Emission'], node_mix.inputs[2])
            group.links.new(node_mix.outputs[0], node_output.inputs['Shader'])

    @classmethod
    def __create_blender_lego_rubber_node_group(cls):
        group_name = 'Lego Rubber Solid'
        if bpy.data.node_groups.get(group_name) is None:
            print("createBlenderLegoRubberNodeGroup #create")
            # create a group
            group, node_input, node_output = cls.__create_group(group_name, 45 - 950, 340 - 50, 45 + 200,
                                                                340 - 5, True)
            group.inputs.new('NodeSocketColor', 'Color')
            group.inputs.new('NodeSocketVectorDirection', 'Normal')

            node_noise = cls.__node_noise_texture(group.nodes, 250, 2, 0.0, 45 - 770, 340 - 200)
            node_bump1 = cls.__node_bump_shader(group.nodes, 1.0, 0.3, 45 - 366, 340 - 200)
            node_bump2 = cls.__node_bump_shader(group.nodes, 1.0, 0.1, 45 - 184, 340 - 115)
            node_subtract = cls.__node_math(group.nodes, 'SUBTRACT', 45 - 570, 340 - 216)
            node_principled = cls.__node_principled(group.nodes, 0.0, 0.0, 0.0, 0.4, 0.03, 0.0, 1.45, 0.0, 45, 340)

            node_subtract.inputs[1].default_value = 0.4

            group.links.new(node_input.outputs['Color'], node_principled.inputs['Base Color'])
            group.links.new(node_principled.outputs['BSDF'], node_output.inputs[0])
            group.links.new(node_noise.outputs['Color'], node_subtract.inputs[0])
            group.links.new(node_subtract.outputs[0], node_bump1.inputs['Height'])
            group.links.new(node_bump1.outputs['Normal'], node_bump2.inputs['Normal'])
            group.links.new(node_bump2.outputs['Normal'], node_principled.inputs['Normal'])

    @classmethod
    def __create_blender_lego_rubber_translucent_node_group(cls):
        group_name = 'Lego Rubber Translucent'
        if bpy.data.node_groups.get(group_name) is None:
            print("createBlenderLegoRubberTranslucentNodeGroup #create")
            # create a group
            group, node_input, node_output = cls.__create_group(group_name, -250, 0, 250, 0, True)
            group.inputs.new('NodeSocketColor', 'Color')
            group.inputs.new('NodeSocketVectorDirection', 'Normal')

            node_noise = cls.__node_noise_texture(group.nodes, 250, 2, 0.0, 45 - 770, 340 - 200)
            node_bump1 = cls.__node_bump_shader(group.nodes, 1.0, 0.3, 45 - 366, 340 - 200)
            node_bump2 = cls.__node_bump_shader(group.nodes, 1.0, 0.1, 45 - 184, 340 - 115)
            node_subtract = cls.__node_math(group.nodes, 'SUBTRACT', 45 - 570, 340 - 216)
            node_principled = cls.__node_principled(group.nodes, 0.0, 0.0, 0.0, 0.4, 0.03, 0.0, 1.45, 0.0, 45, 340)
            node_mix = cls.__node_mix(group.nodes, 0.8, 300, 290)
            node_refraction = cls.__node_refraction(group.nodes, 0.0, 1.45, 290 - 242, 154 - 330)
            node_input.location = -320, 290
            node_output.location = 530, 285

            node_subtract.inputs[1].default_value = 0.4

            group.links.new(node_input.outputs['Normal'], node_refraction.inputs['Normal'])
            group.links.new(node_refraction.outputs[0], node_mix.inputs[2])
            group.links.new(node_principled.outputs[0], node_mix.inputs[1])
            group.links.new(node_mix.outputs[0], node_output.inputs[0])
            group.links.new(node_input.outputs['Color'], node_principled.inputs['Base Color'])
            group.links.new(node_noise.outputs['Color'], node_subtract.inputs[0])
            group.links.new(node_subtract.outputs[0], node_bump1.inputs['Height'])
            group.links.new(node_bump1.outputs['Normal'], node_bump2.inputs['Normal'])
            group.links.new(node_bump2.outputs['Normal'], node_principled.inputs['Normal'])
            group.links.new(node_mix.outputs[0], node_output.inputs[0])

    @classmethod
    def __create_blender_lego_emission_node_group(cls):
        group_name = 'Lego Emission'
        if bpy.data.node_groups.get(group_name) is None:
            print("createBlenderLegoEmissionNodeGroup #create")

            # create a group
            group, node_input, node_output = cls.__create_group(group_name, -450, 90, 250, 0, True)
            group.inputs.new('NodeSocketColor', 'Color')
            group.inputs.new('NodeSocketFloatFactor', 'Luminance')
            group.inputs.new('NodeSocketVectorDirection', 'Normal')

            node_emit = cls.__node_emission(group.nodes, -242, -123)
            node_mix = cls.__node_mix(group.nodes, 0.5, 0, 90)

            node_main = cls.__node_principled(group.nodes, 1.0, 0.05, 0.0, 0.5, 0.0, 0.03, 1.45, 0.0, -242, 154 + 240)
            if cls.add_subsurface:
                group.links.new(node_input.outputs['Color'], node_main.inputs['Subsurface Color'])
            group.links.new(node_input.outputs['Color'], node_emit.inputs['Color'])
            main_color = 'Base Color'

            # link nodes together
            group.links.new(node_input.outputs['Color'], node_main.inputs[main_color])
            group.links.new(node_input.outputs['Normal'], node_main.inputs['Normal'])
            group.links.new(node_input.outputs['Luminance'], node_mix.inputs[0])
            group.links.new(node_main.outputs[0], node_mix.inputs[1])
            group.links.new(node_emit.outputs[0], node_mix.inputs[2])
            group.links.new(node_mix.outputs[0], node_output.inputs[0])

    @classmethod
    def __create_blender_lego_chrome_node_group(cls):
        group_name = 'Lego Chrome'
        if bpy.data.node_groups.get(group_name) is None:
            print("createBlenderLegoChromeNodeGroup #create")

            # create a group
            group, node_input, node_output = cls.__create_group(group_name, -450, 90, 250, 0, True)
            group.inputs.new('NodeSocketColor', 'Color')
            group.inputs.new('NodeSocketVectorDirection', 'Normal')

            node_hsv = cls.__node_hsv(group.nodes, 0.5, 0.9, 2.0, -90, 0)
            node_principled = cls.__node_principled(group.nodes, 0.0, 0.0, 1.0, 0.0, 1.0, 0.0, 2.4, 0.0, 100, 0)

            node_output.location = (575, -140)

            # link nodes together
            group.links.new(node_input.outputs['Color'], node_hsv.inputs['Color'])
            group.links.new(node_input.outputs['Normal'], node_principled.inputs['Normal'])
            group.links.new(node_hsv.outputs['Color'], node_principled.inputs['Base Color'])
            group.links.new(node_principled.outputs['BSDF'], node_output.inputs[0])

    @classmethod
    def __create_blender_lego_pearlescent_node_group(cls):
        group_name = 'Lego Pearlescent'
        if bpy.data.node_groups.get(group_name) is None:
            print("createBlenderLegoPearlescentNodeGroup #create")

            # create a group
            group, node_input, node_output = cls.__create_group(group_name, -450, 90, 630, 95, True)
            group.inputs.new('NodeSocketColor', 'Color')
            group.inputs.new('NodeSocketVectorDirection', 'Normal')

            node_principled = cls.__node_principled(group.nodes, 1.0, 0.25, 0.5, 0.2, 1.0, 0.2, 1.6,
                                                    0.0, 310, 95)
            node_sep_hsv = cls.__node_separate_hsv(group.nodes, -240, 75)
            node_multiply = cls.__node_math(group.nodes, 'MULTIPLY', -60, 0)
            node_com_hsv = cls.__node_combine_hsv(group.nodes, 110, 95)
            node_tex_coord = cls.__node_tex_coord(group.nodes, -730, -223)
            node_tex_wave = cls.__node_tex_wave(group.nodes, 'BANDS', 'SIN', 0.5, 40, 1, 1.5, -520, -190)
            node_color_ramp = cls.__node_color_ramp(group.nodes, 0.329, (0.89, 0.89, 0.89, 1), 0.820, (1, 1, 1, 1), -340, -70)
            element = node_color_ramp.color_ramp.elements.new(1.0)
            element.color = (1.118, 1.118, 1.118, 1)

            # link nodes together
            group.links.new(node_input.outputs['Color'], node_sep_hsv.inputs['Color'])
            group.links.new(node_input.outputs['Normal'], node_principled.inputs['Normal'])
            group.links.new(node_sep_hsv.outputs['H'], node_com_hsv.inputs['H'])
            group.links.new(node_sep_hsv.outputs['S'], node_com_hsv.inputs['S'])
            group.links.new(node_sep_hsv.outputs['V'], node_multiply.inputs[0])
            group.links.new(node_com_hsv.outputs['Color'], node_principled.inputs['Base Color'])
            if cls.add_subsurface:
                group.links.new(node_com_hsv.outputs['Color'], node_principled.inputs['Subsurface Color'])
            group.links.new(node_tex_coord.outputs['Object'], node_tex_wave.inputs['Vector'])
            group.links.new(node_tex_wave.outputs['Fac'], node_color_ramp.inputs['Fac'])
            group.links.new(node_color_ramp.outputs['Color'], node_multiply.inputs[1])
            group.links.new(node_multiply.outputs[0], node_com_hsv.inputs['V'])
            group.links.new(node_principled.outputs['BSDF'], node_output.inputs[0])

    @classmethod
    def __create_blender_lego_metal_node_group(cls):
        group_name = 'Lego Metal'
        if bpy.data.node_groups.get(group_name) is None:
            print("createBlenderLegoMetalNodeGroup #create")

            # create a group
            group, node_input, node_output = cls.__create_group(group_name, -450, 90, 250, 0, True)
            group.inputs.new('NodeSocketColor', 'Color')
            group.inputs.new('NodeSocketVectorDirection', 'Normal')

            node_principled = cls.__node_principled(group.nodes, 0.0, 0.0, 0.8, 0.2, 0.0, 0.03, 1.45, 0.0, 310, 95)

            group.links.new(node_input.outputs['Color'], node_principled.inputs['Base Color'])
            group.links.new(node_input.outputs['Normal'], node_principled.inputs['Normal'])
            group.links.new(node_principled.outputs[0], node_output.inputs['Shader'])

    @classmethod
    def __create_blender_lego_glitter_node_group(cls):
        group_name = 'Lego Glitter'
        if bpy.data.node_groups.get(group_name) is None:
            print("createBlenderLegoGlitterNodeGroup #create")

            # create a group
            group, node_input, node_output = cls.__create_group(group_name, -450, 0, 410, 0, True)
            group.inputs.new('NodeSocketColor', 'Color')
            group.inputs.new('NodeSocketColor', 'Glitter Color')
            group.inputs.new('NodeSocketVectorDirection', 'Normal')

            node_voronoi = cls.__node_voronoi(group.nodes, 100, -222, 310)
            node_gamma = cls.__node_gamma(group.nodes, 50, 0, 200)
            node_mix = cls.__node_mix(group.nodes, 0.05, 210, 90 + 25)
            node_principled1 = cls.__node_principled(group.nodes, 0.0, 0.0, 0.0, 0.2, 0.0, 0.03, 1.585, 1.0, 45 - 270, 340 - 210)
            node_principled2 = cls.__node_principled(group.nodes, 0.0, 0.0, 0.0, 0.5, 0.0, 0.03, 1.45, 0.0, 45 - 270, 340 - 750)

            group.links.new(node_input.outputs['Color'], node_principled1.inputs['Base Color'])
            group.links.new(node_input.outputs['Glitter Color'], node_principled2.inputs['Base Color'])
            group.links.new(node_input.outputs['Normal'], node_principled1.inputs['Normal'])
            group.links.new(node_input.outputs['Normal'], node_principled2.inputs['Normal'])
            group.links.new(node_voronoi.outputs['Color'], node_gamma.inputs['Color'])
            group.links.new(node_gamma.outputs[0], node_mix.inputs[0])
            group.links.new(node_principled1.outputs['BSDF'], node_mix.inputs[1])
            group.links.new(node_principled2.outputs['BSDF'], node_mix.inputs[2])
            group.links.new(node_mix.outputs[0], node_output.inputs[0])

    @classmethod
    def __create_blender_lego_speckle_node_group(cls):
        group_name = 'Lego Speckle'
        if bpy.data.node_groups.get(group_name) is None:
            print("createBlenderLegoSpeckleNodeGroup #create")

            # create a group
            group, node_input, node_output = cls.__create_group(group_name, -450, 0, 410, 0, True)
            group.inputs.new('NodeSocketColor', 'Color')
            group.inputs.new('NodeSocketColor', 'Speckle Color')
            group.inputs.new('NodeSocketVectorDirection', 'Normal')

            node_voronoi = cls.__node_voronoi(group.nodes, 50, -222, 310)
            node_gamma = cls.__node_gamma(group.nodes, 3.5, 0, 200)
            node_mix = cls.__node_mix(group.nodes, 0.05, 210, 90 + 25)
            node_principled1 = cls.__node_principled(group.nodes, 0.0, 0.0, 0.0, 0.1, 0.0, 0.03, 1.45, 0.0, 45 - 270, 340 - 210)
            node_principled2 = cls.__node_principled(group.nodes, 0.0, 0.0, 1.0, 0.5, 0.0, 0.03, 1.45, 0.0, 45 - 270, 340 - 750)

            group.links.new(node_input.outputs['Color'], node_principled1.inputs['Base Color'])
            group.links.new(node_input.outputs['Speckle Color'], node_principled2.inputs['Base Color'])
            group.links.new(node_input.outputs['Normal'], node_principled1.inputs['Normal'])
            group.links.new(node_input.outputs['Normal'], node_principled2.inputs['Normal'])
            group.links.new(node_voronoi.outputs['Color'], node_gamma.inputs['Color'])
            group.links.new(node_gamma.outputs[0], node_mix.inputs[0])
            group.links.new(node_principled1.outputs['BSDF'], node_mix.inputs[1])
            group.links.new(node_principled2.outputs['BSDF'], node_mix.inputs[2])
            group.links.new(node_mix.outputs[0], node_output.inputs[0])

    @classmethod
    def __create_blender_lego_milky_white_node_group(cls):
        group_name = 'Lego Milky White'
        if bpy.data.node_groups.get(group_name) is None:
            print("createBlenderLegoMilkyWhiteNodeGroup #create")

            # create a group
            group, node_input, node_output = cls.__create_group(group_name, -450, 0, 350, 0, True)
            group.inputs.new('NodeSocketColor', 'Color')
            group.inputs.new('NodeSocketVectorDirection', 'Normal')

            node_principled = cls.__node_principled(group.nodes, 1.0, 0.05, 0.0, 0.5, 0.0, 0.03, 1.45, 0.0, 45 - 270, 340 - 210)
            node_translucent = cls.__node_translucent(group.nodes, -225, -382)
            node_mix = cls.__node_mix(group.nodes, 0.5, 65, -40)

            group.links.new(node_input.outputs['Color'], node_principled.inputs['Base Color'])
            if cls.add_subsurface:
                group.links.new(node_input.outputs['Color'], node_principled.inputs['Subsurface Color'])
            group.links.new(node_input.outputs['Normal'], node_principled.inputs['Normal'])
            group.links.new(node_input.outputs['Normal'], node_translucent.inputs['Normal'])
            group.links.new(node_principled.outputs[0], node_mix.inputs[1])
            group.links.new(node_translucent.outputs[0], node_mix.inputs[2])
            group.links.new(node_mix.outputs[0], node_output.inputs[0])
