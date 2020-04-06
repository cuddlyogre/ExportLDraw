import bpy
import mathutils

from . import options
from . import ldraw_colors


def create_blender_node_groups():
    __create_blender_slope_texture_node_group()

    __create_blender_lego_standard_node_group()
    __create_blender_lego_transparent_node_group()
    __create_blender_lego_glass_node_group()
    __create_blender_lego_transparent_fluorescent_node_group()
    __create_blender_lego_rubber_node_group()
    __create_blender_lego_rubber_translucent_node_group()
    __create_blender_lego_emission_node_group()
    __create_blender_lego_chrome_node_group()
    __create_blender_lego_pearlescent_node_group()
    __create_blender_lego_metal_node_group()
    __create_blender_lego_glitter_node_group()
    __create_blender_lego_speckle_node_group()
    __create_blender_lego_milky_white_node_group()


def get_material(color_code, use_edge_color=False, is_slope_material=False):
    key = []
    key.append(color_code)
    if options.use_alt_colors:
        key.append("alt")
    if is_slope_material:
        key.append("s")
    if options.add_subsurface:
        key.append("ss")
    if use_edge_color:
        key.append("edge")
    key = "_".join([k.lower() for k in key])

    if key in bpy.data.materials:
        return bpy.data.materials[key]

    material = __create_node_based_material(key, color_code, use_edge_color=use_edge_color, is_slope_material=is_slope_material)
    return material


def __create_node_based_material(key, color_code, use_edge_color=False, is_slope_material=False):
    """Set Cycles Material Values."""

    color = ldraw_colors.get_color(color_code)

    # Reuse current material if it exists, otherwise create a new material
    if bpy.data.materials.get(key) is None:
        bpy.data.materials.new(key)
    material = bpy.data.materials[key]

    # Use nodes
    material.use_nodes = True

    nodes = material.node_tree.nodes
    links = material.node_tree.links

    # Remove any existing nodes
    for n in nodes:
        nodes.remove(n)

    is_transparent = False

    if color is None:
        diffuse_color = (1.0, 1.0, 0.0) + (1.0,)
        material.diffuse_color = diffuse_color
        material["LEGO.isTransparent"] = is_transparent
        material[options.ldraw_color_code_key] = ""
        __create_cycles_basic(nodes, links, diffuse_color, 1.0, "")
        return material

    if use_edge_color:
        diffuse_color = color.edge_color + (1.0,)
        material.diffuse_color = diffuse_color
        material["LEGO.isTransparent"] = is_transparent
        material[options.ldraw_color_code_key] = ""
        __create_cycles_basic(nodes, links, diffuse_color, 1.0, "")
        return material

    is_transparent = color.alpha < 1.0

    diffuse_color = color.color + (1.0,)
    material.diffuse_color = diffuse_color
    material["LEGO.isTransparent"] = is_transparent
    material[options.ldraw_color_code_key] = color.code

    if is_transparent:
        material.blend_method = 'BLEND'
        material.refraction_depth = 0.1
        material.use_screen_refraction = True

    if color.name == "Milky_White":
        __create_cycles_milky_white(nodes, links, diffuse_color)
    elif color.luminance > 0:
        __create_cycles_emission(nodes, links, diffuse_color, color.alpha, color.luminance)
    elif color.material == "CHROME":
        __create_cycles_chrome(nodes, links, diffuse_color)
    elif color.material == "PEARLESCENT":
        __create_cycles_pearlescent(nodes, links, diffuse_color)
    elif color.material == "METAL":
        __create_cycles_metal(nodes, links, diffuse_color)
    elif color.material == "GLITTER":
        __create_cycles_glitter(nodes, links, diffuse_color, color.secondary_color)
    elif color.material == "SPECKLE":
        __create_cycles_speckle(nodes, links, diffuse_color, color.secondary_color)
    elif color.material == "RUBBER":
        __create_cycles_rubber(nodes, links, diffuse_color, color.alpha)
    else:
        __create_cycles_basic(nodes, links, diffuse_color, color.alpha, color.name)

    if is_slope_material:
        # TODO: slight variation in strength for each material
        __create_cycles_slope_texture(nodes, links)

    # https://blender.stackexchange.com/questions/157531/blender-2-8-python-add-texture-image
    texmap_material = True
    if texmap_material:
        pass

    glossmap_material = True
    if glossmap_material:
        pass

    return material


def __node_slope_texture(nodes, strength, x, y):
    node = nodes.new('ShaderNodeGroup')
    node.node_tree = bpy.data.node_groups['Slope Texture']
    node.location = x, y
    node.inputs['Strength'].default_value = strength
    return node


def __node_lego_standard(nodes, color, x, y):
    node = nodes.new('ShaderNodeGroup')
    node.node_tree = bpy.data.node_groups['LEGO Standard']
    node.location = x, y
    node.inputs['Color'].default_value = color
    return node


def __node_lego_transparent_fluorescent(nodes, color, x, y):
    node = nodes.new('ShaderNodeGroup')
    node.node_tree = bpy.data.node_groups['LEGO Transparent Fluorescent']
    node.location = x, y
    node.inputs['Color'].default_value = color
    return node


