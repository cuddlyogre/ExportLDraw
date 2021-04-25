import bpy
import mathutils
import os

from . import strings
from . import options
from . import ldraw_colors
from . import filesystem


# https://github.com/bblanimation/abs-plastic-materials
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


def create_ldraw_materials():
    for is_slope_material in (False, True):
        for color_code in ldraw_colors.colors:
            color = ldraw_colors.colors[color_code]
            # is_slope_material = False
            use_edge_color = False
            get_material(color, is_slope_material=is_slope_material, use_edge_color=use_edge_color)


def get_material(color, use_edge_color=False, is_slope_material=False, texmap=None):
    key = []
    key.append("LDraw Material")
    key.append(color.code)
    key.append(color.name)

    suffix = []
    if options.use_alt_colors:
        suffix.append("alt")
    if is_slope_material:
        suffix.append("s")
    if options.add_subsurface:
        suffix.append("ss")
    if not options.use_glass:
        suffix.append("t")
    if use_edge_color:
        suffix.append("edge")
    if texmap is not None:
        texmap_suffix = "_".join([x for x in [texmap.method, texmap.texture, texmap.glossmap] if x != ''])
        suffix.append(texmap_suffix)
    suffix = "_".join([k.lower() for k in suffix])

    key.append(suffix)
    key = " ".join(key)

    if key in bpy.data.materials:
        return bpy.data.materials[key]

    material = __create_node_based_material(key, color, use_edge_color=use_edge_color, is_slope_material=is_slope_material, texmap=texmap)

    return material


def __create_node_based_material(key, color, use_edge_color=False, is_slope_material=False, texmap=None):
    """Set Cycles Material Values."""

    # Reuse current material if it exists, otherwise create a new material
    if bpy.data.materials.get(key) is None:
        bpy.data.materials.new(key)
    material = bpy.data.materials[key]

    material.use_fake_user = True
    material.use_nodes = True

    nodes = material.node_tree.nodes
    links = material.node_tree.links

    nodes.clear()

    is_transparent = False

    if color is None:
        diff_color = (1.0, 1.0, 0.0) + (1.0,)
        material.diffuse_color = diff_color
        material["LEGO.isTransparent"] = is_transparent
        material[strings.ldraw_color_code_key] = "16"
        __create_cycles_standard(nodes, links, diff_color)
        return material

    if use_edge_color:
        diff_color = color.edge_color + (1.0,)
        material.diffuse_color = diff_color
        material["LEGO.isTransparent"] = is_transparent
        material[strings.ldraw_color_code_key] = "24"
        __create_cycles_standard(nodes, links, diff_color)
        return material

    is_transparent = color.alpha < 1.0

    diff_color = color.color + (1.0,)
    material.diffuse_color = diff_color
    material["LEGO.isTransparent"] = is_transparent
    material[strings.ldraw_color_code_key] = color.code

    if is_transparent:
        material.blend_method = "BLEND"
        material.refraction_depth = 0.1
        material.use_screen_refraction = True

    if color.name == "Milky_White":
        __create_cycles_milky_white(nodes, links, diff_color)
    elif color.luminance > 0:
        __create_cycles_emission(nodes, links, diff_color, color.luminance)
    elif color.material == "CHROME":
        __create_cycles_chrome(nodes, links, diff_color)
    elif color.material == "PEARLESCENT":
        __create_cycles_pearlescent(nodes, links, diff_color)
    elif color.material == "METAL":
        __create_cycles_metal(nodes, links, diff_color)
    elif color.material == "GLITTER":
        __create_cycles_glitter(nodes, links, diff_color, color.secondary_color)
    elif color.material == "SPECKLE":
        __create_cycles_speckle(nodes, links, diff_color, color.secondary_color)
    elif color.material == "RUBBER":
        if is_transparent:
            __create_cycles_rubber_translucent(nodes, links, diff_color)
        else:
            __create_cycles_rubber(nodes, links, diff_color)
    elif is_transparent:
        if ldraw_colors.is_fluorescent_transparent(color.name):
            __create_cycles_fluorescent_transparent(nodes, links, diff_color)
        else:
            if options.use_glass:
                __create_cycles_glass(nodes, links, diff_color)
            else:
                __create_cycles_transparent(nodes, links, diff_color)
    else:
        __create_cycles_standard(nodes, links, diff_color)

    if texmap is not None:
        __create_texmap_texture(nodes, links, diff_color, texmap)

    if is_slope_material:
        __create_cycles_slope_texture(nodes, links)

    return material


def __node_texmap_texture():
    pass


def __node_slope_texture(nodes, strength, x, y):
    node = nodes.new("ShaderNodeGroup")
    node.name = "slope_texture"
    node.node_tree = bpy.data.node_groups["LEGO Slope Bump"]
    node.location = x, y
    node.inputs["Strength"].default_value = strength
    return node


def __node_lego_standard(nodes, color, x, y):
    node = nodes.new("ShaderNodeGroup")
    node.name = "standard"
    node.node_tree = bpy.data.node_groups["LEGO Standard"]
    node.location = x, y
    node.inputs["Color"].default_value = color
    return node


def __node_lego_transparent_fluorescent(nodes, color, x, y):
    node = nodes.new("ShaderNodeGroup")
    node.name = "transparent_fluorescent"
    node.node_tree = bpy.data.node_groups["LEGO Transparent Fluorescent"]
    node.location = x, y
    node.inputs["Color"].default_value = color
    return node


def __node_lego_transparent(nodes, color, x, y):
    node = nodes.new("ShaderNodeGroup")
    node.name = "transparent"
    node.node_tree = bpy.data.node_groups["LEGO Transparent"]
    node.location = x, y
    node.inputs["Color"].default_value = color
    return node


def __node_lego_glass(nodes, color, x, y):
    node = nodes.new("ShaderNodeGroup")
    node.name = "glass"
    node.node_tree = bpy.data.node_groups["LEGO Glass"]
    node.location = x, y
    node.inputs["Color"].default_value = color
    return node


def __node_lego_rubber(nodes, color, x, y):
    node = nodes.new("ShaderNodeGroup")
    node.name = "rubber"
    node.node_tree = bpy.data.node_groups["LEGO Rubber Solid"]
    node.location = x, y
    node.inputs["Color"].default_value = color
    return node


def __node_lego_rubber_translucent(nodes, color, x, y):
    node = nodes.new("ShaderNodeGroup")
    node.name = "rubber_translucent"
    node.node_tree = bpy.data.node_groups["LEGO Rubber Translucent"]
    node.location = x, y
    node.inputs["Color"].default_value = color
    return node


