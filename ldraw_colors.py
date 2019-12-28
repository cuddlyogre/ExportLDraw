import re
import math

from . import options
from .ldraw_file import LDrawFile


class LDrawColors:
    """Parses and stores a table of color / material definitions. Converts color space."""

    colors = {}

    @staticmethod
    def reset_caches():
        LDrawColors.colors = {}

    @staticmethod
    def __is_int(s):
        try:
            int(s)
            return True
        except ValueError:
            return False

    @staticmethod
    def get_color(color_code):
        if options.debug_text:
            print(len(LDrawColors.colors))

        if LDrawColors.__is_int(color_code):
            color_int = int(color_code)
            if color_int in LDrawColors.colors:
                return LDrawColors.colors[color_int]

        return None

    @staticmethod
    def set_color(color_code, color):
        LDrawColors.colors[color_code] = color

    @staticmethod
    def read_color_table():
        """Reads the color values from the LDConfig.ldr file. For details of the
        Ldraw color system see: http://www.ldraw.org/article/547"""

        if options.use_alt_colors:
            filepath = "LDCfgalt.ldr"
        else:
            filepath = "LDConfig.ldr"

        ldraw_file = LDrawFile(filepath)
        ldraw_file.read_file()
        ldraw_file.parse_file()

    @staticmethod
    def __clamp(value):
        return max(min(value, 1.0), 0.0)

    @classmethod
    def lighten_rgba(cls, color, scale):
        # Moves the linear RGB values closer to white
        # scale = 0 means full white
        # scale = 1 means color stays same
        color = ((1.0 - color[0]) * scale,
                 (1.0 - color[1]) * scale,
                 (1.0 - color[2]) * scale,
                 color[3])
        return (cls.__clamp(1.0 - color[0]),
                cls.__clamp(1.0 - color[1]),
                cls.__clamp(1.0 - color[2]),
                color[3])

    @staticmethod
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

    @staticmethod
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

    @classmethod
    def hex_string_to_linear_rgba(cls, hex_string):
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
                color1 = cls.srgb_to_linear_rgb((r, g, b))
                r = float(int(rgb_str[3], 16)) / 15
                g = float(int(rgb_str[4], 16)) / 15
                b = float(int(rgb_str[5], 16)) / 15
                color2 = cls.srgb_to_linear_rgb((r, g, b))
                return (0.5 * (color1[0] + color2[0]),
                        0.5 * (color1[1] + color2[1]),
                        0.5 * (color1[2] + color2[2]), alpha)

            # String is "RRGGBB" format
            return cls.hex_digits_to_linear_rgba(rgb_str, alpha)
        return None