def __node_lego_transparent(nodes, color, x, y):
    node = nodes.new('ShaderNodeGroup')
    node.node_tree = bpy.data.node_groups['LEGO Transparent']
    node.location = x, y
    node.inputs['Color'].default_value = color
    return node


def __node_lego_glass(nodes, color, x, y):
    node = nodes.new('ShaderNodeGroup')
    node.node_tree = bpy.data.node_groups['LEGO Glass']
    node.location = x, y
    node.inputs['Color'].default_value = color
    return node


def __node_lego_rubber_solid(nodes, color, x, y):
    node = nodes.new('ShaderNodeGroup')
    node.node_tree = bpy.data.node_groups['LEGO Rubber Solid']
    node.location = x, y
    node.inputs['Color'].default_value = color
    return node


def __node_lego_rubber_translucent(nodes, color, x, y):
    node = nodes.new('ShaderNodeGroup')
    node.node_tree = bpy.data.node_groups['LEGO Rubber Translucent']
    node.location = x, y
    node.inputs['Color'].default_value = color
    return node


def __node_lego_emission(nodes, color, luminance, x, y):
    node = nodes.new('ShaderNodeGroup')
    node.node_tree = bpy.data.node_groups['LEGO Emission']
    node.location = x, y
    node.inputs['Color'].default_value = color
    node.inputs['Luminance'].default_value = luminance
    return node


def __node_lego_chrome(nodes, color, x, y):
    node = nodes.new('ShaderNodeGroup')
    node.node_tree = bpy.data.node_groups['LEGO Chrome']
    node.location = x, y
    node.inputs['Color'].default_value = color
    return node


def __node_lego_pearlescent(nodes, color, x, y):
    node = nodes.new('ShaderNodeGroup')
    node.node_tree = bpy.data.node_groups['LEGO Pearlescent']
    node.location = x, y
    node.inputs['Color'].default_value = color
    return node


def __node_lego_metal(nodes, color, x, y):
    node = nodes.new('ShaderNodeGroup')
    node.node_tree = bpy.data.node_groups['LEGO Metal']
    node.location = x, y
    node.inputs['Color'].default_value = color
    return node


def __node_lego_glitter(nodes, color, glittercolor, x, y):
    node = nodes.new('ShaderNodeGroup')
    node.node_tree = bpy.data.node_groups['LEGO Glitter']
    node.location = x, y
    node.inputs['Color'].default_value = color
    node.inputs['Glitter Color'].default_value = glittercolor
    return node


def __node_lego_speckle(nodes, color, specklecolor, x, y):
    node = nodes.new('ShaderNodeGroup')
    node.node_tree = bpy.data.node_groups['LEGO Speckle']
    node.location = x, y
    node.inputs['Color'].default_value = color
    node.inputs['Speckle Color'].default_value = specklecolor
    return node


def __node_lego_milky_white(nodes, color, x, y):
    node = nodes.new('ShaderNodeGroup')
    node.node_tree = bpy.data.node_groups['LEGO Milky White']
    node.location = x, y
    node.inputs['Color'].default_value = color
    return node


def __node_mix(nodes, factor, x, y):
    node = nodes.new('ShaderNodeMixShader')
    node.location = x, y
    node.inputs['Fac'].default_value = factor
    return node


def __node_output(nodes, x, y):
    node = nodes.new('ShaderNodeOutputMaterial')
    node.location = x, y
    return node


def __node_principled(nodes, subsurface, sub_rad, metallic, roughness, clearcoat, clearcoat_roughness, ior, transmission, x, y):
    node = nodes.new('ShaderNodeBsdfPrincipled')
    node.location = x, y
    if options.add_subsurface:
        node.inputs['Subsurface'].default_value = subsurface
        node.inputs['Subsurface Radius'].default_value = mathutils.Vector((sub_rad, sub_rad, sub_rad))
    node.inputs['Metallic'].default_value = metallic
    node.inputs['Roughness'].default_value = roughness
    node.inputs['Clearcoat'].default_value = clearcoat
    node.inputs['Clearcoat Roughness'].default_value = clearcoat_roughness
    node.inputs['IOR'].default_value = ior
    node.inputs['Transmission'].default_value = transmission
    return node


def __node_hsv(nodes, h, s, v, x, y):
    node = nodes.new('ShaderNodeHueSaturation')
    node.location = x, y
    node.inputs[0].default_value = h
    node.inputs[1].default_value = s
    node.inputs[2].default_value = v
    return node


def __node_separate_hsv(nodes, x, y):
    node = nodes.new('ShaderNodeSeparateHSV')
    node.location = x, y
    return node


def __node_combine_hsv(nodes, x, y):
    node = nodes.new('ShaderNodeCombineHSV')
    node.location = x, y
    return node


def __node_tex_coord(nodes, x, y):
    node = nodes.new('ShaderNodeTexCoord')
    node.location = x, y
    return node


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