def __node_lego_emission(nodes, color, luminance, x, y):
    node = nodes.new("ShaderNodeGroup")
    node.name = "emission"
    node.node_tree = bpy.data.node_groups["LEGO Emission"]
    node.location = x, y
    node.inputs["Color"].default_value = color
    node.inputs["Luminance"].default_value = luminance
    return node


def __node_lego_chrome(nodes, color, x, y):
    node = nodes.new("ShaderNodeGroup")
    node.name = "chrome"
    node.node_tree = bpy.data.node_groups["LEGO Chrome"]
    node.location = x, y
    node.inputs["Color"].default_value = color
    return node


def __node_lego_pearlescent(nodes, color, x, y):
    node = nodes.new("ShaderNodeGroup")
    node.name = "pearlescent"
    node.node_tree = bpy.data.node_groups["LEGO Pearlescent"]
    node.location = x, y
    node.inputs["Color"].default_value = color
    return node


def __node_lego_metal(nodes, color, x, y):
    node = nodes.new("ShaderNodeGroup")
    node.name = "metal"
    node.node_tree = bpy.data.node_groups["LEGO Metal"]
    node.location = x, y
    node.inputs["Color"].default_value = color
    return node


def __node_lego_glitter(nodes, color, glitter_color, x, y):
    node = nodes.new("ShaderNodeGroup")
    node.name = "glitter"
    node.node_tree = bpy.data.node_groups["LEGO Glitter"]
    node.location = x, y
    node.inputs["Color"].default_value = color
    node.inputs["Glitter Color"].default_value = glitter_color
    return node


def __node_lego_speckle(nodes, color, speckle_color, x, y):
    node = nodes.new("ShaderNodeGroup")
    node.name = "speckle"
    node.node_tree = bpy.data.node_groups["LEGO Speckle"]
    node.location = x, y
    node.inputs["Color"].default_value = color
    node.inputs["Speckle Color"].default_value = speckle_color
    return node


def __node_lego_milky_white(nodes, color, x, y):
    node = nodes.new("ShaderNodeGroup")
    node.name = "milky_white"
    node.node_tree = bpy.data.node_groups["LEGO Milky White"]
    node.location = x, y
    node.inputs["Color"].default_value = color
    return node


def __node_mix(nodes, factor, x, y):
    node = nodes.new("ShaderNodeMixShader")
    node.location = x, y
    node.inputs["Fac"].default_value = factor
    return node


def __node_output(nodes, x, y):
    node = nodes.new("ShaderNodeOutputMaterial")
    node.location = x, y
    return node


def __node_principled(nodes, subsurface, sub_rad, metallic, roughness, clearcoat, clearcoat_roughness, ior, transmission, x, y):
    node = nodes.new("ShaderNodeBsdfPrincipled")
    node.location = x, y
    if options.add_subsurface:
        node.inputs["Subsurface"].default_value = subsurface
        node.inputs["Subsurface Radius"].default_value = mathutils.Vector((sub_rad, sub_rad, sub_rad))
    node.inputs["Metallic"].default_value = metallic
    node.inputs["Roughness"].default_value = roughness
    node.inputs["Clearcoat"].default_value = clearcoat
    node.inputs["Clearcoat Roughness"].default_value = clearcoat_roughness
    node.inputs["IOR"].default_value = ior
    node.inputs["Transmission"].default_value = transmission
    return node


def __node_hsv(nodes, h, s, v, x, y):
    node = nodes.new("ShaderNodeHueSaturation")
    node.location = x, y
    node.inputs[0].default_value = h
    node.inputs[1].default_value = s
    node.inputs[2].default_value = v
    return node


def __node_separate_hsv(nodes, x, y):
    node = nodes.new("ShaderNodeSeparateHSV")
    node.location = x, y
    return node


def __node_combine_hsv(nodes, x, y):
    node = nodes.new("ShaderNodeCombineHSV")
    node.location = x, y
    return node


def __node_tex_coord(nodes, x, y):
    node = nodes.new("ShaderNodeTexCoord")
    node.location = x, y
    return node


def __node_mapping(nodes, x, y):
    node = nodes.new("ShaderNodeMapping")
    node.location = x, y
    return node


def __node_tex_image(nodes, x, y):
    node = nodes.new("ShaderNodeTexImage")
    node.location = x, y
    return node


def __node_mix_rgb(nodes, x, y):
    node = nodes.new("ShaderNodeMixRGB")
    node.location = x, y
    return node


def __node_tex_wave(nodes, wave_type, wave_profile, scale, distortion, detail, detail_scale, x, y):
    node = nodes.new("ShaderNodeTexWave")
    node.wave_type = wave_type
    node.wave_profile = wave_profile
    node.inputs[1].default_value = scale
    node.inputs[2].default_value = distortion
    node.inputs[3].default_value = detail
    node.inputs[4].default_value = detail_scale
    node.location = x, y
    return node


def __node_diffuse(nodes, roughness, x, y):
    node = nodes.new("ShaderNodeBsdfDiffuse")
    node.location = x, y
    node.inputs["Color"].default_value = (1, 1, 1, 1)
    node.inputs["Roughness"].default_value = roughness
    return node


def __node_glass(nodes, roughness, ior, distribution, x, y):
    node = nodes.new("ShaderNodeBsdfGlass")
    node.location = x, y
    node.distribution = distribution
    node.inputs["Color"].default_value = (1, 1, 1, 1)
    node.inputs["Roughness"].default_value = roughness
    node.inputs["IOR"].default_value = ior
    return node


def __node_fresnel(nodes, ior, x, y):
    node = nodes.new("ShaderNodeFresnel")
    node.location = x, y
    node.inputs["IOR"].default_value = ior
    return node


def __node_glossy(nodes, color, roughness, distribution, x, y):
    node = nodes.new("ShaderNodeBsdfGlossy")
    node.location = x, y
    node.distribution = distribution
    node.inputs["Color"].default_value = color
    node.inputs["Roughness"].default_value = roughness
    return node


def __node_translucent(nodes, x, y):
    node = nodes.new("ShaderNodeBsdfTranslucent")
    node.location = x, y
    return node


def __node_transparent(nodes, x, y):
    node = nodes.new("ShaderNodeBsdfTransparent")
    node.location = x, y
    return node


def __node_add_shader(nodes, x, y):
    node = nodes.new("ShaderNodeAddShader")
    node.location = x, y
    return node


