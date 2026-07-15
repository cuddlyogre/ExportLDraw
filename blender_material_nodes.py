import bpy


def create_node_based_material(name, use_backface_culling=True):
    material = bpy.data.materials.new(name)
    material.use_fake_user = True
    material.use_nodes = True
    material.use_backface_culling = use_backface_culling

    nodes = material.node_tree.nodes
    links = material.node_tree.links

    nodes.clear()

    return material


def node_tex_image_closest_repeat(nodes, x, y, image_name):
    node = nodes.new("ShaderNodeTexImage")
    node.select = False
    node.location = x, y
    node.name = image_name
    node.interpolation = "Closest"
    node.extension = "REPEAT"

    if image_name is not None:
        image = bpy.data.images.get(image_name)
        if image is not None:
            node.image = image

    return node


def node_tex_image_closest_clip(nodes, x, y, image_name):
    node = nodes.new("ShaderNodeTexImage")
    node.location = x, y
    node.select = False
    node.name = image_name
    node.interpolation = "Closest"
    node.extension = "CLIP"

    if image_name is not None:
        image = bpy.data.images.get(image_name)
        if image is not None:
            node.image = image

    return node


def node_principled(nodes, x, y):
    node = nodes.new("ShaderNodeBsdfPrincipled")
    node.select = False
    node.location = x, y
    return node


def node_value(nodes, x, y):
    node = nodes.new("ShaderNodeValue")
    node.select = False
    node.location = x, y
    return node


def node_map_range(nodes, x, y):
    node = nodes.new("ShaderNodeMapRange")
    node.select = False
    node.location = x, y
    return node


def node_output_material(nodes, x, y):
    node = nodes.new("ShaderNodeOutputMaterial")
    node.select = False
    node.location = x, y
    return node


def node_frame(nodes, x, y):
    node = nodes.new("NodeFrame")
    node.select = False
    node.location = x, y
    return node


def node_separate_hsv(nodes, x, y):
    node = nodes.new("ShaderNodeSeparateColor")
    node.select = False
    node.location = x, y
    node.mode = "HSV"
    return node


def node_combine_hsv(nodes, x, y):
    node = nodes.new("ShaderNodeCombineColor")
    node.select = False
    node.location = x, y
    node.mode = "HSV"
    return node


def node_rgb(nodes, x, y):
    node = nodes.new("ShaderNodeRGB")
    node.select = False
    node.location = x, y
    return node


def node_mix_rgb(nodes, x, y):
    node = nodes.new("ShaderNodeMix")
    node.select = False
    node.location = x, y
    node.data_type = "RGBA"
    node.blend_type = "MIX"
    return node


def node_add_rgb(nodes, x, y):
    node = nodes.new("ShaderNodeMix")
    node.select = False
    node.location = x, y
    node.data_type = "RGBA"
    node.blend_type = "ADD"
    return node


def node_hsv(nodes, x, y):
    node = nodes.new("ShaderNodeHueSaturation")
    node.select = False
    node.location = x, y
    return node


def node_texture_coordinate(nodes, x, y):
    node = nodes.new("ShaderNodeTexCoord")
    node.select = False
    node.location = x, y
    return node


def node_mapping(nodes, x, y):
    node = nodes.new("ShaderNodeMapping")
    node.select = False
    node.location = x, y
    return node


def node_tex_voronoi(nodes, x, y):
    node = nodes.new("ShaderNodeTexVoronoi")
    node.select = False
    node.location = x, y
    return node


def node_tex_noise(nodes, x, y):
    node = nodes.new("ShaderNodeTexNoise")
    node.select = False
    node.location = x, y
    return node


def node_color_ramp(nodes, x, y):
    node = nodes.new("ShaderNodeValToRGB")
    node.select = False
    node.location = x, y
    return node


def node_bump(nodes, x, y):
    node = nodes.new("ShaderNodeBump")
    node.select = False
    node.location = x, y
    return node


def node_separate_xyz(nodes, x, y):
    node = nodes.new("ShaderNodeSeparateXYZ")
    node.select = False
    node.location = x, y
    return node


def node_math_add(nodes, x, y):
    node = nodes.new("ShaderNodeMath")
    node.select = False
    node.location = x, y
    node.operation = 'ADD'
    return node


def node_math_multiply(nodes, x, y):
    node = nodes.new("ShaderNodeMath")
    node.select = False
    node.location = x, y
    node.operation = "MULTIPLY"
    return node


def node_maximum(nodes, x, y):
    node = nodes.new("ShaderNodeMath")
    node.select = False
    node.location = x, y
    node.operation = "MAXIMUM"
    return node


def node_vector_math_normalize(nodes, x, y):
    node = nodes.new("ShaderNodeVectorMath")
    node.select = False
    node.location = x, y
    node.operation = "NORMALIZE"
    return node


def node_math_maximum(nodes, x, y):
    node = nodes.new("ShaderNodeMath")
    node.select = False
    node.location = x, y
    node.operation = "MAXIMUM"
    return node


def node_math_minimum(nodes, x, y):
    node = nodes.new("ShaderNodeMath")
    node.select = False
    node.location = x, y
    node.operation = "MINIMUM"
    return node


def node_math_arccosine(nodes, x, y):
    node = nodes.new("ShaderNodeMath")
    node.select = False
    node.location = x, y
    node.operation = "ARCCOSINE"
    return node


def node_math_to_degrees(nodes, x, y):
    node = nodes.new("ShaderNodeMath")
    node.select = False
    node.location = x, y
    node.operation = 'DEGREES'
    return node


def node_math_compare(nodes, x, y):
    node = nodes.new("ShaderNodeMath")
    node.select = False
    node.location = x, y
    node.operation = 'COMPARE'
    return node


def node_math_absolute(nodes, x, y):
    node = nodes.new("ShaderNodeMath")
    node.select = False
    node.location = x, y
    node.operation = 'ABSOLUTE'
    return node


def node_math_greater_than(nodes, x, y):
    node = nodes.new("ShaderNodeMath")
    node.select = False
    node.location = x, y
    node.operation = 'GREATER_THAN'
    return node

# 'GREATER_THAN'
# 'ABSOLUTE'
# 'MULTIPLY'
# 'MINIMUM'
# 'NORMALIZE'
# 'DEGREES'
# 'MAXIMUM'
# 'ARCCOSINE'
# 'COMPARE'
# 'ADD'