def __node_diffuse(nodes, roughness, x, y):
    node = nodes.new('ShaderNodeBsdfDiffuse')
    node.location = x, y
    node.inputs['Color'].default_value = (1, 1, 1, 1)
    node.inputs['Roughness'].default_value = roughness
    return node


def __node_glass(nodes, roughness, ior, distribution, x, y):
    node = nodes.new('ShaderNodeBsdfGlass')
    node.location = x, y
    node.distribution = distribution
    node.inputs['Color'].default_value = (1, 1, 1, 1)
    node.inputs['Roughness'].default_value = roughness
    node.inputs['IOR'].default_value = ior
    return node


def __node_fresnel(nodes, ior, x, y):
    node = nodes.new('ShaderNodeFresnel')
    node.location = x, y
    node.inputs['IOR'].default_value = ior
    return node


def __node_glossy(nodes, color, roughness, distribution, x, y):
    node = nodes.new('ShaderNodeBsdfGlossy')
    node.location = x, y
    node.distribution = distribution
    node.inputs['Color'].default_value = color
    node.inputs['Roughness'].default_value = roughness
    return node


def __node_translucent(nodes, x, y):
    node = nodes.new('ShaderNodeBsdfTranslucent')
    node.location = x, y
    return node


def __node_transparent(nodes, x, y):
    node = nodes.new('ShaderNodeBsdfTransparent')
    node.location = x, y
    return node


def __node_add_shader(nodes, x, y):
    node = nodes.new('ShaderNodeAddShader')
    node.location = x, y
    return node


def __node_volume(nodes, density, x, y):
    node = nodes.new('ShaderNodeVolumeAbsorption')
    node.inputs['Density'].default_value = density
    node.location = x, y
    return node


def __node_light_path(nodes, x, y):
    node = nodes.new('ShaderNodeLightPath')
    node.location = x, y
    return node


def __node_math(nodes, operation, x, y):
    node = nodes.new('ShaderNodeMath')
    node.operation = operation
    node.location = x, y
    return node


def __node_vector_math(nodes, operation, x, y):
    node = nodes.new('ShaderNodeVectorMath')
    node.operation = operation
    node.location = x, y
    return node


def __node_emission(nodes, x, y):
    node = nodes.new('ShaderNodeEmission')
    node.location = x, y
    return node


def __node_voronoi(nodes, scale, x, y):
    node = nodes.new('ShaderNodeTexVoronoi')
    node.location = x, y
    node.inputs['Scale'].default_value = scale
    return node


def __node_gamma(nodes, gamma, x, y):
    node = nodes.new('ShaderNodeGamma')
    node.location = x, y
    node.inputs['Gamma'].default_value = gamma
    return node


def __node_color_ramp(nodes, pos1, color1, pos2, color2, x, y):
    node = nodes.new('ShaderNodeValToRGB')
    node.location = x, y
    node.color_ramp.elements[0].position = pos1
    node.color_ramp.elements[0].color = color1
    node.color_ramp.elements[1].position = pos2
    node.color_ramp.elements[1].color = color2
    return node


def __node_noise_texture(nodes, scale, detail, distortion, x, y):
    node = nodes.new('ShaderNodeTexNoise')
    node.location = x, y
    node.inputs['Scale'].default_value = scale
    node.inputs['Detail'].default_value = detail
    node.inputs['Distortion'].default_value = distortion
    return node


def __node_bump_shader(nodes, strength, distance, x, y):
    node = nodes.new('ShaderNodeBump')
    node.location = x, y
    node.inputs[0].default_value = strength
    node.inputs[1].default_value = distance
    return node


def __node_refraction(nodes, roughness, ior, x, y):
    node = nodes.new('ShaderNodeBsdfRefraction')
    node.inputs['Roughness'].default_value = roughness
    node.inputs['IOR'].default_value = ior
    node.location = x, y
    return node


def __get_group(nodes):
    for x in nodes:
        if x.type == 'GROUP':
            return x
    return None


def __create_cycles_slope_texture(nodes, links, strength=0.6):
    """Slope face normals for Cycles render engine"""
    slope_texture = __node_slope_texture(nodes, strength, -200, 5)
    target = __get_group(nodes)
    if target is not None:
        links.new(slope_texture.outputs['Normal'], target.inputs['Normal'])


def __create_cycles_basic(nodes, links, diff_color, alpha, col_name):
    """Basic Material for Cycles render engine."""

    use_glass = True
    if alpha < 1:
        if ldraw_colors.is_fluorescent_transparent(col_name):
            node = __node_lego_transparent_fluorescent(nodes, diff_color, 0, 5)
        elif use_glass:
            node = __node_lego_glass(nodes, diff_color, 0, 5)
        else:
            node = __node_lego_transparent(nodes, diff_color, 0, 5)
    else:
        node = __node_lego_standard(nodes, diff_color, 0, 5)

    out = __node_output(nodes, 200, 0)
    links.new(node.outputs['Shader'], out.inputs[0])