def __node_volume(nodes, density, x, y):
    node = nodes.new("ShaderNodeVolumeAbsorption")
    node.inputs["Density"].default_value = density
    node.location = x, y
    return node


def __node_light_path(nodes, x, y):
    node = nodes.new("ShaderNodeLightPath")
    node.location = x, y
    return node


def __node_math(nodes, operation, x, y):
    node = nodes.new("ShaderNodeMath")
    node.operation = operation
    node.location = x, y
    return node


def __node_vector_math(nodes, operation, x, y):
    node = nodes.new("ShaderNodeVectorMath")
    node.operation = operation
    node.location = x, y
    return node


def __node_emission(nodes, x, y):
    node = nodes.new("ShaderNodeEmission")
    node.location = x, y
    return node


def __node_voronoi(nodes, scale, x, y):
    node = nodes.new("ShaderNodeTexVoronoi")
    node.location = x, y
    node.inputs["Scale"].default_value = scale
    return node


def __node_gamma(nodes, gamma, x, y):
    node = nodes.new("ShaderNodeGamma")
    node.location = x, y
    node.inputs["Gamma"].default_value = gamma
    return node


def __node_color_ramp(nodes, pos1, color1, pos2, color2, x, y):
    node = nodes.new("ShaderNodeValToRGB")
    node.location = x, y
    node.color_ramp.elements[0].position = pos1
    node.color_ramp.elements[0].color = color1
    node.color_ramp.elements[1].position = pos2
    node.color_ramp.elements[1].color = color2
    return node


def __node_noise_texture(nodes, scale, detail, distortion, x, y):
    node = nodes.new("ShaderNodeTexNoise")
    node.location = x, y
    node.inputs["Scale"].default_value = scale
    node.inputs["Detail"].default_value = detail
    node.inputs["Distortion"].default_value = distortion
    return node


def __node_bump_shader(nodes, strength, distance, x, y):
    node = nodes.new("ShaderNodeBump")
    node.location = x, y
    node.inputs[0].default_value = strength
    node.inputs[1].default_value = distance
    return node


def __node_refraction(nodes, roughness, ior, x, y):
    node = nodes.new("ShaderNodeBsdfRefraction")
    node.inputs["Roughness"].default_value = roughness
    node.inputs["IOR"].default_value = ior
    node.location = x, y
    return node


def __get_group(nodes):
    for x in nodes:
        if x.type == "GROUP":
            return x
    return None


def __create_texmap_texture(nodes, links, diff_color, texmap):
    # node_tree.nodes.active
    target = __get_group(nodes)
    if target is None:
        return

    image_name = texmap.texture
    if image_name is not None:
        texmap_image = __node_tex_image(nodes, -500.0, 0.0)
        texmap_image.name = 'ldraw_texmap_image'
        texmap_image.interpolation = "Closest"
        texmap_image.extension = "CLIP"

        if image_name not in bpy.data.images:
            # TODO: requests retrieve image from ldraw.org
            image_path = filesystem.locate(image_name, texture=True)

            if image_path is not None:
                # https://blender.stackexchange.com/questions/157531/blender-2-8-python-add-texture-image
                image = bpy.data.images.load(image_path)
                image.name = image_name
                image[strings.ldraw_filename_key] = image_name

        if image_name in bpy.data.images:
            image = bpy.data.images[image_name]
            texmap_image.image = image

        mix_rgb = __node_mix_rgb(nodes, -200, 0.0)
        mix_rgb.inputs["Color1"].default_value = diff_color

        links.new(texmap_image.outputs["Color"], mix_rgb.inputs["Color2"])
        links.new(texmap_image.outputs["Alpha"], mix_rgb.inputs["Fac"])
        links.new(mix_rgb.outputs["Color"], target.inputs["Color"])

    image_name = texmap.glossmap
    if image_name != '':
        glossmap_image = __node_tex_image(nodes, -360.0, -280.0)
        glossmap_image.name = 'ldraw_glossmap_image'
        glossmap_image.interpolation = "Closest"
        glossmap_image.extension = "CLIP"

        if image_name not in bpy.data.images:
            image_path = filesystem.locate(image_name, texture=True)
            if image_path is not None:
                image = bpy.data.images.load(image_path)
                image.name = image_name
                image[strings.ldraw_filename_key] = image_name
                image.colorspace_settings.name = 'Non-Color'

        if image_name in bpy.data.images:
            image = bpy.data.images[image_name]
            glossmap_image.image = image

        links.new(glossmap_image.outputs["Color"], target.inputs["Specular"])


# TODO: slight variation in strength for each material
def __create_cycles_slope_texture(nodes, links, strength=None):
    """Slope face normals for Cycles render engine"""

    if strength is None:
        strength = options.slope_texture_strength

    slope_texture = __node_slope_texture(nodes, strength, -200, 0)
    target = __get_group(nodes)
    if target is not None:
        links.new(slope_texture.outputs["Normal"], target.inputs["Normal"])


def __create_cycles_fluorescent_transparent(nodes, links, diff_color):
    """Fluorescent Transparent Material for Cycles render engine."""

    node = __node_lego_transparent_fluorescent(nodes, diff_color, 0, 0)
    out = __node_output(nodes, 200, 0)
    links.new(node.outputs["Shader"], out.inputs[0])


def __create_cycles_glass(nodes, links, diff_color):
    """Glass Material for Cycles render engine."""

    node = __node_lego_glass(nodes, diff_color, 0, 0)
    out = __node_output(nodes, 200, 0)
    links.new(node.outputs["Shader"], out.inputs[0])


def __create_cycles_transparent(nodes, links, diff_color):
    """Transparent Material for Cycles render engine."""

    node = __node_lego_transparent(nodes, diff_color, 0, 0)
    out = __node_output(nodes, 200, 0)
    links.new(node.outputs["Shader"], out.inputs[0])


def __create_cycles_standard(nodes, links, diff_color):
    """Basic Material for Cycles render engine."""

    node = __node_lego_standard(nodes, diff_color, 0, 0)
    out = __node_output(nodes, 200, 0)
    links.new(node.outputs["Shader"], out.inputs[0])


def __create_cycles_emission(nodes, links, diff_color, luminance):
    """Emission material for Cycles render engine."""

    node = __node_lego_emission(nodes, diff_color, luminance / 100.0, 0, 0)
    out = __node_output(nodes, 200, 0)
    links.new(node.outputs["Shader"], out.inputs[0])


