"""Parses and stores a table of color / material definitions. Converts color space."""

import math
import struct

from . import helpers

defaults = dict()
defaults['use_alt_colors'] = True

use_alt_colors = defaults['use_alt_colors']

colors = {}
bad_color = None
materials = ["chrome", "pearlescent", "rubber", "matte_metallic", "metal"]


def reset_caches():
    global colors
    colors = {}


def get_color(color_code):
    if color_code in colors:
        return colors[color_code]

    global bad_color
    if bad_color is None:
        clean_line = "0 !COLOUR Bad_Color CODE -9999 VALUE #FF0000 EDGE #00FF00"
        params = helpers.get_params(clean_line, "0 !COLOUR ", lowercase=False)
        color_code = parse_color(params)
        bad_color = colors[color_code]

    print(f"Bad color code: {color_code}")
    color_code = bad_color.code
    return colors[color_code]


def parse_color(params):
    color = LDrawColor()
    color.parse_color(params)
    colors[color.code] = color
    return color.code


def lighten_rgba(color, scale):
    # Moves the linear RGB values closer to white
    # scale = 0 means full white
    # scale = 1 means color stays same
    color = ((1.0 - color[0]) * scale,
             (1.0 - color[1]) * scale,
             (1.0 - color[2]) * scale,
             color[3])
    return (
        __clamp(1.0 - color[0]),
        __clamp(1.0 - color[1]),
        __clamp(1.0 - color[2]),
        color[3]
    )


# wp-content/plugins/woocommerce/includes/wc-formatting-functions.php
# line 779
def is_dark(color):
    r = color[0]
    g = color[1]
    b = color[2]

    # Measure the perceived brightness of color
    brightness = math.sqrt(0.299 * r * r + 0.587 * g * g + 0.114 * b * b)

    # Dark colors have white lines
    return brightness < 0.02


def __is_int(s):
    try:
        int(s)
        return True
    except ValueError:
        return False


def __srgb_to_rgb_value(value):
    # See https://en.wikipedia.org/wiki/SRGB#The_reverse_transformation
    if value < 0.04045:
        return value / 12.92
    return ((value + 0.055) / 1.055) ** 2.4


def srgb_to_linear_rgb(srgb_color):
    # See https://en.wikipedia.org/wiki/SRGB#The_reverse_transformation
    (sr, sg, sb) = srgb_color
    r = __srgb_to_rgb_value(sr)
    g = __srgb_to_rgb_value(sg)
    b = __srgb_to_rgb_value(sb)
    return r, g, b


def hex_digits_to_linear_rgba(hex_digits):
    srgb = hex_digits_to_srgb(hex_digits)
    linear_rgb = srgb_to_linear_rgb(srgb)
    return linear_rgb[0], linear_rgb[1], linear_rgb[2]


def hex_digits_to_srgb(hex_digits):
    # String is "RRGGBB" format
    int_tuple = struct.unpack("BBB", bytes.fromhex(hex_digits))
    srgb = tuple([val / 255 for val in int_tuple])
    return srgb[0], srgb[1], srgb[2]


def get_color_value(value, linear=True):
    hex_digits = extract_hex_digits(value)

    if linear:
        return hex_digits_to_linear_rgba(hex_digits)
    else:
        return hex_digits_to_srgb(hex_digits)


def extract_hex_digits(hex_digits):
    if hex_digits.startswith('#'):
        return hex_digits[1:]
    else:
        return hex_digits


def __clamp(value):
    return max(min(value, 1.0), 0.0)


class LDrawColor:
    def __init__(self):
        self.name = None
        self.code = None
        self.color = None
        self.edge_color = None
        self.alpha = None
        self.luminance = None
        self.material_name = None
        self.material_color = None
        self.material_alpha = None
        self.material_luminance = None
        self.material_fraction = None
        self.material_vfraction = None
        self.material_size = None
        self.material_minsize = None
        self.material_maxsize = None

    def parse_color(self, params, linear=True):
        # name CODE x VALUE v EDGE e required
        # 0 !COLOUR Black CODE 0 VALUE #1B2A34 EDGE #2B4354

        name = params[0]
        self.name = name

        # Tags are case-insensitive.
        # https://www.ldraw.org/article/299
        lparams = [x.lower() for x in params]

        i = lparams.index("code")
        code = lparams[i + 1]
        self.code = code

        i = lparams.index("value")
        value = lparams[i + 1]
        rgba = get_color_value(value, linear)
        self.color = rgba

        i = lparams.index("edge")
        edge = lparams[i + 1]
        e_rgba = get_color_value(edge, linear)
        self.edge_color = e_rgba

        # [ALPHA a] [LUMINANCE l] [ CHROME | PEARLESCENT | RUBBER | MATTE_METALLIC | METAL | MATERIAL <params> ]
        alpha = 255
        if "alpha" in lparams:
            i = lparams.index("alpha")
            alpha = int(lparams[i + 1])
        self.alpha = alpha / 255

        luminance = 0
        if "luminance" in lparams:
            i = lparams.index("luminance")
            luminance = int(lparams[i + 1])
        self.luminance = luminance

        material_name = None
        for _material in materials:
            if _material in lparams:
                material_name = _material
                break
        self.material_name = material_name

        # MATERIAL SPECKLE VALUE #898788 FRACTION 0.4               MINSIZE 1    MAXSIZE 3
        # MATERIAL GLITTER VALUE #FFFFFF FRACTION 0.8 VFRACTION 0.6 MINSIZE 0.02 MAXSIZE 0.1
        if "material" in lparams:
            i = lparams.index("material")
            material_parts = lparams[i:]

            material_name = material_parts[1]
            self.material_name = material_name

            i = lparams.index("value")
            material_value = lparams[i + 1]
            material_rgba = get_color_value(material_value, linear)
            self.material_color = material_rgba

            material_alpha = 255
            if "alpha" in material_parts:
                i = material_parts.index("alpha")
                material_alpha = int(material_parts[i + 1])
            self.material_alpha = material_alpha / 255

            material_luminance = 0
            if "luminance" in material_parts:
                i = material_parts.index("luminance")
                material_luminance = int(material_parts[i + 1])
            self.material_luminance = material_luminance

            material_minsize = 0.0
            material_maxsize = 0.0
            if "size" in material_parts:
                i = material_parts.index("size")
                material_minsize = float(material_parts[i + 1])
                material_maxsize = float(material_parts[i + 1])

            if "minsize" in material_parts:
                i = material_parts.index("minsize")
                material_minsize = float(material_parts[i + 1])

            if "maxsize" in material_parts:
                i = material_parts.index("maxsize")
                material_maxsize = float(material_parts[i + 1])
            self.material_minsize = material_minsize
            self.material_maxsize = material_maxsize

            material_fraction = 0.0
            if "fraction" in material_parts:
                i = material_parts.index("fraction")
                material_fraction = float(material_parts[i + 1])
            self.material_fraction = material_fraction

            material_vfraction = 0.0
            if "vfraction" in material_parts:
                i = material_parts.index("vfraction")
                material_vfraction = float(material_parts[i + 1])
            self.material_vfraction = material_vfraction