def __create_cycles_emission(nodes, links, diff_color, alpha, luminance):
    """Emission material for Cycles render engine."""

    node = __node_lego_emission(nodes, diff_color, luminance / 100.0, 0, 5)
    out = __node_output(nodes, 200, 0)
    links.new(node.outputs['Shader'], out.inputs[0])


def __create_cycles_chrome(nodes, links, diff_color):
    """Chrome material for Cycles render engine."""

    node = __node_lego_chrome(nodes, diff_color, 0, 5)
    out = __node_output(nodes, 200, 0)
    links.new(node.outputs['Shader'], out.inputs[0])


def __create_cycles_pearlescent(nodes, links, diff_color):
    """Pearlescent material for Cycles render engine."""

    node = __node_lego_pearlescent(nodes, diff_color, 0, 5)
    out = __node_output(nodes, 200, 0)
    links.new(node.outputs['Shader'], out.inputs[0])


def __create_cycles_metal(nodes, links, diff_color):
    """Metal material for Cycles render engine."""

    node = __node_lego_metal(nodes, diff_color, 0, 5)
    out = __node_output(nodes, 200, 0)
    links.new(node.outputs['Shader'], out.inputs[0])


def __create_cycles_glitter(nodes, links, diff_color, glitter_color):
    """Glitter material for Cycles render engine."""

    glitter_color = ldraw_colors.lighten_rgba(glitter_color, 0.5)
    node = __node_lego_glitter(nodes, diff_color, glitter_color, 0, 5)
    out = __node_output(nodes, 200, 0)
    links.new(node.outputs['Shader'], out.inputs[0])


def __create_cycles_speckle(nodes, links, diff_color, speckle_color):
    """Speckle material for Cycles render engine."""

    speckle_color = ldraw_colors.lighten_rgba(speckle_color, 0.5)
    node = __node_lego_speckle(nodes, diff_color, speckle_color, 0, 5)
    out = __node_output(nodes, 200, 0)
    links.new(node.outputs['Shader'], out.inputs[0])


def __create_cycles_rubber(nodes, links, diff_color, alpha):
    """Rubber material colors for Cycles render engine."""

    out = __node_output(nodes, 200, 0)

    if alpha < 1.0:
        rubber = __node_lego_rubber_translucent(nodes, diff_color, 0, 5)
    else:
        rubber = __node_lego_rubber_solid(nodes, diff_color, 0, 5)

    links.new(rubber.outputs[0], out.inputs[0])


def __create_cycles_milky_white(nodes, links, diff_color):
    """Milky White material for Cycles render engine."""

    node = __node_lego_milky_white(nodes, diff_color, 0, 5)
    out = __node_output(nodes, 200, 0)
    links.new(node.outputs['Shader'], out.inputs[0])


def __create_group(name, x1, y1, x2, y2, create_shader_output):
    group = bpy.data.node_groups.new(name, 'ShaderNodeTree')
    group.use_fake_user = True

    # create input node
    node_input = group.nodes.new('NodeGroupInput')
    node_input.location = (x1, y1)

    # create output node
    node_output = group.nodes.new('NodeGroupOutput')
    node_output.location = (x2, y2)
    if create_shader_output:
        group.outputs.new('NodeSocketShader', 'Shader')
    return group, node_input, node_output


def __create_blender_slope_texture_node_group():
    if bpy.data.node_groups.get('Slope Texture') is None:
        if options.debug_text:
            print("createBlenderSlopeTextureNodeGroup #create")

        # create a group
        group, node_input, node_output = __create_group('Slope Texture', -530, 0, 300, 0, False)

        strength_socket = group.inputs.new('NodeSocketFloat', 'Strength')
        strength_socket.default_value = 0.6

        group.inputs.new('NodeSocketVectorDirection', 'Normal')
        group.outputs.new('NodeSocketVectorDirection', 'Normal')

        # create nodes
        node_texture_coordinate = __node_tex_coord(group.nodes, -300, 240)
        node_voronoi = __node_voronoi(group.nodes, 6.2, -100, 155)
        node_bump = __node_bump_shader(group.nodes, 0.3, 1.0, 90, 50)
        node_bump.invert = True

        # link nodes together
        group.links.new(node_texture_coordinate.outputs['Object'], node_voronoi.inputs['Vector'])
        group.links.new(node_voronoi.outputs['Distance'], node_bump.inputs['Height'])
        group.links.new(node_input.outputs['Strength'], node_bump.inputs['Strength'])
        group.links.new(node_input.outputs['Normal'], node_bump.inputs['Normal'])
        group.links.new(node_bump.outputs['Normal'], node_output.inputs['Normal'])