def __create_cycles_chrome(nodes, links, diff_color):
    """Chrome material for Cycles render engine."""

    node = __node_lego_chrome(nodes, diff_color, 0, 0)
    out = __node_output(nodes, 200, 0)
    links.new(node.outputs["Shader"], out.inputs[0])


def __create_cycles_pearlescent(nodes, links, diff_color):
    """Pearlescent material for Cycles render engine."""

    node = __node_lego_pearlescent(nodes, diff_color, 0, 0)
    out = __node_output(nodes, 200, 0)
    links.new(node.outputs["Shader"], out.inputs[0])


def __create_cycles_metal(nodes, links, diff_color):
    """Metal material for Cycles render engine."""

    node = __node_lego_metal(nodes, diff_color, 0, 0)
    out = __node_output(nodes, 200, 0)
    links.new(node.outputs["Shader"], out.inputs[0])


def __create_cycles_glitter(nodes, links, diff_color, glitter_color):
    """Glitter material for Cycles render engine."""

    glitter_color = ldraw_colors.lighten_rgba(glitter_color, 0.5)
    node = __node_lego_glitter(nodes, diff_color, glitter_color, 0, 0)
    out = __node_output(nodes, 200, 0)
    links.new(node.outputs["Shader"], out.inputs[0])


def __create_cycles_speckle(nodes, links, diff_color, speckle_color):
    """Speckle material for Cycles render engine."""

    speckle_color = ldraw_colors.lighten_rgba(speckle_color, 0.5)
    node = __node_lego_speckle(nodes, diff_color, speckle_color, 0, 0)
    out = __node_output(nodes, 200, 0)
    links.new(node.outputs["Shader"], out.inputs[0])


def __create_cycles_rubber(nodes, links, diff_color):
    """Rubber material colors for Cycles render engine."""

    node = __node_lego_rubber(nodes, diff_color, 0, 0)
    out = __node_output(nodes, 200, 0)
    links.new(node.outputs[0], out.inputs[0])


def __create_cycles_rubber_translucent(nodes, links, diff_color):
    """Translucent Rubber material colors for Cycles render engine."""

    node = __node_lego_rubber_translucent(nodes, diff_color, 0, 0)
    out = __node_output(nodes, 200, 0)
    links.new(node.outputs[0], out.inputs[0])


def __create_cycles_milky_white(nodes, links, diff_color):
    """Milky White material for Cycles render engine."""

    node = __node_lego_milky_white(nodes, diff_color, 0, 0)
    out = __node_output(nodes, 200, 0)
    links.new(node.outputs["Shader"], out.inputs[0])


def __create_blender_slope_texture_node_group():
    group_name = "LEGO Slope Bump"

    if group_name in bpy.data.node_groups:
        return

    node_group = bpy.data.node_groups.new(group_name, 'ShaderNodeTree')
    node_group.use_fake_user = True

    group_input = node_group.nodes.new("NodeGroupInput")
    group_input.location = (-530, 0)

    group_output = node_group.nodes.new("NodeGroupOutput")
    group_output.location = (300, 0)

    node_group.inputs.new("NodeSocketFloat", "Strength")
    node_group.inputs.new("NodeSocketVectorDirection", "Normal")

    node_group.inputs[0].default_value = options.slope_texture_strength

    node_group.outputs.new("NodeSocketVectorDirection", "Normal")

    node_texture_coordinate = __node_tex_coord(node_group.nodes, -300, 240)
    node_voronoi = __node_voronoi(node_group.nodes, 6.2, -100, 155)
    node_bump = __node_bump_shader(node_group.nodes, options.slope_texture_strength, 1.0, 90, 50)
    node_bump.invert = True

    node_group.links.new(node_texture_coordinate.outputs["Object"], node_voronoi.inputs["Vector"])
    node_group.links.new(node_voronoi.outputs["Distance"], node_bump.inputs["Height"])
    node_group.links.new(group_input.outputs["Strength"], node_bump.inputs["Strength"])
    node_group.links.new(group_input.outputs["Normal"], node_bump.inputs["Normal"])
    node_group.links.new(node_bump.outputs["Normal"], group_output.inputs["Normal"])


def __create_blender_lego_standard_node_group():
    group_name = "LEGO Standard"

    if group_name in bpy.data.node_groups:
        return

    node_group = bpy.data.node_groups.new(group_name, 'ShaderNodeTree')
    node_group.use_fake_user = True

    group_input = node_group.nodes.new("NodeGroupInput")
    group_input.location = (-250, 0)

    group_output = node_group.nodes.new("NodeGroupOutput")
    group_output.location = (250, 0)

    node_group.inputs.new("NodeSocketColor", "Color")
    node_group.inputs.new("NodeSocketFloatFactor", "Specular")
    node_group.inputs.new("NodeSocketVectorDirection", "Normal")

    node_group.inputs["Specular"].default_value = 0.5

    node_group.outputs.new("NodeSocketShader", "Shader")

    node_principled = __node_principled(node_group.nodes, 0.05, 0.05, 0.0, 0.1, 0.0, 0.0, 1.45, 0.0, 0, 0)

    node_group.links.new(group_input.outputs["Color"], node_principled.inputs["Base Color"])
    node_group.links.new(group_input.outputs["Specular"], node_principled.inputs["Specular"])
    if options.add_subsurface:
        node_group.links.new(group_input.outputs["Color"], node_principled.inputs["Subsurface Color"])
    node_group.links.new(group_input.outputs["Normal"], node_principled.inputs["Normal"])
    node_group.links.new(node_principled.outputs["BSDF"], group_output.inputs["Shader"])


def __create_blender_lego_transparent_node_group():
    group_name = "LEGO Transparent"

    if group_name in bpy.data.node_groups:
        return

    node_group = bpy.data.node_groups.new(group_name, 'ShaderNodeTree')
    node_group.use_fake_user = True

    group_input = node_group.nodes.new("NodeGroupInput")
    group_input.location = (-250, 0)

    group_output = node_group.nodes.new("NodeGroupOutput")
    group_output.location = (250, 0)

    node_group.inputs.new("NodeSocketColor", "Color")
    node_group.inputs.new("NodeSocketFloatFactor", "Specular")
    node_group.inputs.new("NodeSocketVectorDirection", "Normal")

    node_group.inputs["Specular"].default_value = 0.5

    node_group.outputs.new("NodeSocketShader", "Shader")

    node_principled = __node_principled(node_group.nodes, 0.0, 0.0, 0.0, 0.05, 0.0, 0.0, 1.585, 1.0, 45, 340)

    node_group.links.new(group_input.outputs["Color"], node_principled.inputs["Base Color"])
    node_group.links.new(group_input.outputs["Specular"], node_principled.inputs["Specular"])
    node_group.links.new(group_input.outputs["Normal"], node_principled.inputs["Normal"])
    node_group.links.new(node_principled.outputs["BSDF"], group_output.inputs["Shader"])


