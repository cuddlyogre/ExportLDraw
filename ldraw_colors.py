"""Parses and stores a table of color / material definitions. Converts color space."""

import math
import struct

defaults = dict()
defaults['use_alt_colors'] = True

use_alt_colors = defaults['use_alt_colors']

colors = {}
bad_color = None


def reset_caches():
    global colors
    colors = {}


def get_color(color_code):
    if color_code in colors:
        return colors[color_code]

    global bad_color
    if bad_color is None:
        bad_color = LDrawColor()
        bad_color.name = "Bad Color"
        bad_color.code = "-9999"

        hex_digits = "#FF0000"[1:]
        rgba = get_color_value(hex_digits)
        bad_color.color = rgba

        hex_digits = "#00FF00"[1:]
        e_rgba = get_color_value(hex_digits)
        bad_color.edge_color = e_rgba

        bad_color.alpha = 1.0
        bad_color.luminance = 0.0
        colors[bad_color.code] = bad_color

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


def get_value(line, value):
    """Parses a color value from the ldConfig.ldr file"""
    if value in line:
        n = line.index(value)
        return line[n + 1]


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


def get_color_value(hex_digits, linear=True):
    if linear:
        return hex_digits_to_linear_rgba(hex_digits)
    else:
        return hex_digits_to_srgb(hex_digits)


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
        self.material = None
        self.secondary_color = None
        self.fraction = None
        self.vfraction = None
        self.size = None
        self.minsize = None
        self.maxsize = None

    def parse_color(self, params, linear=True):
        name = params[2]
        self.name = name

        color_code = params[4]
        self.code = color_code

        hex_digits = params[6][1:]
        rgba = get_color_value(hex_digits, linear)
        self.color = rgba

        hex_digits = params[8][1:]
        e_rgba = get_color_value(hex_digits, linear)
        self.edge_color = e_rgba

        self.alpha = 1.0
        self.luminance = 0.0
        self.material = "BASIC"

        if "ALPHA" in params:
            self.alpha = int(get_value(params, "ALPHA")) / 256.0

        if "LUMINANCE" in params:
            self.luminance = int(get_value(params, "LUMINANCE"))

        if "CHROME" in params:
            self.material = "CHROME"

        if "PEARLESCENT" in params:
            self.material = "PEARLESCENT"

        if "RUBBER" in params:
            self.material = "RUBBER"

        if "MATTE_METALLIC" in params:
            self.material = "MATTE_METALLIC"

        if "METAL" in params:
            self.material = "METAL"

        if "MATERIAL" in params:
            subline = params[params.index("MATERIAL"):]

            self.material = get_value(subline, "MATERIAL")

            hex_digits = get_value(subline, "VALUE")[1:]
            secondary_color = get_color_value(hex_digits, linear)
            self.secondary_color = secondary_color

            self.fraction = get_value(subline, "FRACTION")
            self.vfraction = get_value(subline, "VFRACTION")
            self.size = get_value(subline, "SIZE")
            self.minsize = get_value(subline, "MINSIZE")
            self.maxsize = get_value(subline, "MAXSIZE")