def __create_blender_lego_standard_node_group():
    if bpy.data.node_groups.get('LEGO Standard') is None:
        if options.debug_text:
            print("createBlenderLEGOStandardNodeGroup #create")

        # create a group
        group, node_input, node_output = __create_group('LEGO Standard', -250, 0, 250, 0, True)
        group.inputs.new('NodeSocketColor', 'Color')
        group.inputs.new('NodeSocketVectorDirection', 'Normal')

        node_main = __node_principled(group.nodes, 0.05, 0.05, 0.0, 0.1, 0.0, 0.0, 1.45, 0.0, 0, 0)

        if options.add_subsurface:
            group.links.new(node_input.outputs['Color'], node_main.inputs['Subsurface Color'])

        # link nodes together
        group.links.new(node_input.outputs['Color'], node_main.inputs['Base Color'])
        group.links.new(node_input.outputs['Normal'], node_main.inputs['Normal'])
        group.links.new(node_main.outputs['BSDF'], node_output.inputs['Shader'])


def __create_blender_lego_transparent_node_group():
    if bpy.data.node_groups.get('LEGO Transparent') is None:
        if options.debug_text:
            print("createBlenderLEGOTransparentNodeGroup #create")

        # create a group
        group, node_input, node_output = __create_group('LEGO Transparent', -250, 0, 250, 0, True)
        group.inputs.new('NodeSocketColor', 'Color')
        group.inputs.new('NodeSocketVectorDirection', 'Normal')

        node_principled = __node_principled(group.nodes, 0.0, 0.0, 0.0, 0.05, 0.0, 0.0, 1.585, 1.0, 45, 340)

        # link nodes together
        group.links.new(node_input.outputs['Color'], node_principled.inputs['Base Color'])
        group.links.new(node_input.outputs['Normal'], node_principled.inputs['Normal'])
        group.links.new(node_principled.outputs['BSDF'], node_output.inputs['Shader'])


# https://blender.stackexchange.com/a/137791
# https://blenderartists.org/t/realistic-glass-in-eevee/1149937/19
def __create_blender_lego_glass_node_group():
    if 'LEGO Glass' in bpy.data.node_groups:
        return

    if options.debug_text:
        print("createBlenderLEGOGlassNodeGroup #create")

    group = bpy.data.node_groups.new('LEGO Glass', 'ShaderNodeTree')

    group_input = group.nodes.new("NodeGroupInput")
    group_input.location = (-900.0, -140.0)

    group.inputs.new('NodeSocketColor', "Color")
    group.inputs.new('NodeSocketVectorDirection', "Normal")

    bsdf_glass = group.nodes.new("ShaderNodeBsdfGlass")
    bsdf_glass.location = (-700.0, -60.0)
    bsdf_glass.inputs[1].default_value = 0.0
    bsdf_glass.inputs[2].default_value = 1.45

    bsdf_glossy = group.nodes.new("ShaderNodeBsdfGlossy")
    bsdf_glossy.location = (-700.0, -300.0)
    bsdf_glossy.inputs[1].default_value = 0.5

    fresnel = group.nodes.new("ShaderNodeFresnel")
    fresnel.location = (-900.0, 100.0)
    fresnel.inputs[0].default_value = 1.4

    bsdf_glossy_0 = group.nodes.new("ShaderNodeBsdfGlossy")
    bsdf_glossy_0.location = (-400.0, -220.0)
    bsdf_glossy_0.inputs[1].default_value = 0.5

    rgb_curve = group.nodes.new("ShaderNodeRGBCurve")
    rgb_curve.location = (-700.0, 340.0)
    rgb_curve.inputs[0].default_value = 0.5
    curves = 3
    r = 0
    g = 1
    b = 2
    curves = rgb_curve.mapping.curves[curves]
    curves.points.new(0.0000, 0.0000)
    curves.points.new(0.6227, 0.2438)
    curves.points.new(1.0000, 1.0000)

    mix = group.nodes.new("ShaderNodeMixShader")
    mix.location = (-400.0, -40.0)
    mix.inputs[0].default_value = 0.25

    fresnel_0 = group.nodes.new("ShaderNodeFresnel")
    fresnel_0.location = (-400.0, 120.0)
    fresnel_0.inputs[0].default_value = 1.4

    mix_0 = group.nodes.new("ShaderNodeMixShader")
    mix_0.location = (-200.0, 0.0)
    mix_0.inputs[0].default_value = 0.5

    group_output = group.nodes.new("NodeGroupOutput")
    group_output.location = (0.0, 0.0)

    group.outputs.new('NodeSocketShader', "Shader")

    group.links.new(group_input.outputs[0], bsdf_glass.inputs[0])
    group.links.new(group_input.outputs[1], bsdf_glass.inputs[3])
    group.links.new(group_input.outputs[0], bsdf_glossy_0.inputs[0])
    group.links.new(bsdf_glass.outputs[0], mix.inputs[1])
    group.links.new(bsdf_glossy.outputs[0], mix.inputs[2])
    group.links.new(bsdf_glossy_0.outputs[0], mix_0.inputs[2])
    group.links.new(mix.outputs[0], mix_0.inputs[1])
    group.links.new(mix_0.outputs[0], group_output.inputs[0])
    group.links.new(fresnel.outputs[0], rgb_curve.inputs[1])
    group.links.new(rgb_curve.outputs[0], mix.inputs[0])
    group.links.new(fresnel_0.outputs[0], mix_0.inputs[0])