# https://blender.stackexchange.com/a/137791
# https://blenderartists.org/t/realistic-glass-in-eevee/1149937/19
def __create_blender_lego_glass_node_group():
    group_name = "LEGO Glass"

    if group_name in bpy.data.node_groups:
        return

    node_group = bpy.data.node_groups.new(group_name, 'ShaderNodeTree')
    node_group.use_fake_user = True

    group_input = node_group.nodes.new("NodeGroupInput")
    group_input.name = "group_input"
    group_input.location = (-1100.0, 0.0)

    group_output = node_group.nodes.new("NodeGroupOutput")
    group_output.name = "group_output"
    group_output.location = (0.0, 40.0)

    node_group.inputs.new("NodeSocketColor", "Color")
    node_group.inputs.new("NodeSocketFloatFactor", "Roughness")
    node_group.inputs.new("NodeSocketFloat", "IOR")
    node_group.inputs.new("NodeSocketVectorDirection", "Normal")

    node_group.inputs["Color"].default_value = (0.0, 0.0, 0.0, 1.0)
    node_group.inputs["Roughness"].default_value = 0.06
    node_group.inputs["IOR"].default_value = 1.58
    node_group.inputs["Normal"].default_value = (0.0, 0.0, 0.0)

    node_group.outputs.new("NodeSocketShader", "Shader")

    bsdf_glass = node_group.nodes.new("ShaderNodeBsdfGlass")
    bsdf_glass.name = "bsdf_glass"
    bsdf_glass.location = (-620.0, 40.0)
    bsdf_glass.inputs[1].default_value = 0.0
    bsdf_glass.inputs[2].default_value = 1.45

    bsdf_glossy = node_group.nodes.new("ShaderNodeBsdfGlossy")
    bsdf_glossy.name = "bsdf_glossy"
    bsdf_glossy.location = (-620.0, -260.0)
    bsdf_glossy.inputs[1].default_value = 0.5

    fresnel = node_group.nodes.new("ShaderNodeFresnel")
    fresnel.name = "fresnel"
    fresnel.location = (-900.0, 140.0)
    fresnel.inputs[0].default_value = 1.4

    bsdf_glossy_0 = node_group.nodes.new("ShaderNodeBsdfGlossy")
    bsdf_glossy_0.name = "bsdf_glossy_0"
    bsdf_glossy_0.location = (-400.0, -120.0)
    bsdf_glossy_0.inputs[1].default_value = 0.5

    rgb_curve = node_group.nodes.new("ShaderNodeRGBCurve")
    rgb_curve.name = "rgb_curve"
    rgb_curve.location = (-700.0, 420.0)
    rgb_curve.inputs[0].default_value = 0.5
    r = 0
    g = 1
    b = 2
    c = 3
    curves = rgb_curve.mapping.curves[c]
    curves.points.new(0.0000, 0.0000)
    curves.points.new(0.6227, 0.2438)
    curves.points.new(1.0000, 1.0000)

    mix = node_group.nodes.new("ShaderNodeMixShader")
    mix.name = "mix"
    mix.location = (-400.0, 40.0)
    mix.inputs[0].default_value = 0.25

    fresnel_0 = node_group.nodes.new("ShaderNodeFresnel")
    fresnel_0.name = "fresnel_0"
    fresnel_0.location = (-400.0, 180.0)
    fresnel_0.inputs[0].default_value = 1.4

    mix_0 = node_group.nodes.new("ShaderNodeMixShader")
    mix_0.name = "mix_0"
    mix_0.location = (-200.0, 40.0)
    mix_0.inputs[0].default_value = 0.5

    # color
    node_group.links.new(group_input.outputs["Color"], bsdf_glass.inputs[0])
    node_group.links.new(group_input.outputs["Color"], bsdf_glossy_0.inputs[0])

    # roughness
    node_group.links.new(group_input.outputs["Roughness"], bsdf_glass.inputs[1])
    node_group.links.new(group_input.outputs["Roughness"], bsdf_glossy.inputs[1])
    node_group.links.new(group_input.outputs["Roughness"], bsdf_glossy_0.inputs[1])

    # ior
    node_group.links.new(group_input.outputs["IOR"], bsdf_glass.inputs[2])
    node_group.links.new(group_input.outputs["IOR"], fresnel.inputs[0])
    node_group.links.new(group_input.outputs["IOR"], fresnel_0.inputs[0])

    # normal
    node_group.links.new(group_input.outputs["Normal"], bsdf_glass.inputs[3])

    node_group.links.new(bsdf_glass.outputs[0], mix.inputs[1])
    node_group.links.new(bsdf_glossy.outputs[0], mix.inputs[2])
    node_group.links.new(bsdf_glossy_0.outputs[0], mix_0.inputs[2])
    node_group.links.new(mix.outputs[0], mix_0.inputs[1])
    node_group.links.new(mix_0.outputs[0], group_output.inputs[0])
    node_group.links.new(fresnel.outputs[0], rgb_curve.inputs[1])
    node_group.links.new(rgb_curve.outputs[0], mix.inputs[0])
    node_group.links.new(fresnel_0.outputs[0], mix_0.inputs[0])


def __create_blender_lego_transparent_fluorescent_node_group():
    group_name = "LEGO Transparent Fluorescent"

    if group_name in bpy.data.node_groups:
        return

    node_group = bpy.data.node_groups.new(group_name, 'ShaderNodeTree')
    node_group.use_fake_user = True

    group_input = node_group.nodes.new("NodeGroupInput")
    group_input.location = (-160, 220)

    group_output = node_group.nodes.new("NodeGroupOutput")
    group_output.location = (250, 0)
    group_output.location = 540, 460

    node_group.inputs.new("NodeSocketColor", "Color")
    node_group.inputs.new("NodeSocketFloatFactor", "Specular")
    node_group.inputs.new("NodeSocketVectorDirection", "Normal")

    node_group.inputs["Specular"].default_value = 0.5

    node_group.outputs.new("NodeSocketShader", "Shader")

    node_principled = __node_principled(node_group.nodes, 0.0, 0.0, 0.0, 0.05, 0.0, 0.0, 1.585, 1.0, 45, 340)
    node_emission = __node_emission(node_group.nodes, 40, 460)
    node_mix = __node_mix(node_group.nodes, 0.03, 340, 460)

    node_group.links.new(group_input.outputs["Color"], node_principled.inputs["Base Color"])
    node_group.links.new(group_input.outputs["Color"], node_emission.inputs["Color"])
    node_group.links.new(group_input.outputs["Specular"], node_principled.inputs["Specular"])
    node_group.links.new(group_input.outputs["Normal"], node_principled.inputs["Normal"])
    node_group.links.new(node_principled.outputs["BSDF"], node_mix.inputs[1])
    node_group.links.new(node_emission.outputs["Emission"], node_mix.inputs[2])
    node_group.links.new(node_mix.outputs[0], group_output.inputs["Shader"])


