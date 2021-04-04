"""Parses and stores a table of color / material definitions. Converts color space."""

import re
import math
import struct

from . import options

colors = {}


def reset_caches():
    global colors
    colors = {}


def get_color(color_code):
    if options.debug_text:
        print(len(colors))

    if color_code in colors:
        return colors[color_code]

    print(f"Bad color code: {color_code}")
    color_code = "16"
    return colors[color_code]


def parse_color(params):
    color = LdrawColor(params)
    colors[color.code] = color


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


def is_fluorescent_transparent(col_name):
    return col_name in [
        "Trans_Neon_Orange",
        "Trans_Neon_Green",
        "Trans_Neon_Yellow",
        "Trans_Bright_Green",
    ]


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


def hex_string_to_linear_rgba(hex_string):
    """Convert color hex value to RGB value."""
    # Handle direct colors
    # Direct colors are documented here: http://www.hassings.dk/l3/l3p.html
    match = re.fullmatch(r"0x0*([0-9])((?:[A-F0-9]{2}){3})", hex_string)
    if match is not None:
        digit = match.group(1)
        rgb_str = match.group(2)

        interleaved = False
        if digit == "2":  # Opaque
            alpha = 1.0
        elif digit == "3":  # Transparent
            alpha = 0.5
        elif digit == "4":  # Opaque
            alpha = 1.0
            interleaved = True
        elif digit == "5":  # More Transparent
            alpha = 0.333
            interleaved = True
        elif digit == "6":  # Less transparent
            alpha = 0.666
            interleaved = True
        elif digit == "7":  # Invisible
            alpha = 0.0
            interleaved = True
        else:
            alpha = 1.0

        if interleaved:
            # Input string is six hex digits of two colors "RGBRGB".
            # This was designed to be a dithered color.
            # Take the average of those two colors (R+R,G+G,B+B) * 0.5
            r = float(int(rgb_str[0], 16)) / 15
            g = float(int(rgb_str[1], 16)) / 15
            b = float(int(rgb_str[2], 16)) / 15
            color1 = srgb_to_linear_rgb((r, g, b))
            r = float(int(rgb_str[3], 16)) / 15
            g = float(int(rgb_str[4], 16)) / 15
            b = float(int(rgb_str[5], 16)) / 15
            color2 = srgb_to_linear_rgb((r, g, b))
            return (0.5 * (color1[0] + color2[0]),
                    0.5 * (color1[1] + color2[1]),
                    0.5 * (color1[2] + color2[2]), alpha)

        # String is "RRGGBB" format
        return hex_digits_to_linear_rgba(rgb_str, alpha)
    return None


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


def hex_digits_to_linear_rgba(hex_digits, alpha):
    # String is "RRGGBB" format
    int_tuple = struct.unpack("BBB", bytes.fromhex(hex_digits))
    srgb = tuple([val / 255 for val in int_tuple])
    linear_rgb = srgb_to_linear_rgb(srgb)
    return linear_rgb[0], linear_rgb[1], linear_rgb[2], alpha


def __clamp(value):
    return max(min(value, 1.0), 0.0)


class LdrawColor:
    def __init__(self, params):
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

        self.__parse_color(params)

    def __parse_color(self, params):
        name = params[2]
        color_code = params[4]

        linear_rgba = hex_digits_to_linear_rgba(params[6][1:], 1.0)
        alpha = linear_rgba[3]
        linear_rgba = srgb_to_linear_rgb(linear_rgba[0:3])

        lineaer_rgba_edge = hex_digits_to_linear_rgba(params[8][1:], 1.0)
        lineaer_rgba_edge = srgb_to_linear_rgb(lineaer_rgba_edge[0:3])

        self.name = name
        self.code = color_code
        self.color = linear_rgba
        self.alpha = alpha
        self.edge_color = lineaer_rgba_edge
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

        if "METAL" in params:
            self.material = "METAL"

        if "MATERIAL" in params:
            subline = params[params.index("MATERIAL"):]

            self.material = get_value(subline, "MATERIAL")
            hex_digits = get_value(subline, "VALUE")[1:]
            self.secondary_color = hex_digits_to_linear_rgba(hex_digits, 1.0)
            self.fraction = get_value(subline, "FRACTION")
            self.vfraction = get_value(subline, "VFRACTION")
            self.size = get_value(subline, "SIZE")
            self.minsize = get_value(subline, "MINSIZE")
            self.maxsize = get_value(subline, "MAXSIZE")