def __create_blender_lego_transparent_fluorescent_node_group():
    if bpy.data.node_groups.get('LEGO Transparent Fluorescent') is None:
        if options.debug_text:
            print("createBlenderLEGOTransparentFluorescentNodeGroup #create")

        # create a group
        group, node_input, node_output = __create_group('LEGO Transparent Fluorescent', -250, 0, 250, 0, True)
        group.inputs.new('NodeSocketColor', 'Color')
        group.inputs.new('NodeSocketVectorDirection', 'Normal')

        node_principled = __node_principled(group.nodes, 0.0, 0.0, 0.0, 0.05, 0.0, 0.0, 1.585, 1.0, 45, 340)
        node_emission = __node_emission(group.nodes, 45, -160)
        node_mix = __node_mix(group.nodes, 0.03, 300, 290)

        node_output.location = 500, 290

        # link nodes together
        group.links.new(node_input.outputs['Color'], node_principled.inputs['Base Color'])
        group.links.new(node_input.outputs['Color'], node_emission.inputs['Color'])
        group.links.new(node_input.outputs['Normal'], node_principled.inputs['Normal'])
        group.links.new(node_principled.outputs['BSDF'], node_mix.inputs[1])
        group.links.new(node_emission.outputs['Emission'], node_mix.inputs[2])
        group.links.new(node_mix.outputs[0], node_output.inputs['Shader'])


def __create_blender_lego_rubber_node_group():
    if bpy.data.node_groups.get('LEGO Rubber Solid') is None:
        if options.debug_text:
            print("createBlenderLEGORubberNodeGroup #create")

        # create a group
        group, node_input, node_output = __create_group('LEGO Rubber Solid', 45 - 950, 340 - 50, 45 + 200, 340 - 5, True)
        group.inputs.new('NodeSocketColor', 'Color')
        group.inputs.new('NodeSocketVectorDirection', 'Normal')

        node_noise = __node_noise_texture(group.nodes, 250, 2, 0.0, 45 - 770, 340 - 200)
        node_bump1 = __node_bump_shader(group.nodes, 1.0, 0.3, 45 - 366, 340 - 200)
        node_bump2 = __node_bump_shader(group.nodes, 1.0, 0.1, 45 - 184, 340 - 115)
        node_subtract = __node_math(group.nodes, 'SUBTRACT', 45 - 570, 340 - 216)
        node_principled = __node_principled(group.nodes, 0.0, 0.0, 0.0, 0.4, 0.03, 0.0, 1.45, 0.0, 45, 340)

        node_subtract.inputs[1].default_value = 0.4

        group.links.new(node_input.outputs['Color'], node_principled.inputs['Base Color'])
        group.links.new(node_principled.outputs['BSDF'], node_output.inputs[0])
        group.links.new(node_noise.outputs['Color'], node_subtract.inputs[0])
        group.links.new(node_subtract.outputs[0], node_bump1.inputs['Height'])
        group.links.new(node_bump1.outputs['Normal'], node_bump2.inputs['Normal'])
        group.links.new(node_bump2.outputs['Normal'], node_principled.inputs['Normal'])


def __create_blender_lego_rubber_translucent_node_group():
    if bpy.data.node_groups.get('LEGO Rubber Translucent') is None:
        if options.debug_text:
            print("createBlenderLEGORubberTranslucentNodeGroup #create")

        # create a group
        group, node_input, node_output = __create_group('LEGO Rubber Translucent', -250, 0, 250, 0, True)
        group.inputs.new('NodeSocketColor', 'Color')
        group.inputs.new('NodeSocketVectorDirection', 'Normal')

        node_noise = __node_noise_texture(group.nodes, 250, 2, 0.0, 45 - 770, 340 - 200)
        node_bump1 = __node_bump_shader(group.nodes, 1.0, 0.3, 45 - 366, 340 - 200)
        node_bump2 = __node_bump_shader(group.nodes, 1.0, 0.1, 45 - 184, 340 - 115)
        node_subtract = __node_math(group.nodes, 'SUBTRACT', 45 - 570, 340 - 216)
        node_principled = __node_principled(group.nodes, 0.0, 0.0, 0.0, 0.4, 0.03, 0.0, 1.45, 0.0, 45, 340)
        node_mix = __node_mix(group.nodes, 0.8, 300, 290)
        node_refraction = __node_refraction(group.nodes, 0.0, 1.45, 290 - 242, 154 - 330)
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


def __create_blender_lego_emission_node_group():
    if bpy.data.node_groups.get('LEGO Emission') is None:
        if options.debug_text:
            print("createBlenderLEGOEmissionNodeGroup #create")

        # create a group
        group, node_input, node_output = __create_group('LEGO Emission', -450, 90, 250, 0, True)
        group.inputs.new('NodeSocketColor', 'Color')
        group.inputs.new('NodeSocketFloatFactor', 'Luminance')
        group.inputs.new('NodeSocketVectorDirection', 'Normal')

        node_emit = __node_emission(group.nodes, -242, -123)
        node_mix = __node_mix(group.nodes, 0.5, 0, 90)

        node_main = __node_principled(group.nodes, 1.0, 0.05, 0.0, 0.5, 0.0, 0.03, 1.45, 0.0, -242, 154 + 240)
        if options.add_subsurface:
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