def __create_blender_lego_rubber_node_group():
    group_name = "LEGO Rubber Solid"

    if group_name in bpy.data.node_groups:
        return

    node_group = bpy.data.node_groups.new(group_name, 'ShaderNodeTree')
    node_group.use_fake_user = True

    group_input = node_group.nodes.new("NodeGroupInput")
    group_input.location = (45 - 950, 340 - 50)

    group_output = node_group.nodes.new("NodeGroupOutput")
    group_output.location = (45 + 200, 340 - 5)

    node_group.inputs.new("NodeSocketColor", "Color")
    node_group.inputs.new("NodeSocketFloatFactor", "Specular")
    node_group.inputs["Specular"].default_value = 0.5
    node_group.inputs.new("NodeSocketVectorDirection", "Normal")

    node_group.outputs.new("NodeSocketShader", "Shader")

    node_noise = __node_noise_texture(node_group.nodes, 250, 2, 0.0, 45 - 770, 340 - 200)
    node_bump1 = __node_bump_shader(node_group.nodes, 1.0, 0.3, 45 - 366, 340 - 200)
    node_bump2 = __node_bump_shader(node_group.nodes, 1.0, 0.1, 45 - 184, 340 - 115)
    node_subtract = __node_math(node_group.nodes, 'SUBTRACT', 45 - 570, 340 - 216)
    node_principled = __node_principled(node_group.nodes, 0.0, 0.0, 0.0, 0.4, 0.03, 0.0, 1.45, 0.0, 45, 340)

    node_subtract.inputs[1].default_value = 0.4

    node_group.links.new(group_input.outputs["Color"], node_principled.inputs["Base Color"])
    node_group.links.new(node_principled.outputs["BSDF"], group_output.inputs[0])
    node_group.links.new(node_noise.outputs["Color"], node_subtract.inputs[0])
    node_group.links.new(node_subtract.outputs[0], node_bump1.inputs["Height"])
    node_group.links.new(node_bump1.outputs["Normal"], node_bump2.inputs["Normal"])
    node_group.links.new(node_bump2.outputs["Normal"], node_principled.inputs["Normal"])


def __create_blender_lego_rubber_translucent_node_group():
    group_name = "LEGO Rubber Translucent"

    if group_name in bpy.data.node_groups:
        return

    node_group = bpy.data.node_groups.new(group_name, 'ShaderNodeTree')
    node_group.use_fake_user = True

    group_input = node_group.nodes.new("NodeGroupInput")
    group_input.location = (-250, 0)
    group_input.location = -320, 290

    group_output = node_group.nodes.new("NodeGroupOutput")
    group_output.location = (250, 0)
    group_output.location = 530, 285

    node_group.inputs.new("NodeSocketColor", "Color")
    node_group.inputs.new("NodeSocketFloatFactor", "Specular")
    node_group.inputs["Specular"].default_value = 0.5
    node_group.inputs.new("NodeSocketVectorDirection", "Normal")

    node_group.outputs.new("NodeSocketShader", "Shader")

    node_noise = __node_noise_texture(node_group.nodes, 250, 2, 0.0, 45 - 770, 340 - 200)
    node_bump1 = __node_bump_shader(node_group.nodes, 1.0, 0.3, 45 - 366, 340 - 200)
    node_bump2 = __node_bump_shader(node_group.nodes, 1.0, 0.1, 45 - 184, 340 - 115)
    node_subtract = __node_math(node_group.nodes, 'SUBTRACT', 45 - 570, 340 - 216)
    node_principled = __node_principled(node_group.nodes, 0.0, 0.0, 0.0, 0.4, 0.03, 0.0, 1.45, 0.0, 45, 340)
    node_mix = __node_mix(node_group.nodes, 0.8, 300, 290)
    node_refraction = __node_refraction(node_group.nodes, 0.0, 1.45, 290 - 242, 154 - 330)

    node_subtract.inputs[1].default_value = 0.4

    node_group.links.new(group_input.outputs["Normal"], node_refraction.inputs["Normal"])
    node_group.links.new(node_refraction.outputs[0], node_mix.inputs[2])
    node_group.links.new(node_principled.outputs[0], node_mix.inputs[1])
    node_group.links.new(node_mix.outputs[0], group_output.inputs[0])
    node_group.links.new(group_input.outputs["Color"], node_principled.inputs["Base Color"])
    node_group.links.new(node_noise.outputs["Color"], node_subtract.inputs[0])
    node_group.links.new(node_subtract.outputs[0], node_bump1.inputs["Height"])
    node_group.links.new(node_bump1.outputs["Normal"], node_bump2.inputs["Normal"])
    node_group.links.new(node_bump2.outputs["Normal"], node_principled.inputs["Normal"])
    node_group.links.new(node_mix.outputs[0], group_output.inputs[0])


def __create_blender_lego_emission_node_group():
    group_name = "LEGO Emission"

    if group_name in bpy.data.node_groups:
        return

    node_group = bpy.data.node_groups.new(group_name, 'ShaderNodeTree')
    node_group.use_fake_user = True

    group_input = node_group.nodes.new("NodeGroupInput")
    group_input.location = (-450, 90)

    group_output = node_group.nodes.new("NodeGroupOutput")
    group_output.location = (250, 0)

    node_group.inputs.new("NodeSocketColor", "Color")
    node_group.inputs.new("NodeSocketFloatFactor", "Specular")
    node_group.inputs["Specular"].default_value = 0.5
    node_group.inputs.new("NodeSocketFloatFactor", "Luminance")
    node_group.inputs.new("NodeSocketVectorDirection", "Normal")

    node_group.outputs.new("NodeSocketShader", "Shader")

    node_emit = __node_emission(node_group.nodes, -242, -123)
    node_mix = __node_mix(node_group.nodes, 0.5, 0, 90)

    node_main = __node_principled(node_group.nodes, 1.0, 0.05, 0.0, 0.5, 0.0, 0.03, 1.45, 0.0, -242, 154 + 240)

    if options.add_subsurface:
        node_group.links.new(group_input.outputs["Color"], node_main.inputs["Subsurface Color"])
    node_group.links.new(group_input.outputs["Color"], node_emit.inputs["Color"])
    node_group.links.new(group_input.outputs["Color"], node_main.inputs["Base Color"])
    node_group.links.new(group_input.outputs["Normal"], node_main.inputs["Normal"])
    node_group.links.new(group_input.outputs["Luminance"], node_mix.inputs[0])
    node_group.links.new(node_main.outputs[0], node_mix.inputs[1])
    node_group.links.new(node_emit.outputs[0], node_mix.inputs[2])
    node_group.links.new(node_mix.outputs[0], group_output.inputs[0])


