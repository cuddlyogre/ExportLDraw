import bpy
import mathutils

import os
import uuid

from .ldraw_color_options import LDrawColorOptions
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
        return

        path = os.path.join(APP_ROOT, 'inc', 'all_monkeys.blend')
        if bpy.app.version < (3, 4):
            path = os.path.join(APP_ROOT, 'inc', 'all_monkeys_33.blend')
        elif bpy.app.version < (4,):
            path = os.path.join(APP_ROOT, 'inc', 'all_monkeys_36.blend')

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
    def get_material(cls, color_code, bfc_certified=True, part_slopes=None, texmap=None, pe_texmaps=None):
        color = LDrawColor.get_color(color_code)
        bfc_certified = bfc_certified is True

        key = cls.__build_key(color, bfc_certified, part_slopes, texmap, pe_texmaps)

        # Reuse current material if it exists, otherwise create a new material
        material = bpy.data.materials.get(key)
        if material is not None:
            return material

        material = cls.__create_node_based_material(
            key,
            color,
            bfc_certified=bfc_certified,
            part_slopes=part_slopes,
            texmap=texmap,
            pe_texmaps=pe_texmaps,
        )
        return material

    @classmethod
    def __build_key(cls, color, bfc_certified, part_slopes, texmap, pe_texmaps):
        _key = ()

        _key += (color.name, color.code,)

        _key += (bfc_certified,)

        _key += (LDrawColorOptions.use_alt_colors,)

        if part_slopes is not None:
            _key += (part_slopes,)

        if texmap is not None:
            # wraps_full_circle changes the node graph (u-wrap chain), so it must key separately
            _key += (texmap.method, texmap.image_name, texmap.glossmap_image_name, texmap.wraps_full_circle(),)

        if pe_texmaps is not None:
            for pe_texmap in pe_texmaps:
                _key += (pe_texmap.image_name,)

        max_len = bpy.types.Object.bl_rna.properties['name'].length_max

        str_key = str(_key)
        if len(str_key) < max_len:
            return str_key

        key = cls.__key_map.get(_key)
        if key is None:
            cls.__key_map[_key] = str(uuid.uuid4())
            key = cls.__key_map.get(_key)

        return key

    @classmethod
    def __create_node_based_material(cls, key, color, bfc_certified=True, part_slopes=None, texmap=None, pe_texmaps=None):
        material = bpy.data.materials.new(key)
        material.use_fake_user = True
        material.use_nodes = True
        material.use_backface_culling = bfc_certified

        nodes = material.node_tree.nodes
        links = material.node_tree.links

        nodes.clear()

        diff_color = color.linear_color_a
        material.diffuse_color = diff_color
        material[strings.ldraw_color_code_key] = color.code
        material[strings.ldraw_color_name_key] = color.name

        is_transparent = color.alpha < 1.0
        if is_transparent:
            material.use_screen_refraction = True
            material.refraction_depth = 0.5

        rgb_node, mix_node, node_principled = cls.__node_color_code_material(color, nodes, links)

        if texmap is not None:
            cls.__create_texmap(nodes, links, -500, -180, mix_node, node_principled, texmap)

        if pe_texmaps is not None:
            for pe_texmap in pe_texmaps:
                cls.__create_pe_texmap(nodes, links, -500, -180, mix_node, node_principled, pe_texmap)

        if part_slopes is not None and len(part_slopes) > 0:
            cls.__create_slope(color, nodes, links, mix_node, node_principled, part_slopes)

        return material

    @classmethod
    def __node_principled(cls, nodes, x, y):
        node = nodes.new("ShaderNodeBsdfPrincipled")
        node.location = x, y
        return node

    @classmethod
    def __node_value(cls, nodes, x, y):
        node = nodes.new("ShaderNodeValue")
        node.location = x, y
        return node

    @classmethod
    def __node_map_range(cls, nodes, x, y):
        node = nodes.new("ShaderNodeMapRange")
        node.location = x, y
        return node

    @classmethod
    def __node_output_material(cls, nodes, x, y):
        node = nodes.new("ShaderNodeOutputMaterial")
        node.location = x, y
        return node

    @classmethod
    def __node_frame(cls, nodes, x, y):
        node = nodes.new("NodeFrame")
        node.location = x, y
        return node

    @classmethod
    def __node_separate_hsv(cls, nodes, x, y):
        node = nodes.new("ShaderNodeSeparateColor")
        node.mode = "HSV"
        node.location = x, y
        return node

    @classmethod
    def __node_combine_hsv(cls, nodes, x, y):
        node = nodes.new("ShaderNodeCombineColor")
        node.mode = "HSV"
        node.location = x, y
        return node

    @classmethod
    def __node_rgb(cls, nodes, x, y):
        node = nodes.new("ShaderNodeRGB")
        node.location = x, y
        return node

    @classmethod
    def __node_mix_rgb(cls, nodes, x, y):
        node = nodes.new("ShaderNodeMix")
        node.location = x, y
        node.data_type = "RGBA"
        node.blend_type = "MIX"
        return node

    @classmethod
    def __node_add_rgb(cls, nodes, x, y):
        node = nodes.new("ShaderNodeMix")
        node.location = x, y
        node.data_type = "RGBA"
        node.blend_type = "ADD"
        return node

    @classmethod
    def __node_hsv(cls, nodes, x, y):
        node = nodes.new("ShaderNodeHueSaturation")
        node.location = x, y
        return node

    @classmethod
    def __node_texture_coordinate(cls, nodes, x, y):
        node = nodes.new("ShaderNodeTexCoord")
        node.location = x, y
        return node

    @classmethod
    def __node_mapping(cls, nodes, x, y):
        node = nodes.new("ShaderNodeMapping")
        node.location = x, y
        return node

    @classmethod
    def __node_tex_voronoi(cls, nodes, x, y):
        node = nodes.new("ShaderNodeTexVoronoi")
        node.location = x, y
        return node

    @classmethod
    def __node_tex_noise(cls, nodes, x, y):
        node = nodes.new("ShaderNodeTexNoise")
        node.location = x, y
        return node

    @classmethod
    def __node_color_ramp(cls, nodes, x, y):
        node = nodes.new("ShaderNodeValToRGB")
        node.location = x, y
        return node

    @classmethod
    def __node_bump(cls, nodes, x, y):
        node = nodes.new("ShaderNodeBump")
        node.location = x, y
        return node

    @classmethod
    def __node_separate_xyz(cls, nodes, x, y):
        node = nodes.new("ShaderNodeSeparateXYZ")
        node.location = x, y
        return node

    @classmethod
    def __node_math_add(cls, nodes, x, y):
        node = nodes.new("ShaderNodeMath")
        node.operation = 'ADD'
        node.location = x, y
        return node

    @classmethod
    def __node_math_multiply(cls, nodes, x, y):
        node = nodes.new("ShaderNodeMath")
        node.operation = "MULTIPLY"
        node.location = x, y
        return node

    @classmethod
    def __node_maximum(cls, nodes, x, y):
        node = nodes.new("ShaderNodeMath")
        node.operation = "MAXIMUM"
        node.location = x, y
        return node

    @classmethod
    def __node_vector_math_normalize(cls, nodes, x, y):
        node = nodes.new("ShaderNodeVectorMath")
        node.operation = "NORMALIZE"
        node.location = x, y
        return node

    @classmethod
    def __node_math_maximum(cls, nodes, x, y):
        node = nodes.new("ShaderNodeMath")
        node.operation = "MAXIMUM"
        node.location = x, y
        return node

    @classmethod
    def __node_math_minimum(cls, nodes, x, y):
        node = nodes.new("ShaderNodeMath")
        node.operation = "MINIMUM"
        node.location = x, y
        return node

    @classmethod
    def __node_math_arccosine(cls, nodes, x, y):
        node = nodes.new("ShaderNodeMath")
        node.operation = "ARCCOSINE"
        node.location = x, y
        return node

    @classmethod
    def __node_math_to_degrees(cls, nodes, x, y):
        node = nodes.new("ShaderNodeMath")
        node.operation = 'DEGREES'
        node.location = x, y
        return node

    @classmethod
    def __node_math_compare(cls, nodes, x, y):
        node = nodes.new("ShaderNodeMath")
        node.operation = 'COMPARE'
        node.location = x, y
        return node

    @classmethod
    def __node_math_absolute(cls, nodes, x, y):
        node = nodes.new("ShaderNodeMath")
        node.operation = 'ABSOLUTE'
        node.location = x, y
        return node

    @classmethod
    def __node_math_greater_than(cls, nodes, x, y):
        node = nodes.new("ShaderNodeMath")
        node.operation = 'GREATER_THAN'
        node.location = x, y
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

    @classmethod
    def __node_color_code_material(cls, color, nodes, links):
        if False:
            ...
        elif color.material_name == "chrome":
            return cls.__node_lego_chrome(color, nodes, links)
        elif color.material_name == "pearlescent":
            return cls.__node_lego_pearlescent(color, nodes, links)
        elif color.material_name == "metal":
            return cls.__node_lego_metal(color, nodes, links)
        elif color.material_name == "glitter":
            return cls.__node_lego_glitter(color, nodes, links)
        elif color.material_name == "speckle":
            return cls.__node_lego_speckle(color, nodes, links)
        elif color.material_name == "rubber":
            return cls.__node_lego_rubber(color, nodes, links)
        elif color.material_name == "fabric":
            if color.material_fabric_type == "velvet":
                return cls.__node_lego_canvas(color, nodes, links)
            elif color.material_fabric_type == "canvas":
                return cls.__node_lego_canvas(color, nodes, links)
            elif color.material_fabric_type == "string":
                return cls.__node_lego_canvas(color, nodes, links)
            elif color.material_fabric_type == "fur":
                return cls.__node_lego_canvas(color, nodes, links)
            else:
                return cls.__node_lego_canvas(color, nodes, links)
        elif color.name.startswith("Milky_"):
            return cls.__node_lego_milky(color, nodes, links)
        elif color.name.startswith("Glow_In_Dark_"):
            return cls.__node_lego_milky(color, nodes, links)
        elif color.alpha < 1.0:
            return cls.__node_lego_transparent_material(color, nodes, links)
        else:
            return cls.__node_lego_standard_material(color, nodes, links)

    @classmethod
    # TODO: slight variation in strength for each material
    def __create_slope(cls, color, nodes, links, mix_node, node_principled, part_slopes=None):
        node_math_add = cls.__node_math_add(nodes, -1160, 0)
        node_math_add.inputs[0].default_value = 0
        node_math_add.inputs[1].default_value = 0

        node_tex_voronoi0 = cls.__node_tex_voronoi(nodes, -980, 0)
        node_tex_voronoi0.normalize = True
        node_tex_voronoi0.inputs['Scale'].default_value = 200

        node_math_multiply = cls.__node_math_multiply(nodes, -780, 0)

        node_bump = cls.__node_bump(nodes, -600, 0)
        node_bump.invert = True
        node_bump.inputs['Distance'].default_value = 1.0

        links.new(node_math_add.outputs['Value'], node_math_multiply.inputs[0])
        links.new(node_tex_voronoi0.outputs["Distance"], node_math_multiply.inputs[1])
        links.new(node_math_multiply.outputs['Value'], node_bump.inputs["Height"])
        links.new(node_bump.outputs["Normal"], node_principled.inputs["Normal"])

        if len(part_slopes) == 4:
            node_math_multiply1 = cls.__node_slope_if_angle(color, nodes, links, part_slopes[0], x=-500, y=1000)
            node_math_multiply2 = cls.__node_slope_if_angle(color, nodes, links, part_slopes[1], x=-500, y=300)
            node_math_multiply3 = cls.__node_slope_if_angle(color, nodes, links, part_slopes[2], x=-500, y=-300)
            node_math_multiply4 = cls.__node_slope_if_angle(color, nodes, links, part_slopes[3], x=-500, y=-1000)

            node_math_add1 = cls.__node_math_add(nodes, -1360, 800)
            node_math_add2 = cls.__node_math_add(nodes, -1360, -800)

            links.new(node_math_multiply1.outputs['Value'], node_math_add1.inputs[0])
            links.new(node_math_multiply2.outputs['Value'], node_math_add1.inputs[1])

            links.new(node_math_multiply3.outputs['Value'], node_math_add2.inputs[0])
            links.new(node_math_multiply4.outputs['Value'], node_math_add2.inputs[1])

            links.new(node_math_add1.outputs['Value'], node_math_add.inputs[0])
            links.new(node_math_add2.outputs['Value'], node_math_add.inputs[1])
        elif len(part_slopes) == 3:
            node_math_multiply1 = cls.__node_slope_if_angle(color, nodes, links, part_slopes[0], x=-500, y=600)
            node_math_multiply2 = cls.__node_slope_if_angle(color, nodes, links, part_slopes[1], x=-500, y=0)
            node_math_multiply3 = cls.__node_slope_if_angle(color, nodes, links, part_slopes[2], x=-500, y=-600)

            node_math_add1 = cls.__node_math_add(nodes, -1360, 500)

            links.new(node_math_multiply1.outputs['Value'], node_math_add1.inputs[0])
            links.new(node_math_multiply2.outputs['Value'], node_math_add1.inputs[1])

            links.new(node_math_add1.outputs['Value'], node_math_add.inputs[0])
            links.new(node_math_multiply3.outputs['Value'], node_math_add.inputs[1])
        elif len(part_slopes) == 2:
            node_math_multiply1 = cls.__node_slope_if_angle(color, nodes, links, part_slopes[0], x=-500, y=300)
            node_math_multiply2 = cls.__node_slope_if_angle(color, nodes, links, part_slopes[1], x=-500, y=-300)

            node_math_add1 = cls.__node_math_add(nodes, -1360, 0)

            links.new(node_math_multiply1.outputs['Value'], node_math_add1.inputs[0])
            links.new(node_math_multiply2.outputs['Value'], node_math_add1.inputs[1])

            links.new(node_math_add1.outputs['Value'], node_math_add.inputs[0])
        elif len(part_slopes) == 1:
            node_math_multiply1 = cls.__node_slope_if_angle(color, nodes, links, part_slopes[0], x=-500, y=0)

            links.new(node_math_multiply1.outputs['Value'], node_math_add.inputs[0])

    @classmethod
    def __node_slope_if_angle(cls, color, nodes, links, angle, x=0, y=0):
        offset = mathutils.Vector((x, y))

        # get the faces's up vector relative to down, Z up -Z down
        # =====================
        node_texture_coordinate = cls.__node_texture_coordinate(nodes, -2540, -180)
        node_separate_xyz = cls.__node_separate_xyz(nodes, -2360, -180)

        node_math_multiply = cls.__node_math_multiply(nodes, -2180, -180)
        node_math_multiply.inputs[1].default_value = -1

        node_math_arccosine = cls.__node_math_arccosine(nodes, -2000, -180)

        node_math_to_degrees = cls.__node_math_to_degrees(nodes, -1820, -180)
        # =====================

        # blender up is Z, LDraw up is -Y, so rotate the face's up to match with the list up angles in the slopes list
        # if the slope angles in the list used blender up, this could be skipped, but using ldraw up in the list is more portable
        # =====================
        node_math_add = cls.__node_math_add(nodes, -1640, -180)
        node_math_add.inputs[1].default_value = -90
        node_math_add.label = "Blender Up to LDraw Up"
        # =====================

        # face with this angle get the slope texture
        # =====================
        node_value = cls.__node_value(nodes, -1640, -20)
        node_value.outputs["Value"].default_value = angle
        # =====================

        # make sure value != 0 so that when value == 0, vertical faces don't get slope texture
        # if value of multiple node == 0, and that is connected to bum strength, that will prevent the texture from showing on those faces
        # =====================
        node_math_absolute = cls.__node_math_absolute(nodes, -1460, 160)

        node_math_greater_than = cls.__node_math_greater_than(nodes, -1280, 160)
        node_math_greater_than.inputs[1].default_value = 0.0

        node_math_multiply1 = cls.__node_math_multiply(nodes, -1100, 160)
        # =====================

        # does the face angle == value within 5 degrees
        # =====================
        node_math_compare = cls.__node_math_compare(nodes, -1460, -20)
        node_math_compare.inputs[2].default_value = 5.0
        # =====================

        links.new(node_texture_coordinate.outputs["Normal"], node_separate_xyz.inputs["Vector"])
        links.new(node_separate_xyz.outputs["Z"], node_math_multiply.inputs[0])
        links.new(node_math_multiply.outputs["Value"], node_math_arccosine.inputs[0])
        links.new(node_math_arccosine.outputs["Value"], node_math_to_degrees.inputs[0])
        links.new(node_math_to_degrees.outputs["Value"], node_math_add.inputs[0])
        links.new(node_value.outputs["Value"], node_math_compare.inputs[0])
        links.new(node_math_add.outputs["Value"], node_math_compare.inputs[1])
        links.new(node_value.outputs["Value"], node_math_absolute.inputs[0])
        links.new(node_math_absolute.outputs["Value"], node_math_greater_than.inputs[0])
        links.new(node_math_greater_than.outputs["Value"], node_math_multiply1.inputs[0])
        links.new(node_math_compare.outputs["Value"], node_math_multiply1.inputs[1])

        node_texture_coordinate.location += offset
        node_separate_xyz.location += offset
        node_math_multiply.location += offset
        node_math_arccosine.location += offset
        node_math_to_degrees.location += offset
        node_math_add.location += offset
        node_value.location += offset
        node_math_compare.location += offset
        node_math_absolute.location += offset
        node_math_greater_than.location += offset
        node_math_multiply1.location += offset

        return node_math_multiply1

    @classmethod
    def __mapped_value(cls, value):
        from_min = 0.1
        from_max = 0.4
        to_min = 0.15
        to_max = 0.25
        mapped_value = to_min + (value - from_min) * (to_max - to_min) / (from_max - from_min)
        return mapped_value

    @classmethod
    def __create_image(cls, nodes, links, x, y, mix_node, texmap, wrap_u=False):
        image_name = texmap.image_name
        if image_name is not None:
            texmap_image = cls.__node_tex_image_closest_clip(nodes, x, y, image_name, "sRGB")
            if wrap_u:
                cls.__wrap_u_links(nodes, links, x - 300, y, texmap_image)
            links.new(texmap_image.outputs["Alpha"], mix_node.inputs["Factor"])
            links.new(texmap_image.outputs["Color"], mix_node.inputs["B"])

    @classmethod
    def __create_glossmap_image(cls, nodes, links, x, y, node_principled, texmap, wrap_u=False):
        image_name = texmap.glossmap_image_name
        if image_name is not None:
            glossmap_image = cls.__node_tex_image_closest_clip(nodes, x, y - 280, image_name, "Non-Color")
            if wrap_u:
                cls.__wrap_u_links(nodes, links, x - 300, y - 280, glossmap_image)
            # spec: "a single channel image where the value indicates the amount of
            # specularity", so it drives the specular amount, not its tint
            links.new(glossmap_image.outputs["Color"], node_principled.inputs["Specular IOR Level"])

    # wrap u (fract) while leaving v to the image node's CLIP extension: full-circumference
    # cylindrical/spherical textures need the seam-straddling face (u pushed outside 0..1 by
    # the seam fix) to sample the wrapped texel, but v outside 0..1 must still clip so
    # geometry beyond the projection shows the part color instead of a tiled texture
    @classmethod
    def __wrap_u_links(cls, nodes, links, x, y, image_node):
        node_uv = nodes.new("ShaderNodeUVMap")
        node_uv.location = x - 600, y
        node_separate = nodes.new("ShaderNodeSeparateXYZ")
        node_separate.location = x - 400, y
        node_fract = nodes.new("ShaderNodeMath")
        node_fract.operation = "FRACT"
        node_fract.location = x - 200, y
        node_combine = nodes.new("ShaderNodeCombineXYZ")
        node_combine.location = x, y

        links.new(node_uv.outputs["UV"], node_separate.inputs["Vector"])
        links.new(node_separate.outputs["X"], node_fract.inputs[0])
        links.new(node_fract.outputs["Value"], node_combine.inputs["X"])
        links.new(node_separate.outputs["Y"], node_combine.inputs["Y"])
        links.new(node_combine.outputs["Vector"], image_node.inputs["Vector"])

    @classmethod
    def __create_texmap(cls, nodes, links, x, y, mix_node, node_principled, texmap):
        wrap_u = texmap.wraps_full_circle()
        cls.__create_image(nodes, links, x, y, mix_node, texmap, wrap_u=wrap_u)
        cls.__create_glossmap_image(nodes, links, x, y, node_principled, texmap, wrap_u=wrap_u)

    @classmethod
    def __create_pe_texmap(cls, nodes, links, x, y, mix_node, node_principled, pe_texmap):
        cls.__create_image(nodes, links, x, y, mix_node, pe_texmap)

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
    def __node_lego_standard_material(cls, color, nodes, links):
        diffuse_color = color.linear_color_d
        rgb_node = cls.__node_rgb(nodes, -420, 0)
        rgb_node.outputs["Color"].default_value = diffuse_color

        mix_node = cls.__node_mix_rgb(nodes, -220, 0)
        mix_node.inputs["Factor"].default_value = 0

        node_principled = cls.__node_principled(nodes, -35, 0)
        node_principled.inputs['Metallic'].default_value = 0.0
        node_principled.inputs['Roughness'].default_value = 0.1
        node_principled.inputs['Subsurface Weight'].default_value = 1.0
        node_principled.inputs['Subsurface Scale'].default_value = 0.005
        node_principled.inputs['Emission Strength'].default_value = color.luminance

        out = cls.__node_output_material(nodes, 240, 0)

        links.new(rgb_node.outputs["Color"], mix_node.inputs["A"])
        links.new(mix_node.outputs["Result"], node_principled.inputs["Base Color"])
        links.new(node_principled.outputs["BSDF"], out.inputs["Surface"])

        return rgb_node, mix_node, node_principled

    @classmethod
    def __node_lego_transparency(cls, color, nodes, links, node_principled, min_transparency=None):
        node_value = cls.__node_value(nodes, -440, -480)
        node_value.label = "Alpha"
        node_value.outputs["Value"].default_value = color.alpha

        if min_transparency is None:
            min_transparency = 128 / 255
        node_value1 = cls.__node_value(nodes, -440, -540)
        node_value1.label = "Min Transparency"
        node_value1.outputs["Value"].default_value = min_transparency

        node_map_range_ior = cls.__node_map_range(nodes, -220, -260)
        node_map_range_ior.name = "Map Range IOR"
        node_map_range_ior.inputs['Value'].default_value = color.alpha  # 255/255 (1.0) needs to mean transmission 0, 128 / 255 (0.5) needs to mean transmission 1, 0/255 needs to mean invisible
        node_map_range_ior.inputs['From Min'].default_value = 0
        node_map_range_ior.inputs['From Max'].default_value = min_transparency
        node_map_range_ior.inputs['To Min'].default_value = 1.0
        node_map_range_ior.inputs['To Max'].default_value = 1.5

        node_map_range_transmission = cls.__node_map_range(nodes, -220, -520)
        node_map_range_transmission.name = "Map Range Transmission"
        node_map_range_transmission.inputs['Value'].default_value = color.alpha  # 255/255 (1.0) needs to mean transmission 0, 128/255 (0.5) needs to mean transmission 1, 0/255 needs to mean invisible
        node_map_range_transmission.inputs['From Min'].default_value = min_transparency
        node_map_range_transmission.inputs['From Max'].default_value = 1.0
        node_map_range_transmission.inputs['To Min'].default_value = 1.0
        node_map_range_transmission.inputs['To Max'].default_value = 0.9

        links.new(node_value.outputs["Value"], node_map_range_ior.inputs['Value'])
        links.new(node_value.outputs["Value"], node_map_range_transmission.inputs['Value'])
        links.new(node_value1.outputs["Value"], node_map_range_ior.inputs['From Max'])
        links.new(node_value1.outputs["Value"], node_map_range_transmission.inputs['From Min'])
        links.new(node_map_range_ior.outputs['Result'], node_principled.inputs['IOR'])
        links.new(node_map_range_transmission.outputs['Result'], node_principled.inputs['Transmission Weight'])

    @classmethod
    def __node_lego_transparent_material(cls, color, nodes, links):
        rgb_node, mix_node, node_principled = cls.__node_lego_standard_material(color, nodes, links)

        if color.alpha < 1.0:
            cls.__node_lego_transparency(color, nodes, links, node_principled)

        return rgb_node, mix_node, node_principled

    @classmethod
    def __node_lego_chrome(cls, color, nodes, links):
        rgb_node, mix_node, node_principled = cls.__node_lego_standard_material(color, nodes, links)

        node_principled.inputs['Metallic'].default_value = 1.0
        node_principled.inputs['Roughness'].default_value = 0.0

        return rgb_node, mix_node, node_principled

    @classmethod
    def __node_lego_pearlescent(cls, color, nodes, links):
        rgb_node, mix_node, node_principled = cls.__node_lego_standard_material(color, nodes, links)

        node_principled.inputs['Metallic'].default_value = 0.6
        node_principled.inputs['Roughness'].default_value = 0.6

        return rgb_node, mix_node, node_principled

    @classmethod
    def __node_lego_metal(cls, color, nodes, links):
        rgb_node, mix_node, node_principled = cls.__node_lego_standard_material(color, nodes, links)

        node_principled.inputs['Metallic'].default_value = 1.0
        node_principled.inputs['Roughness'].default_value = 0.2

        return rgb_node, mix_node, node_principled

    @classmethod
    def __node_lego_milky(cls, color, nodes, links):
        rgb_node, mix_node, node_principled = cls.__node_lego_standard_material(color, nodes, links)

        node_principled.inputs['Subsurface Scale'].default_value = 0.08

        links.new(rgb_node.outputs["Color"], node_principled.inputs["Emission Color"])

        return rgb_node, mix_node, node_principled

    @classmethod
    def __node_lego_glitter(cls, color, nodes, links):
        rgb_node, mix_node, node_principled = cls.__node_lego_standard_material(color, nodes, links)

        rgb_node.location = (-600, 0)
        mix_node.location = (-400, 0)

        if color.alpha < 1.0:
            cls.__node_lego_transparency(color, nodes, links, node_principled)

        node_tex_voronoi0 = cls.__node_tex_voronoi(nodes, -1120, 0)
        node_tex_voronoi0.normalize = True
        node_tex_voronoi0.inputs['Scale'].default_value = 100 / (color.material_size or color.material_maxsize or 1)
        node_tex_voronoi0.inputs['Roughness'].default_value = 0.0

        node_color_ramp0 = cls.__node_color_ramp(nodes, -920, 0)
        node_color_ramp0.color_ramp.interpolation = "CONSTANT"
        node_color_ramp0.color_ramp.elements[0].position = 0.0
        node_color_ramp0.color_ramp.elements[0].color = (1.0, 1.0, 1.0, 1.0)
        node_color_ramp0.color_ramp.elements[1].position = cls.__mapped_value(color.material_vfraction or 0.3)
        node_color_ramp0.color_ramp.elements[1].color = (0.0, 0.0, 0.0, 1.0)

        mix_node1 = cls.__node_mix_rgb(nodes, -220, 0)

        diffuse_color1 = color.linear_material_color_d
        rgb_node1 = cls.__node_rgb(nodes, -820, -240)
        rgb_node1.outputs["Color"].default_value = diffuse_color1

        if bpy.app.version >= (5,):
            links.new(node_tex_voronoi0.outputs["Distance"], node_color_ramp0.inputs["Factor"])
        else:
            links.new(node_tex_voronoi0.outputs["Distance"], node_color_ramp0.inputs["Fac"])

        links.new(node_color_ramp0.outputs["Color"], mix_node1.inputs["Factor"])
        links.new(node_color_ramp0.outputs["Color"], node_principled.inputs["Metallic"])

        links.new(mix_node.outputs["Result"], mix_node1.inputs["A"])
        links.new(mix_node1.outputs["Result"], node_principled.inputs["Base Color"])
        links.new(rgb_node1.outputs["Color"], mix_node1.inputs["B"])

        return rgb_node, mix_node, node_principled

    @classmethod
    def __node_lego_speckle(cls, color, nodes, links):
        rgb_node, mix_node, node_principled = cls.__node_lego_standard_material(color, nodes, links)

        rgb_node.location = (-600, 0)
        mix_node.location = (-400, 0)

        if color.alpha < 1.0:
            cls.__node_lego_transparency(color, nodes, links, node_principled)

        node_tex_noise = cls.__node_tex_noise(nodes, -1120, 0)
        node_tex_noise.normalize = True
        node_tex_noise.inputs['Scale'].default_value = 100 * (color.material_minsize or 1)
        node_tex_noise.inputs['Roughness'].default_value = 0.0

        node_color_ramp0 = cls.__node_color_ramp(nodes, -920, 0)
        node_color_ramp0.color_ramp.interpolation = "CONSTANT"
        node_color_ramp0.color_ramp.elements[0].position = 0.0
        node_color_ramp0.color_ramp.elements[0].color = (1.0, 1.0, 1.0, 1.0)
        node_color_ramp0.color_ramp.elements[1].position = color.material_fraction or 0.5
        node_color_ramp0.color_ramp.elements[1].color = (0.0, 0.0, 0.0, 1.0)

        mix_node1 = cls.__node_mix_rgb(nodes, -220, 0)

        diffuse_color1 = color.linear_material_color_d
        rgb_node1 = cls.__node_rgb(nodes, -820, -240)
        rgb_node1.outputs["Color"].default_value = diffuse_color1

        if bpy.app.version >= (5,):
            links.new(node_tex_noise.outputs["Factor"], node_color_ramp0.inputs["Factor"])
        else:
            links.new(node_tex_noise.outputs["Fac"], node_color_ramp0.inputs["Fac"])

        links.new(node_color_ramp0.outputs["Color"], mix_node1.inputs["Factor"])

        links.new(mix_node.outputs["Result"], mix_node1.inputs["A"])
        links.new(mix_node1.outputs["Result"], node_principled.inputs["Base Color"])
        links.new(rgb_node1.outputs["Color"], mix_node1.inputs["B"])

        return rgb_node, mix_node, node_principled

    @classmethod
    def __node_lego_rubber(cls, color, nodes, links):
        rgb_node, mix_node, node_principled = cls.__node_lego_standard_material(color, nodes, links)

        node_principled.inputs['Subsurface Scale'].default_value = 0.08
        node_principled.inputs['Roughness'].default_value = 0.9

        if color.alpha < 1.0:
            cls.__node_lego_transparency(color, nodes, links, node_principled, min_transparency=0.422)

        node_tex_voronoi0 = cls.__node_tex_voronoi(nodes, -820, 0)
        node_tex_voronoi0.normalize = True
        node_tex_voronoi0.inputs['Scale'].default_value = 500
        node_tex_voronoi0.inputs['Roughness'].default_value = 0.7

        node_bump = cls.__node_bump(nodes, -620, 0)
        node_bump.invert = True
        node_bump.inputs['Strength'].default_value = 0.2
        node_bump.inputs['Distance'].default_value = 0.1

        links.new(node_tex_voronoi0.outputs["Distance"], node_bump.inputs["Height"])
        links.new(node_bump.outputs["Normal"], node_principled.inputs["Normal"])

        return rgb_node, mix_node, node_principled

    @classmethod
    def __node_lego_canvas(cls, color, nodes, links):
        rgb_node, mix_node, node_principled = cls.__node_lego_standard_material(color, nodes, links)

        node_principled.inputs['Subsurface Scale'].default_value = 0.08
        node_principled.inputs['Roughness'].default_value = 0.9

        if color.alpha < 1.0:
            cls.__node_lego_transparency(color, nodes, links, node_principled, min_transparency=0.422)

        node_tex_voronoi0 = cls.__node_tex_voronoi(nodes, -820, 0)
        node_tex_voronoi0.feature = 'DISTANCE_TO_EDGE'
        node_tex_voronoi0.inputs['Scale'].default_value = 365
        node_tex_voronoi0.inputs['Randomness'].default_value = 0.517

        node_bump = cls.__node_bump(nodes, -620, 0)
        node_bump.invert = True
        node_bump.inputs['Strength'].default_value = 0.5
        node_bump.inputs['Distance'].default_value = 1.0

        if bpy.app.version >= (4, 4):
            node_bump.inputs['Filter Width'].default_value = 5.0

        links.new(node_tex_voronoi0.outputs["Distance"], node_bump.inputs["Height"])
        links.new(node_bump.outputs["Normal"], node_principled.inputs["Normal"])

        return rgb_node, mix_node, node_principled
