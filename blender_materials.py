import bpy

import os
import uuid

from .definitions import APP_ROOT
from .ldraw_color import LDrawColor
from .filesystem import FileSystem
from . import strings


class BlenderMaterials:
    __key_map = {}

    @classmethod
    def reset_caches(cls):
        cls.__key_map.clear()

    # https://github.com/bblanimation/abs-plastic-materials
    @classmethod
    def create_blender_node_groups(cls):
        path = os.path.join(APP_ROOT, 'materials', 'all_monkeys.blend')
        if bpy.app.version < (3, 4):
            path = os.path.join(APP_ROOT, 'materials', 'all_monkeys_33.blend')
        elif bpy.app.version < (4,):
            path = os.path.join(APP_ROOT, 'materials', 'all_monkeys_36.blend')

        with bpy.data.libraries.load(path) as (data_from, data_to):
            all_node_groups = False
            if all_node_groups:
                data_to.node_groups = data_from.node_groups
            else:
                do_delete = False
                if do_delete:  # deleting them will cause materials that use those nodes to render solid black
                    data_to.node_groups = []
                    for c in data_from.node_groups:
                        existing_node_group = bpy.data.node_groups.get(c)
                        if existing_node_group is not None:
                            bpy.data.node_groups.remove(existing_node_group)
                        if c.startswith("_") or c.startswith("LEGO"):
                            data_to.node_groups.append(c)
                else:  # don't import the node group again if there is already one that exists with that name
                    data_to.node_groups = [c for c in data_from.node_groups if bpy.data.node_groups.get(c) is None and (c.startswith("_") or c.startswith("LEGO"))]
        for node_group in data_to.node_groups:
            node_group.use_fake_user = True

    @classmethod
    def get_material(cls, color_code, bfc_certified=True, part_slopes=None, parts_cloth=False, texmap=None, pe_texmap=None, easy_key=False):
        color = LDrawColor.get_color(color_code)
        bfc_certified = bfc_certified is True

        if easy_key:
            key = color_code
        else:
            key = cls.__build_key(color, bfc_certified, part_slopes, parts_cloth, texmap, pe_texmap)

        # Reuse current material if it exists, otherwise create a new material
        material = bpy.data.materials.get(key)
        if material is not None:
            return material

        material = cls.__create_node_based_material(
            key,
            color,
            bfc_certified=bfc_certified,
            part_slopes=part_slopes,
            parts_cloth=parts_cloth,
            texmap=texmap,
            pe_texmap=pe_texmap,
        )
        return material

    @classmethod
    def __build_key(cls, color, bfc_certified, part_slopes, parts_cloth, texmap, pe_texmap):
        _key = ()

        _key += (color.name, color.code,)

        _key += (bfc_certified,)

        _key += (LDrawColor.use_alt_colors,)

        if part_slopes is not None:
            _key += (part_slopes,)

        if parts_cloth:
            _key += ("cloth",)

        if texmap is not None:
            _key += (texmap.method, texmap.texture, texmap.glossmap,)

        if pe_texmap is not None:
            _key += (pe_texmap.texture,)

        str_key = str(_key)
        if len(str_key) < 60:
            return str(str_key)

        key = cls.__key_map.get(_key)
        if key is None:
            cls.__key_map[_key] = str(uuid.uuid4())
            key = cls.__key_map.get(_key)

        return key

    @classmethod
    def __create_node_based_material(cls, key, color, bfc_certified=True, part_slopes=None, parts_cloth=False, texmap=None, pe_texmap=None):
        material = bpy.data.materials.new(key)
        material.use_fake_user = True
        material.use_nodes = True
        material.use_backface_culling = bfc_certified

        nodes = material.node_tree.nodes
        links = material.node_tree.links

        nodes.clear()

        out = cls.__node_output_material(nodes, 200, 0)

        node, rgb_node, mix_rgb_node = cls.__node_group_color_code(color, nodes, links, 200, 0)
        diff_color = color.linear_color_a
        material.diffuse_color = diff_color
        material[strings.ldraw_color_code_key] = color.code
        material[strings.ldraw_color_name_key] = color.name

        links.new(node.outputs["Shader"], out.inputs["Surface"])

        is_transparent = color.alpha < 1.0
        if is_transparent:
            material.use_screen_refraction = True
            material.refraction_depth = 0.5

        if part_slopes is not None and len(part_slopes) > 0:
            cls.__create_slope(nodes, links, node, -200, -220, part_slopes)

        if parts_cloth:
            cls.__create_cloth(nodes, links, node, -200, -100)

        if texmap is not None:
            cls.__create_texmap(nodes, links, -500, -140, texmap, mix_rgb_node.inputs["Color2"], mix_rgb_node.inputs["Fac"], node.inputs["Specular"])

        if pe_texmap is not None:
            cls.__create_texture(nodes, links, -500, -140, pe_texmap, mix_rgb_node.inputs["Color2"], mix_rgb_node.inputs["Fac"])

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
    def __node_vertex_color(cls, nodes, x, y):
        node = nodes.new("ShaderNodeVertexColor")
        node.location = x, y
        return node

    @classmethod
    def __node_group_color_code(cls, color, nodes, links, x, y):
        diff_color = color.linear_color_d
        rgb_node = cls.__node_rgb(nodes, x + -600, y + 60)
        rgb_node.outputs["Color"].default_value = diff_color

        mix_rgb_node = cls.__node_mix_rgb(nodes, x + -400, y + 0)
        mix_rgb_node.inputs["Fac"].default_value = 0

        node = cls.__node_color_code_material(nodes, color, x + -200, y + 0)

        links.new(rgb_node.outputs["Color"], mix_rgb_node.inputs["Color1"])
        links.new(mix_rgb_node.outputs["Color"], node.inputs["Color"])

        return node, rgb_node, mix_rgb_node

    @classmethod
    def __node_color_code_material(cls, nodes, color, x, y):
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
    def __create_texture(cls, nodes, links, x, y, texmap, color_input, alpha_input):
        image_name = texmap.texture
        if image_name is not None:
            texmap_image = cls.__node_tex_image_closest_clip(nodes, x, y, image_name, "sRGB")
            links.new(texmap_image.outputs["Color"], color_input)
            links.new(texmap_image.outputs["Alpha"], alpha_input)

    @classmethod
    def __create_texmap(cls, nodes, links, x, y, texmap, color_input, alpha_input, specular_input):
        cls.__create_texture(nodes, links, x, y, texmap, color_input, alpha_input)

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