def __create_blender_lego_chrome_node_group():
    if bpy.data.node_groups.get('LEGO Chrome') is None:
        if options.debug_text:
            print("createBlenderLEGOChromeNodeGroup #create")

        # create a group
        group, node_input, node_output = __create_group('LEGO Chrome', -450, 90, 250, 0, True)
        group.inputs.new('NodeSocketColor', 'Color')
        group.inputs.new('NodeSocketVectorDirection', 'Normal')

        node_hsv = __node_hsv(group.nodes, 0.5, 0.9, 2.0, -90, 0)
        node_principled = __node_principled(group.nodes, 0.0, 0.0, 1.0, 0.0, 1.0, 0.0, 2.4, 0.0, 100, 0)

        node_output.location = (575, -140)

        # link nodes together
        group.links.new(node_input.outputs['Color'], node_hsv.inputs['Color'])
        group.links.new(node_input.outputs['Normal'], node_principled.inputs['Normal'])
        group.links.new(node_hsv.outputs['Color'], node_principled.inputs['Base Color'])
        group.links.new(node_principled.outputs['BSDF'], node_output.inputs[0])


def __create_blender_lego_pearlescent_node_group():
    if bpy.data.node_groups.get('LEGO Pearlescent') is None:
        if options.debug_text:
            print("createBlenderLEGOPearlescentNodeGroup #create")

        # create a group
        group, node_input, node_output = __create_group('LEGO Pearlescent', -450, 90, 630, 95, True)
        group.inputs.new('NodeSocketColor', 'Color')
        group.inputs.new('NodeSocketVectorDirection', 'Normal')

        node_principled = __node_principled(group.nodes, 1.0, 0.25, 0.5, 0.2, 1.0, 0.2, 1.6,
                                            0.0, 310, 95)
        node_sep_hsv = __node_separate_hsv(group.nodes, -240, 75)
        node_multiply = __node_math(group.nodes, 'MULTIPLY', -60, 0)
        node_com_hsv = __node_combine_hsv(group.nodes, 110, 95)
        node_tex_coord = __node_tex_coord(group.nodes, -730, -223)
        node_tex_wave = __node_tex_wave(group.nodes, 'BANDS', 'SIN', 0.5, 40, 1, 1.5, -520, -190)
        node_color_ramp = __node_color_ramp(group.nodes, 0.329, (0.89, 0.89, 0.89, 1), 0.820, (1, 1, 1, 1), -340, -70)
        element = node_color_ramp.color_ramp.elements.new(1.0)
        element.color = (1.118, 1.118, 1.118, 1)

        # link nodes together
        group.links.new(node_input.outputs['Color'], node_sep_hsv.inputs['Color'])
        group.links.new(node_input.outputs['Normal'], node_principled.inputs['Normal'])
        group.links.new(node_sep_hsv.outputs['H'], node_com_hsv.inputs['H'])
        group.links.new(node_sep_hsv.outputs['S'], node_com_hsv.inputs['S'])
        group.links.new(node_sep_hsv.outputs['V'], node_multiply.inputs[0])
        group.links.new(node_com_hsv.outputs['Color'], node_principled.inputs['Base Color'])
        if options.add_subsurface:
            group.links.new(node_com_hsv.outputs['Color'], node_principled.inputs['Subsurface Color'])
        group.links.new(node_tex_coord.outputs['Object'], node_tex_wave.inputs['Vector'])
        group.links.new(node_tex_wave.outputs['Fac'], node_color_ramp.inputs['Fac'])
        group.links.new(node_color_ramp.outputs['Color'], node_multiply.inputs[1])
        group.links.new(node_multiply.outputs[0], node_com_hsv.inputs['V'])
        group.links.new(node_principled.outputs['BSDF'], node_output.inputs[0])


def __create_blender_lego_metal_node_group():
    if bpy.data.node_groups.get('LEGO Metal') is None:
        if options.debug_text:
            print("createBlenderLEGOMetalNodeGroup #create")

        # create a group
        group, node_input, node_output = __create_group('LEGO Metal', -450, 90, 250, 0, True)
        group.inputs.new('NodeSocketColor', 'Color')
        group.inputs.new('NodeSocketVectorDirection', 'Normal')

        node_principled = __node_principled(group.nodes, 0.0, 0.0, 0.8, 0.2, 0.0, 0.03, 1.45, 0.0, 310, 95)

        group.links.new(node_input.outputs['Color'], node_principled.inputs['Base Color'])
        group.links.new(node_input.outputs['Normal'], node_principled.inputs['Normal'])
        group.links.new(node_principled.outputs[0], node_output.inputs['Shader'])