def __create_blender_lego_chrome_node_group():
    group_name = "LEGO Chrome"

    if group_name in bpy.data.node_groups:
        return

    node_group = bpy.data.node_groups.new(group_name, 'ShaderNodeTree')
    node_group.use_fake_user = True

    group_input = node_group.nodes.new("NodeGroupInput")
    group_input.location = (-450, 90)

    group_output = node_group.nodes.new("NodeGroupOutput")
    group_output.location = (250, 0)
    group_output.location = (575, -140)

    node_group.inputs.new("NodeSocketColor", "Color")
    node_group.inputs.new("NodeSocketFloatFactor", "Specular")
    node_group.inputs["Specular"].default_value = 0.5
    node_group.inputs.new("NodeSocketVectorDirection", "Normal")

    node_group.outputs.new("NodeSocketShader", "Shader")

    node_hsv = __node_hsv(node_group.nodes, 0.5, 0.9, 2.0, -90, 0)
    node_principled = __node_principled(node_group.nodes, 0.0, 0.0, 1.0, 0.0, 1.0, 0.0, 2.4, 0.0, 100, 0)

    node_group.links.new(group_input.outputs["Color"], node_hsv.inputs["Color"])
    node_group.links.new(group_input.outputs["Normal"], node_principled.inputs["Normal"])
    node_group.links.new(node_hsv.outputs["Color"], node_principled.inputs["Base Color"])
    node_group.links.new(node_principled.outputs["BSDF"], group_output.inputs[0])


def __create_blender_lego_pearlescent_node_group():
    group_name = "LEGO Pearlescent"

    if group_name in bpy.data.node_groups:
        return

    node_group = bpy.data.node_groups.new(group_name, 'ShaderNodeTree')
    node_group.use_fake_user = True

    group_input = node_group.nodes.new("NodeGroupInput")
    group_input.location = (-450, 90)

    group_output = node_group.nodes.new("NodeGroupOutput")
    group_output.location = (630, 95)

    node_group.inputs.new("NodeSocketColor", "Color")
    node_group.inputs.new("NodeSocketFloatFactor", "Specular")
    node_group.inputs["Specular"].default_value = 0.5
    node_group.inputs.new("NodeSocketVectorDirection", "Normal")

    node_group.outputs.new("NodeSocketShader", "Shader")

    node_principled = __node_principled(node_group.nodes, 1.0, 0.25, 0.5, 0.2, 1.0, 0.2, 1.6, 0.0, 310, 95)
    node_sep_hsv = __node_separate_hsv(node_group.nodes, -240, 75)
    node_multiply = __node_math(node_group.nodes, 'MULTIPLY', -60, 0)
    node_com_hsv = __node_combine_hsv(node_group.nodes, 110, 95)
    node_tex_coord = __node_tex_coord(node_group.nodes, -730, -223)
    node_tex_wave = __node_tex_wave(node_group.nodes, 'BANDS', 'SIN', 0.5, 40, 1, 1.5, -520, -190)
    node_color_ramp = __node_color_ramp(node_group.nodes, 0.329, (0.89, 0.89, 0.89, 1), 0.820, (1, 1, 1, 1), -340, -70)
    element = node_color_ramp.color_ramp.elements.new(1.0)
    element.color = (1.118, 1.118, 1.118, 1)

    node_group.links.new(group_input.outputs["Color"], node_sep_hsv.inputs["Color"])
    node_group.links.new(group_input.outputs["Normal"], node_principled.inputs["Normal"])
    node_group.links.new(node_sep_hsv.outputs["H"], node_com_hsv.inputs["H"])
    node_group.links.new(node_sep_hsv.outputs["S"], node_com_hsv.inputs["S"])
    node_group.links.new(node_sep_hsv.outputs["V"], node_multiply.inputs[0])
    node_group.links.new(node_com_hsv.outputs["Color"], node_principled.inputs["Base Color"])
    if options.add_subsurface:
        node_group.links.new(node_com_hsv.outputs["Color"], node_principled.inputs["Subsurface Color"])
    node_group.links.new(node_tex_coord.outputs["Object"], node_tex_wave.inputs["Vector"])
    node_group.links.new(node_tex_wave.outputs["Fac"], node_color_ramp.inputs["Fac"])
    node_group.links.new(node_color_ramp.outputs["Color"], node_multiply.inputs[1])
    node_group.links.new(node_multiply.outputs[0], node_com_hsv.inputs["V"])
    node_group.links.new(node_principled.outputs["BSDF"], group_output.inputs[0])


def __create_blender_lego_metal_node_group():
    group_name = "LEGO Metal"

    if group_name in bpy.data.node_groups:
        return

    node_group = bpy.data.node_groups.new(group_name, 'ShaderNodeTree')
    node_group.use_fake_user = True

    group_input = node_group.nodes.new("NodeGroupInput")
    group_input.location = (-450, 90)

    group_output = node_group.nodes.new("NodeGroupOutput")
    group_output.location = (250, 0)

    node_group.inputs.new("NodeSocketColor", "Color")
    node_group.inputs.new("NodeSocketFloatFactor", "Specular")
    node_group.inputs["Specular"].default_value = 0.5
    node_group.inputs.new("NodeSocketVectorDirection", "Normal")

    node_group.outputs.new("NodeSocketShader", "Shader")

    node_principled = __node_principled(node_group.nodes, 0.0, 0.0, 0.8, 0.2, 0.0, 0.03, 1.45, 0.0, 310, 95)

    node_group.links.new(group_input.outputs["Color"], node_principled.inputs["Base Color"])
    node_group.links.new(group_input.outputs["Normal"], node_principled.inputs["Normal"])
    node_group.links.new(node_principled.outputs[0], group_output.inputs["Shader"])


