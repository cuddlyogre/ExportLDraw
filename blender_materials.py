import bpy
import os
import uuid

from .definitions import APP_ROOT
from .ldraw_colors import LDrawColor
from .filesystem import FileSystem
from . import strings


class BlenderMaterials:
    __key_map = {}

    @classmethod
    def reset_caches(cls):
        cls.__key_map = {}

    # https://github.com/bblanimation/abs-plastic-materials
    @classmethod
    def create_blender_node_groups(cls):
        cls.reset_caches()
        path = os.path.join(APP_ROOT, 'materials', 'all_monkeys.blend')
        with bpy.data.libraries.load(path, link=False) as (data_from, data_to):
            all_node_groups = False
            if all_node_groups:
                data_to.node_groups = data_from.node_groups
            else:
                data_to.node_groups = [c for c in data_from.node_groups if c.startswith("_") or c.startswith("LEGO")]
        for node_group in data_to.node_groups:
            node_group.use_fake_user = True

    @classmethod
    def get_material(cls, color_code, use_edge_color=False, part_slopes=None, parts_cloth=False, texmap=None, pe_texmap=None, use_backface_culling=True, easy_key=False):
        color = LDrawColor.get_color(color_code)
        use_backface_culling = use_backface_culling is True

        if easy_key:
            key = color_code
        else:
            key = cls.__build_key(color, use_edge_color, part_slopes, parts_cloth, texmap, pe_texmap, use_backface_culling)

        # Reuse current material if it exists, otherwise create a new material
        material = bpy.data.materials.get(key)
        if material is not None:
            return material

        material = cls.__create_node_based_material(
            key,
            color,
            use_edge_color=use_edge_color,
            part_slopes=part_slopes,
            parts_cloth=parts_cloth,
            texmap=texmap,
            pe_texmap=pe_texmap,
            use_backface_culling=use_backface_culling,
        )
        return material

    @classmethod
    def __build_key(cls, color, use_edge_color, part_slopes, parts_cloth, texmap, pe_texmap, use_backface_culling):
        _key = (color.name, color.code, use_backface_culling,)

        if LDrawColor.use_alt_colors:
            _key += ("alt",)
        if use_edge_color:
            _key += ("edge",)
        if part_slopes is not None:
            _key += (part_slopes,)
        if parts_cloth:
            _key += ("cloth",)
        if texmap is not None:
            _key += (texmap.method, texmap.texture, texmap.glossmap,)
        if pe_texmap is not None:
            _key += (pe_texmap.texture,)

        key = cls.__key_map.get(_key)
        if key is None:
            cls.__key_map[_key] = str(uuid.uuid4())
            key = cls.__key_map.get(_key)

        return key

    @classmethod
    def __create_node_based_material(cls, key, color, use_edge_color=False, part_slopes=None, parts_cloth=False, texmap=None, pe_texmap=None, use_backface_culling=True):
        material = bpy.data.materials.new(key)
        material.use_fake_user = True
        material.use_nodes = True
        material.use_backface_culling = use_backface_culling

        nodes = material.node_tree.nodes
        links = material.node_tree.links

        nodes.clear()

        out = cls.__node_output_material(nodes, 200, 0)

        new_way = True  # slower but color codes are encompassed in their own node groups
        new_way = False  # faster but color codes are directly created within the material
        if new_way:
            group_name = cls.__node_group_color_code(color, 200, 0, use_edge_color)
            node = cls.__node_group(group_name, nodes, 0, 0)
        else:
            node, rgb_node, mix_rgb_node = cls.__node_group_color_code_old(color, nodes, links, 200, 0, use_edge_color)
        links.new(node.outputs["Shader"], out.inputs["Surface"])

        # https://wiki.ldraw.org/wiki/Color_24
        if use_edge_color:
            diff_color = color.edge_color_d
            material.diffuse_color = diff_color
            material[strings.ldraw_color_code_key] = "24"
            material[strings.ldraw_color_name_key] = color.name
        else:
            diff_color = color.color_d
            material.diffuse_color = diff_color
            material[strings.ldraw_color_code_key] = color.code
            material[strings.ldraw_color_name_key] = color.name

            is_transparent = color.alpha < 1.0
            if is_transparent:
                material.use_screen_refraction = True
                material.refraction_depth = 0.5

            if part_slopes is not None and len(part_slopes) > 0:
                cls.__create_slope(nodes, links, node, -200, -220, part_slopes)

            if texmap is not None or pe_texmap is not None:
                if new_way:
                    cls.__create_texmap(nodes, links, -460, 180, texmap, pe_texmap, node.inputs["Texture Color"], node.inputs["Texture Alpha"], node.inputs["Specular"])
                else:
                    cls.__create_texmap(nodes, links, -500, -140, texmap, pe_texmap, mix_rgb_node.inputs["Color2"], mix_rgb_node.inputs["Fac"], node.inputs["Specular"])

            if parts_cloth:
                cls.__create_cloth(nodes, links, node, -200, -100)

        return material

    @classmethod
    def __node_output_material(cls, nodes, x, y):
        node = nodes.new("ShaderNodeOutputMaterial")
        node.location = x, y
        return node

    @classmethod
    def __node_tree(cls, group_name, use_fake_user=True):
        node = bpy.data.node_groups.new(group_name, "ShaderNodeTree")
        node.use_fake_user = use_fake_user
        return node

    @classmethod
    def __node_group(cls, group_name, nodes, x, y):
        node = nodes.new("ShaderNodeGroup")
        node.node_tree = bpy.data.node_groups[group_name]
        node.name = node.node_tree.name
        node.location = x, y
        return node

    @classmethod
    def __node_group_input(cls, nodes, x, y):
        node = nodes.new("NodeGroupInput")
        node.location = x, y
        return node

    @classmethod
    def __node_group_output(cls, nodes, x, y):
        node = nodes.new("NodeGroupOutput")
        node.location = x, y
        return node

    @classmethod
    def __node_rgb(cls, nodes, x, y):
        node = nodes.new("ShaderNodeRGB")
        node.location = x, y
        return node

    @classmethod
    def __node_mix_rgb(cls, nodes, x, y):
        node = nodes.new("ShaderNodeMixRGB")
        node.location = x, y
        return node

    @classmethod
    def __node_group_color_code_old(cls, color, nodes, links, x, y, use_edge_color=False):
        if use_edge_color:
            diff_color = color.edge_color_d
        else:
            diff_color = color.color_d
        rgb_node = cls.__node_rgb(nodes, x + -600, y + 60)
        rgb_node.outputs["Color"].default_value = diff_color

        mix_rgb_node = cls.__node_mix_rgb(nodes, x + -400, y + 0)
        mix_rgb_node.inputs["Fac"].default_value = 0

        node = cls.__node_color_code_material(nodes, color, x + -200, y + 0, use_edge_color)

        links.new(rgb_node.outputs["Color"], mix_rgb_node.inputs["Color1"])
        links.new(mix_rgb_node.outputs["Color"], node.inputs["Color"])

        return node, rgb_node, mix_rgb_node

    @classmethod
    def __node_group_color_code(cls, color, x, y, use_edge_color=False):
        group_name = color.code
        if group_name not in bpy.data.node_groups:
            node_group = cls.__node_tree(group_name)

            node_tree_input = cls.__node_group_input(node_group.nodes, x + -600, y + -200)
            node_tree_output = cls.__node_group_output(node_group.nodes, x, y)

            node_group.inputs.new("NodeSocketColor", "Texture Color")

            node_group.inputs.new("NodeSocketFloatFactor", "Texture Alpha")
            node_group.inputs["Texture Alpha"].default_value = 0.0
            node_group.inputs["Texture Alpha"].min_value = 0.0
            node_group.inputs["Texture Alpha"].max_value = 1.0

            node_group.inputs.new("NodeSocketFloatFactor", "Specular")
            node_group.inputs["Specular"].default_value = 0.5
            node_group.inputs["Specular"].min_value = 0.0
            node_group.inputs["Specular"].max_value = 1.0

            node_group.inputs.new("NodeSocketVectorDirection", "Normal")
            node_group.inputs["Normal"].min_value = 0.0
            node_group.inputs["Normal"].max_value = 1.0

            node_group.outputs.new("NodeSocketShader", "Shader")

            if use_edge_color:
                diff_color = color.edge_color_d
            else:
                diff_color = color.color_d
            rgb_node = cls.__node_rgb(node_group.nodes, x + -600, y + 60)
            rgb_node.outputs["Color"].default_value = diff_color

            mix_rgb_node = cls.__node_mix_rgb(node_group.nodes, x + -400, y + 0)
            mix_rgb_node.inputs["Fac"].default_value = 0

            color_code_node = cls.__node_color_code_material(node_group.nodes, color, x + -200, y + 0, use_edge_color)

            node_group.links.new(rgb_node.outputs["Color"], mix_rgb_node.inputs["Color1"])
            node_group.links.new(node_tree_input.outputs["Texture Color"], mix_rgb_node.inputs["Color2"])
            node_group.links.new(node_tree_input.outputs["Texture Alpha"], mix_rgb_node.inputs["Fac"])
            node_group.links.new(mix_rgb_node.outputs["Color"], color_code_node.inputs["Color"])
            node_group.links.new(node_tree_input.outputs["Specular"], color_code_node.inputs["Specular"])
            node_group.links.new(node_tree_input.outputs["Normal"], color_code_node.inputs["Normal"])
            node_group.links.new(color_code_node.outputs["Shader"], node_tree_output.inputs["Shader"])

            group_name = node_group.name
        return group_name

    @classmethod
    def __node_color_code_material(cls, nodes, color, x, y, use_edge_color=False):
        if use_edge_color:
            is_transparent = False
        else:
            is_transparent = color.alpha < 1.0

        if color.name == "Milky_White":
            node = cls.__node_lego_milky_white(nodes, x, y)
        elif "Opal" in color.name:
            material_color = color.material_color + (1.0,)
            glitter_color = LDrawColor.lighten_rgba(material_color, 0.5)
            node = cls.__node_lego_opal(nodes, glitter_color, x, y)
        elif color.material_name == "glitter":
            material_color = color.material_color + (1.0,)
            glitter_color = LDrawColor.lighten_rgba(material_color, 0.5)
            node = cls.__node_lego_glitter(nodes, glitter_color, x, y)
        elif color.material_name == "speckle":
            material_color = color.material_color + (1.0,)
            speckle_color = LDrawColor.lighten_rgba(material_color, 0.5)
            node = cls.__node_lego_speckle(nodes, speckle_color, x, y)
        elif color.luminance > 0:
            luminance = color.luminance / 100.0
            node = cls.__node_lego_emission(nodes, luminance, x, y)
        elif color.material_name == "chrome":
            node = cls.__node_lego_chrome(nodes, x, y)
        elif color.material_name == "pearlescent":
            node = cls.__node_lego_pearlescent(nodes, x, y)
        elif color.material_name == "metal":
            node = cls.__node_lego_metal(nodes, x, y)
        elif color.material_name == "rubber":
            if is_transparent:
                node = cls.__node_lego_rubber_translucent(nodes, x, y)
            else:
                node = cls.__node_lego_rubber(nodes, x, y)
        elif is_transparent:
            node = cls.__node_lego_transparent(nodes, x, y)
        else:
            node = cls.__node_lego_standard(nodes, x, y)

        return node

    @classmethod
    # TODO: slight variation in strength for each material
    def __create_slope(cls, nodes, links, node, x, y, part_slopes=None):
        slope_texture = cls.__node_slope_texture_by_angle(nodes, x, y, part_slopes)
        links.new(slope_texture.outputs["Normal"], node.inputs["Normal"])

    @classmethod
    def __node_slope_texture_by_angle(cls, nodes, x, y, angles):
        group_name = "_Slope Texture By Angle"
        node = cls.__node_group(group_name, nodes, x, y)
        if len(angles) > 0:
            node.inputs["Angle 1"].default_value = angles[0]
        if len(angles) > 1:
            node.inputs["Angle 2"].default_value = angles[1]
        if len(angles) > 2:
            node.inputs["Angle 3"].default_value = angles[2]
        if len(angles) > 3:
            node.inputs["Angle 4"].default_value = angles[3]
        node.inputs["Strength"].default_value = 0.6
        return node

    @classmethod
    def __create_texmap(cls, nodes, links, x, y, texmap, pe_texmap, color_input, alpha_input, specular_input):
        image_name = None
        if texmap is not None:
            image_name = texmap.texture
        elif pe_texmap is not None:
            image_name = pe_texmap.texture
        if image_name is not None:
            texmap_image = cls.__node_tex_image_closest_clip(nodes, x, y, image_name, "sRGB")
            links.new(texmap_image.outputs["Color"], color_input)
            links.new(texmap_image.outputs["Alpha"], alpha_input)

        image_name = None
        if texmap is not None:
            image_name = texmap.glossmap
        if image_name is not None:
            glossmap_image = cls.__node_tex_image_closest_clip(nodes, x, y - 280, image_name, "Non-Color")
            links.new(glossmap_image.outputs["Color"], specular_input)

    @staticmethod
    def __node_tex_image_closest_clip(nodes, x, y, image_name, colorspace):
        node = nodes.new("ShaderNodeTexImage")
        node.location = x, y
        node.name = image_name
        node.interpolation = "Closest"
        node.extension = "CLIP"

        # TODO: requests retrieve image from ldraw.org
        # https://blender.stackexchange.com/questions/157531/blender-2-8-python-add-texture-image
        image = bpy.data.images.get(image_name)
        if image is None:
            image_path = FileSystem.locate(image_name)
            if image_path is not None:
                image = bpy.data.images.load(image_path)
                image.name = image_name
                image[strings.ldraw_filename_key] = image_name
                image.colorspace_settings.name = colorspace
                image.pack()

        image = bpy.data.images.get(image_name)
        if image_name is not None:
            node.image = image

        return node

    @classmethod
    def __create_cloth(cls, nodes, links, node, x, y):
        cloth = cls.__node_cloth(nodes, x, y)
        links.new(cloth.outputs["Normal"], node.inputs["Normal"])
        links.new(cloth.outputs["Specular"], node.inputs["Specular"])

    @classmethod
    def __node_cloth(cls, nodes, x, y):
        group_name = "_cloth"
        node = cls.__node_group(group_name, nodes, x, y)
        return node

    @classmethod
    def __node_lego_standard(cls, nodes, x, y):
        group_name = "LEGO Standard"
        node = cls.__node_group(group_name, nodes, x, y)
        return node

    @classmethod
    def __node_lego_transparent(cls, nodes, x, y):
        group_name = "LEGO Transparent"
        node = cls.__node_group(group_name, nodes, x, y)
        return node

    @classmethod
    def __node_lego_rubber(cls, nodes, x, y):
        group_name = "LEGO Rubber Solid"
        node = cls.__node_group(group_name, nodes, x, y)
        return node

    @classmethod
    def __node_lego_rubber_translucent(cls, nodes, x, y):
        group_name = "LEGO Rubber Translucent"
        node = cls.__node_group(group_name, nodes, x, y)
        return node

    @classmethod
    def __node_lego_emission(cls, nodes, luminance, x, y):
        group_name = "LEGO Emission"
        node = cls.__node_group(group_name, nodes, x, y)
        node.inputs["Luminance"].default_value = luminance
        return node

    @classmethod
    def __node_lego_chrome(cls, nodes, x, y):
        group_name = "LEGO Chrome"
        node = cls.__node_group(group_name, nodes, x, y)
        return node

    @classmethod
    def __node_lego_pearlescent(cls, nodes, x, y):
        group_name = "LEGO Pearlescent"
        node = cls.__node_group(group_name, nodes, x, y)
        return node

    @classmethod
    def __node_lego_metal(cls, nodes, x, y):
        group_name = "LEGO Metal"
        node = cls.__node_group(group_name, nodes, x, y)
        return node

    @classmethod
    def __node_lego_opal(cls, nodes, glitter_color, x, y):
        group_name = "LEGO Opal"
        node = cls.__node_group(group_name, nodes, x, y)
        node.inputs["Glitter Color"].default_value = glitter_color
        return node

    @classmethod
    def __node_lego_glitter(cls, nodes, glitter_color, x, y):
        group_name = "LEGO Glitter"
        node = cls.__node_group(group_name, nodes, x, y)
        node.inputs["Glitter Color"].default_value = glitter_color
        return node

    @classmethod
    def __node_lego_speckle(cls, nodes, speckle_color, x, y):
        group_name = "LEGO Speckle"
        node = cls.__node_group(group_name, nodes, x, y)
        node.inputs["Speckle Color"].default_value = speckle_color
        return node

    @classmethod
    def __node_lego_milky_white(cls, nodes, x, y):
        group_name = "LEGO Milky White"
        node = cls.__node_group(group_name, nodes, x, y)
        return node
