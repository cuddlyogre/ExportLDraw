import os
import re
import math
import struct


class LDrawColors:
    """Parses and stores a table of color / material definitions. Converts color space."""

    colors = {}

    # if this is made a classmethod, BlenderMaterials sees colors as empty
    @staticmethod
    def read_color_table(ldraw_path, use_alt=False):
        """Reads the color values from the LDConfig.ldr file. For details of the
        Ldraw color system see: http://www.ldraw.org/article/547"""
        if use_alt:
            config_filename = "LDCfgalt.ldr"
        else:
            config_filename = "LDConfig.ldr"

        config_filepath = os.path.join(ldraw_path, config_filename)

        ldconfig_lines = ""
        if os.path.exists(config_filepath):
            with open(config_filepath, "rt", encoding="utf_8") as ldconfig:
                ldconfig_lines = ldconfig.readlines()

        for line in ldconfig_lines:
            if len(line) > 3:
                if line[2:4].lower() == '!c':
                    line_split = line.split()

                    name = line_split[2]
                    code = int(line_split[4])
                    linear_rgba = LDrawColors.hex_digits_to_linear_rgba(line_split[6][1:], 1.0)

                    color = {
                        "name": name,
                        "color": linear_rgba[0:3],
                        "alpha": linear_rgba[3],
                        "luminance": 0.0,
                        "material": "BASIC"
                    }

                    if "ALPHA" in line_split:
                        color["alpha"] = int(LDrawColors.__get_value(line_split, "ALPHA")) / 256.0

                    if "LUMINANCE" in line_split:
                        color["luminance"] = int(LDrawColors.__get_value(line_split, "LUMINANCE"))

                    if "CHROME" in line_split:
                        color["material"] = "CHROME"

                    if "PEARLESCENT" in line_split:
                        color["material"] = "PEARLESCENT"

                    if "RUBBER" in line_split:
                        color["material"] = "RUBBER"

                    if "METAL" in line_split:
                        color["material"] = "METAL"

                    if "MATERIAL" in line_split:
                        subline = line_split[line_split.index("MATERIAL"):]

                        color["material"] = LDrawColors.__get_value(subline, "MATERIAL")
                        hex_digits = LDrawColors.__get_value(subline, "VALUE")[1:]
                        color["secondary_color"] = LDrawColors.hex_digits_to_linear_rgba(hex_digits, 1.0)
                        color["fraction"] = LDrawColors.__get_value(subline, "FRACTION")
                        color["vfraction"] = LDrawColors.__get_value(subline, "VFRACTION")
                        color["size"] = LDrawColors.__get_value(subline, "SIZE")
                        color["minsize"] = LDrawColors.__get_value(subline, "MINSIZE")
                        color["maxsize"] = LDrawColors.__get_value(subline, "MAXSIZE")

                    LDrawColors.colors[code] = color

        # Color Space Management: Convert these sRGB color values to Blender's linear RGB color space
        for key in LDrawColors.colors:
            LDrawColors.colors[key]["color"] = LDrawColors.srgb_to_linear_rgb(LDrawColors.colors[key]["color"])

    @staticmethod
    def __clamp(value):
        return max(min(value, 1.0), 0.0)

    @staticmethod
    def __get_value(line, value):
        """Parses a color value from the ldConfig.ldr file"""
        if value in line:
            n = line.index(value)
            return line[n + 1]

    @staticmethod
    def __srgb_to_rgb_value(value):
        # See https://en.wikipedia.org/wiki/SRGB#The_reverse_transformation
        if value < 0.04045:
            return value / 12.92
        return ((value + 0.055) / 1.055) ** 2.4

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
    def srgb_to_linear_rgb(cls, srgb_color):
        # See https://en.wikipedia.org/wiki/SRGB#The_reverse_transformation
        (sr, sg, sb) = srgb_color
        r = cls.__srgb_to_rgb_value(sr)
        g = cls.__srgb_to_rgb_value(sg)
        b = cls.__srgb_to_rgb_value(sb)
        return r, g, b

    @classmethod
    def hex_digits_to_linear_rgba(cls, hex_digits, alpha):
        # String is "RRGGBB" format
        int_tuple = struct.unpack('BBB', bytes.fromhex(hex_digits))
        srgb = tuple([val / 255 for val in int_tuple])
        linear_rgb = cls.srgb_to_linear_rgb(srgb)
        return linear_rgb[0], linear_rgb[1], linear_rgb[2], alpha

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

    @classmethod
    def __overwrite_color(cls, index, color):
        if index in cls.colors:
            cls.colors[index]["color"] = color

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