def __create_blender_lego_glitter_node_group():
    group_name = "LEGO Glitter"

    if group_name in bpy.data.node_groups:
        return

    node_group = bpy.data.node_groups.new(group_name, 'ShaderNodeTree')
    node_group.use_fake_user = True

    group_input = node_group.nodes.new("NodeGroupInput")
    group_input.location = (-450, 0)

    group_output = node_group.nodes.new("NodeGroupOutput")
    group_output.location = (410, 0)

    node_group.inputs.new("NodeSocketColor", "Color")
    node_group.inputs.new("NodeSocketFloatFactor", "Specular")
    node_group.inputs["Specular"].default_value = 0.5
    node_group.inputs.new("NodeSocketColor", "Glitter Color")
    node_group.inputs.new("NodeSocketVectorDirection", "Normal")

    node_group.outputs.new("NodeSocketShader", "Shader")

    node_voronoi = __node_voronoi(node_group.nodes, 100, -222, 310)
    node_gamma = __node_gamma(node_group.nodes, 50, 0, 200)
    node_mix = __node_mix(node_group.nodes, 0.05, 210, 90 + 25)
    node_principled1 = __node_principled(node_group.nodes, 0.0, 0.0, 0.0, 0.2, 0.0, 0.03, 1.585, 1.0, 45 - 270, 340 - 210)
    node_principled2 = __node_principled(node_group.nodes, 0.0, 0.0, 0.0, 0.5, 0.0, 0.03, 1.45, 0.0, 45 - 270, 340 - 750)

    node_group.links.new(group_input.outputs["Color"], node_principled1.inputs["Base Color"])
    node_group.links.new(group_input.outputs["Glitter Color"], node_principled2.inputs["Base Color"])
    node_group.links.new(group_input.outputs["Normal"], node_principled1.inputs["Normal"])
    node_group.links.new(group_input.outputs["Normal"], node_principled2.inputs["Normal"])
    node_group.links.new(node_voronoi.outputs["Color"], node_gamma.inputs["Color"])
    node_group.links.new(node_gamma.outputs[0], node_mix.inputs[0])
    node_group.links.new(node_principled1.outputs["BSDF"], node_mix.inputs[1])
    node_group.links.new(node_principled2.outputs["BSDF"], node_mix.inputs[2])
    node_group.links.new(node_mix.outputs[0], group_output.inputs[0])


def __create_blender_lego_speckle_node_group():
    group_name = "LEGO Speckle"

    if group_name in bpy.data.node_groups:
        return

    node_group = bpy.data.node_groups.new(group_name, 'ShaderNodeTree')
    node_group.use_fake_user = True

    group_input = node_group.nodes.new("NodeGroupInput")
    group_input.location = (-450, 0)

    group_output = node_group.nodes.new("NodeGroupOutput")
    group_output.location = (410, 0)

    node_group.inputs.new("NodeSocketColor", "Color")
    node_group.inputs.new("NodeSocketFloatFactor", "Specular")
    node_group.inputs["Specular"].default_value = 0.5
    node_group.inputs.new("NodeSocketColor", "Speckle Color")
    node_group.inputs.new("NodeSocketVectorDirection", "Normal")

    node_group.outputs.new("NodeSocketShader", "Shader")

    node_voronoi = __node_voronoi(node_group.nodes, 50, -222, 310)
    node_gamma = __node_gamma(node_group.nodes, 3.5, 0, 200)
    node_mix = __node_mix(node_group.nodes, 0.05, 210, 90 + 25)
    node_principled1 = __node_principled(node_group.nodes, 0.0, 0.0, 0.0, 0.1, 0.0, 0.03, 1.45, 0.0, 45 - 270, 340 - 210)
    node_principled2 = __node_principled(node_group.nodes, 0.0, 0.0, 1.0, 0.5, 0.0, 0.03, 1.45, 0.0, 45 - 270, 340 - 750)

    node_group.links.new(group_input.outputs["Color"], node_principled1.inputs["Base Color"])
    node_group.links.new(group_input.outputs["Speckle Color"], node_principled2.inputs["Base Color"])
    node_group.links.new(group_input.outputs["Normal"], node_principled1.inputs["Normal"])
    node_group.links.new(group_input.outputs["Normal"], node_principled2.inputs["Normal"])
    node_group.links.new(node_voronoi.outputs["Color"], node_gamma.inputs["Color"])
    node_group.links.new(node_gamma.outputs[0], node_mix.inputs[0])
    node_group.links.new(node_principled1.outputs["BSDF"], node_mix.inputs[1])
    node_group.links.new(node_principled2.outputs["BSDF"], node_mix.inputs[2])
    node_group.links.new(node_mix.outputs[0], group_output.inputs[0])


def __create_blender_lego_milky_white_node_group():
    group_name = "LEGO Milky White"

    if group_name in bpy.data.node_groups:
        return

    node_group = bpy.data.node_groups.new(group_name, 'ShaderNodeTree')
    node_group.use_fake_user = True

    group_input = node_group.nodes.new("NodeGroupInput")
    group_input.location = (-450, 0)

    group_output = node_group.nodes.new("NodeGroupOutput")
    group_output.location = (350, 0)

    node_group.inputs.new("NodeSocketColor", "Color")
    node_group.inputs.new("NodeSocketFloatFactor", "Specular")
    node_group.inputs["Specular"].default_value = 0.5
    node_group.inputs.new("NodeSocketVectorDirection", "Normal")

    node_group.outputs.new("NodeSocketShader", "Shader")

    node_principled = __node_principled(node_group.nodes, 1.0, 0.05, 0.0, 0.5, 0.0, 0.03, 1.45, 0.0, 45 - 270, 340 - 210)
    node_translucent = __node_translucent(node_group.nodes, -225, -382)
    node_mix = __node_mix(node_group.nodes, 0.5, 65, -40)

    node_group.links.new(group_input.outputs["Color"], node_principled.inputs["Base Color"])
    if options.add_subsurface:
        node_group.links.new(group_input.outputs["Color"], node_principled.inputs["Subsurface Color"])
    node_group.links.new(group_input.outputs["Normal"], node_principled.inputs["Normal"])
    node_group.links.new(group_input.outputs["Normal"], node_translucent.inputs["Normal"])
    node_group.links.new(node_principled.outputs[0], node_mix.inputs[1])
    node_group.links.new(node_translucent.outputs[0], node_mix.inputs[2])
    node_group.links.new(node_mix.outputs[0], group_output.inputs[0])
