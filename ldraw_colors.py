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

    if __is_int(color_code):
        color_int = int(color_code)
        if color_int in colors:
            return colors[color_int]

    return None


def parse_color(params):
    name = params[2]
    color_code = int(params[4])

    linear_rgba = __hex_digits_to_linear_rgba(params[6][1:], 1.0)
    alpha = linear_rgba[3]
    linear_rgba = __srgb_to_linear_rgb(linear_rgba[0:3])

    lineaer_rgba_edge = __hex_digits_to_linear_rgba(params[8][1:], 1.0)
    lineaer_rgba_edge = __srgb_to_linear_rgb(lineaer_rgba_edge[0:3])

    color = {
        "name": name,
        "code": color_code,
        "color": linear_rgba,
        "alpha": alpha,
        "edge_color": lineaer_rgba_edge,
        "luminance": 0.0,
        "material": "BASIC"
    }

    if "ALPHA" in params:
        color["alpha"] = int(__get_value(params, "ALPHA")) / 256.0

    if "LUMINANCE" in params:
        color["luminance"] = int(__get_value(params, "LUMINANCE"))

    if "CHROME" in params:
        color["material"] = "CHROME"

    if "PEARLESCENT" in params:
        color["material"] = "PEARLESCENT"

    if "RUBBER" in params:
        color["material"] = "RUBBER"

    if "METAL" in params:
        color["material"] = "METAL"

    if "MATERIAL" in params:
        subline = params[params.index("MATERIAL"):]

        color["material"] = __get_value(subline, "MATERIAL")
        hex_digits = __get_value(subline, "VALUE")[1:]
        color["secondary_color"] = __hex_digits_to_linear_rgba(hex_digits, 1.0)
        color["fraction"] = __get_value(subline, "FRACTION")
        color["vfraction"] = __get_value(subline, "VFRACTION")
        color["size"] = __get_value(subline, "SIZE")
        color["minsize"] = __get_value(subline, "MINSIZE")
        color["maxsize"] = __get_value(subline, "MAXSIZE")

    colors[color_code] = color


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
    if col_name == "Trans_Neon_Orange":
        return True
    if col_name == "Trans_Neon_Green":
        return True
    if col_name == "Trans_Neon_Yellow":
        return True
    if col_name == "Trans_Bright_Green":
        return True
    return False


def is_dark(color):
    r = color[0]
    g = color[1]
    b = color[2]

    # Measure the perceived brightness of color
    brightness = math.sqrt(0.299 * r * r + 0.587 * g * g + 0.114 * b * b)

    # Dark colors have white lines
    if brightness < 0.02:
        return True
    return False


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
            color1 = __srgb_to_linear_rgb((r, g, b))
            r = float(int(rgb_str[3], 16)) / 15
            g = float(int(rgb_str[4], 16)) / 15
            b = float(int(rgb_str[5], 16)) / 15
            color2 = __srgb_to_linear_rgb((r, g, b))
            return (0.5 * (color1[0] + color2[0]),
                    0.5 * (color1[1] + color2[1]),
                    0.5 * (color1[2] + color2[2]), alpha)

        # String is "RRGGBB" format
        return __hex_digits_to_linear_rgba(rgb_str, alpha)
    return None


def __is_int(s):
    try:
        int(s)
        return True
    except ValueError:
        return False


def __get_value(line, value):
    """Parses a color value from the ldConfig.ldr file"""
    if value in line:
        n = line.index(value)
        return line[n + 1]


def __srgb_to_rgb_value(value):
    # See https://en.wikipedia.org/wiki/SRGB#The_reverse_transformation
    if value < 0.04045:
        return value / 12.92
    return ((value + 0.055) / 1.055) ** 2.4


def __srgb_to_linear_rgb(srgb_color):
    # See https://en.wikipedia.org/wiki/SRGB#The_reverse_transformation
    (sr, sg, sb) = srgb_color
    r = __srgb_to_rgb_value(sr)
    g = __srgb_to_rgb_value(sg)
    b = __srgb_to_rgb_value(sb)
    return r, g, b


def __hex_digits_to_linear_rgba(hex_digits, alpha):
    # String is "RRGGBB" format
    int_tuple = struct.unpack('BBB', bytes.fromhex(hex_digits))
    srgb = tuple([val / 255 for val in int_tuple])
    linear_rgb = __srgb_to_linear_rgb(srgb)
    return linear_rgb[0], linear_rgb[1], linear_rgb[2], alpha


def __clamp(value):
    return max(min(value, 1.0), 0.0)