def __create_blender_lego_glitter_node_group():
    if bpy.data.node_groups.get('LEGO Glitter') is None:
        if options.debug_text:
            print("createBlenderLEGOGlitterNodeGroup #create")

        # create a group
        group, node_input, node_output = __create_group('LEGO Glitter', -450, 0, 410, 0, True)
        group.inputs.new('NodeSocketColor', 'Color')
        group.inputs.new('NodeSocketColor', 'Glitter Color')
        group.inputs.new('NodeSocketVectorDirection', 'Normal')

        node_voronoi = __node_voronoi(group.nodes, 100, -222, 310)
        node_gamma = __node_gamma(group.nodes, 50, 0, 200)
        node_mix = __node_mix(group.nodes, 0.05, 210, 90 + 25)
        node_principled1 = __node_principled(group.nodes, 0.0, 0.0, 0.0, 0.2, 0.0, 0.03, 1.585, 1.0, 45 - 270, 340 - 210)
        node_principled2 = __node_principled(group.nodes, 0.0, 0.0, 0.0, 0.5, 0.0, 0.03, 1.45, 0.0, 45 - 270, 340 - 750)

        group.links.new(node_input.outputs['Color'], node_principled1.inputs['Base Color'])
        group.links.new(node_input.outputs['Glitter Color'], node_principled2.inputs['Base Color'])
        group.links.new(node_input.outputs['Normal'], node_principled1.inputs['Normal'])
        group.links.new(node_input.outputs['Normal'], node_principled2.inputs['Normal'])
        group.links.new(node_voronoi.outputs['Color'], node_gamma.inputs['Color'])
        group.links.new(node_gamma.outputs[0], node_mix.inputs[0])
        group.links.new(node_principled1.outputs['BSDF'], node_mix.inputs[1])
        group.links.new(node_principled2.outputs['BSDF'], node_mix.inputs[2])
        group.links.new(node_mix.outputs[0], node_output.inputs[0])


def __create_blender_lego_speckle_node_group():
    if bpy.data.node_groups.get('LEGO Speckle') is None:
        if options.debug_text:
            print("createBlenderLEGOSpeckleNodeGroup #create")

        # create a group
        group, node_input, node_output = __create_group('LEGO Speckle', -450, 0, 410, 0, True)
        group.inputs.new('NodeSocketColor', 'Color')
        group.inputs.new('NodeSocketColor', 'Speckle Color')
        group.inputs.new('NodeSocketVectorDirection', 'Normal')

        node_voronoi = __node_voronoi(group.nodes, 50, -222, 310)
        node_gamma = __node_gamma(group.nodes, 3.5, 0, 200)
        node_mix = __node_mix(group.nodes, 0.05, 210, 90 + 25)
        node_principled1 = __node_principled(group.nodes, 0.0, 0.0, 0.0, 0.1, 0.0, 0.03, 1.45, 0.0, 45 - 270, 340 - 210)
        node_principled2 = __node_principled(group.nodes, 0.0, 0.0, 1.0, 0.5, 0.0, 0.03, 1.45, 0.0, 45 - 270, 340 - 750)

        group.links.new(node_input.outputs['Color'], node_principled1.inputs['Base Color'])
        group.links.new(node_input.outputs['Speckle Color'], node_principled2.inputs['Base Color'])
        group.links.new(node_input.outputs['Normal'], node_principled1.inputs['Normal'])
        group.links.new(node_input.outputs['Normal'], node_principled2.inputs['Normal'])
        group.links.new(node_voronoi.outputs['Color'], node_gamma.inputs['Color'])
        group.links.new(node_gamma.outputs[0], node_mix.inputs[0])
        group.links.new(node_principled1.outputs['BSDF'], node_mix.inputs[1])
        group.links.new(node_principled2.outputs['BSDF'], node_mix.inputs[2])
        group.links.new(node_mix.outputs[0], node_output.inputs[0])


def __create_blender_lego_milky_white_node_group():
    if bpy.data.node_groups.get('LEGO Milky White') is None:
        if options.debug_text:
            print("createBlenderLEGOMilkyWhiteNodeGroup #create")

        # create a group
        group, node_input, node_output = __create_group('LEGO Milky White', -450, 0, 350, 0, True)
        group.inputs.new('NodeSocketColor', 'Color')
        group.inputs.new('NodeSocketVectorDirection', 'Normal')

        node_principled = __node_principled(group.nodes, 1.0, 0.05, 0.0, 0.5, 0.0, 0.03, 1.45, 0.0, 45 - 270, 340 - 210)
        node_translucent = __node_translucent(group.nodes, -225, -382)
        node_mix = __node_mix(group.nodes, 0.5, 65, -40)

        group.links.new(node_input.outputs['Color'], node_principled.inputs['Base Color'])
        if options.add_subsurface:
            group.links.new(node_input.outputs['Color'], node_principled.inputs['Subsurface Color'])
        group.links.new(node_input.outputs['Normal'], node_principled.inputs['Normal'])
        group.links.new(node_input.outputs['Normal'], node_translucent.inputs['Normal'])
        group.links.new(node_principled.outputs[0], node_mix.inputs[1])
        group.links.new(node_translucent.outputs[0], node_mix.inputs[2])
        group.links.new(node_mix.outputs[0], node_output.inputs[0])
