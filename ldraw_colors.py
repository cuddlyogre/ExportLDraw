"""Parses and stores a table of color / material definitions. Converts color space."""

import math
import struct

try:
    from . import helpers
except ImportError as e:
    import helpers


class LDrawColor:
    defaults = {}

    defaults['use_alt_colors'] = True
    use_alt_colors = defaults['use_alt_colors']

    __colors = {}
    __bad_color = None

    @classmethod
    def reset_caches(cls):
        cls.__colors = {}
        cls.__bad_color = None

    def __init__(self):
        self.name = None
        self.code = None
        self.color = None
        self.color_d = None
        self.color_a = None
        self.edge_color = None
        self.edge_color_d = None
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

    @classmethod
    def parse_color(cls, _params):
        color = cls()
        color.parse_color_params(_params)
        cls.__colors[color.code] = color
        return color.code

    @classmethod
    def get_color(cls, color_code):
        if color_code in cls.__colors:
            return cls.__colors[color_code]

        hex_digits = cls.__extract_hex_digits(color_code)
        if hex_digits is not None:
            clean_line = f"0 !COLOUR {color_code} CODE {color_code} VALUE #{hex_digits} EDGE #333333"
            _params = helpers.get_params(clean_line, "0 !COLOUR ", lowercase=False)
            color_code = cls.parse_color(_params)
            return cls.__colors[color_code]

        if cls.__bad_color is None:
            clean_line = f"0 !COLOUR Bad_Color CODE {color_code} VALUE #FF0000 EDGE #00FF00"
            _params = helpers.get_params(clean_line, "0 !COLOUR ", lowercase=False)
            color_code = cls.parse_color(_params)
            cls.__bad_color = cls.__colors[color_code]

        print(f"Bad color code: {color_code}")
        return cls.__colors[cls.__bad_color.code]

    @classmethod
    def lighten_rgba(cls, color, scale):
        # Moves the linear RGB values closer to white
        # scale = 0 means full white
        # scale = 1 means color stays same
        color = (
            (1.0 - color[0]) * scale,
            (1.0 - color[1]) * scale,
            (1.0 - color[2]) * scale,
            color[3]
        )
        return (
            helpers.clamp(1.0 - color[0], 0.0, 1.0),
            helpers.clamp(1.0 - color[1], 0.0, 1.0),
            helpers.clamp(1.0 - color[2], 0.0, 1.0),
            color[3]
        )

    def parse_color_params(self, _params, linear=True):
        # name CODE x VALUE v EDGE e required
        # 0 !COLOUR Black CODE 0 VALUE #1B2A34 EDGE #2B4354

        name = _params[0]
        self.name = name

        # Tags are case-insensitive.
        # https://www.ldraw.org/article/299
        lparams = [x.lower() for x in _params]

        i = lparams.index("code")
        code = lparams[i + 1]
        self.code = code

        i = lparams.index("value")
        value = lparams[i + 1]
        rgb = self.get_color_value(value, linear)
        self.color = rgb
        self.color_d = rgb + (1.0,)

        i = lparams.index("edge")
        edge = lparams[i + 1]
        e_rgb = self.get_color_value(edge, linear)
        self.edge_color = e_rgb
        self.edge_color_d = e_rgb + (1.0,)

        # [ALPHA a] [LUMINANCE l] [ CHROME | PEARLESCENT | RUBBER | MATTE_METALLIC | METAL | MATERIAL <params> ]
        alpha = 255
        if "alpha" in lparams:
            i = lparams.index("alpha")
            alpha = int(lparams[i + 1])
        self.alpha = alpha / 255
        self.color_a = rgb + (self.alpha,)

        luminance = 0
        if "luminance" in lparams:
            i = lparams.index("luminance")
            luminance = int(lparams[i + 1])
        self.luminance = luminance

        material_name = None
        for _material in ["chrome", "pearlescent", "rubber", "matte_metallic", "metal"]:
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
            material_rgba = self.get_color_value(material_value, linear)
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

    # wp-content/plugins/woocommerce/includes/wc-formatting-functions.php
    # line 779
    @staticmethod
    def __is_dark(color):
        r = color[0]
        g = color[1]
        b = color[2]

        # Measure the perceived brightness of color
        brightness = math.sqrt(0.299 * r * r + 0.587 * g * g + 0.114 * b * b)

        # Dark colors have white lines
        return brightness < 0.02

    @staticmethod
    def __is_int(s):
        try:
            int(s)
            return True
        except ValueError:
            return False

    @classmethod
    def get_color_value(cls, value, linear=True):
        hex_digits = cls.__extract_hex_digits(value)
        if linear:
            return cls.__hex_digits_to_linear_rgba(hex_digits)
        else:
            return cls.__hex_digits_to_srgb(hex_digits)

    @classmethod
    def get_rgb_color_value(cls, value):
        hex_digits = cls.__extract_hex_digits(value)
        rgb = cls.__hex_to_rgb(hex_digits)
        return rgb

    @staticmethod
    def __extract_hex_digits(value):
        if value.startswith('#'):
            return value[1:7]
        elif value.lower().startswith('0x2'):
            # some color codes in 973psr.dat are just hex values for the desired color, such as 0x24C4C45
            return value[3:9]
        else:
            try:
                # 10220 - Volkswagen T1 Camper Van.mpd -> 97122.dat has color code 4294967295 which is 0xffffffff in hex
                return hex(int(value))[2:8]
            except ValueError as e:
                """color code is not an int"""

        return None

    @classmethod
    def __hex_digits_to_linear_rgba(cls, hex_digits):
        srgb = cls.__hex_digits_to_srgb(hex_digits)
        linear_rgb = cls.__srgb_to_linear_rgb(srgb)
        return linear_rgb[0], linear_rgb[1], linear_rgb[2]

    @staticmethod
    def __hex_to_rgb(hex_digits):
        return struct.unpack("BBB", bytes.fromhex(hex_digits))

    @staticmethod
    def __rgb_to_srgb(ints):
        srgb = tuple([val / 255 for val in ints])
        return srgb

    @classmethod
    def __hex_digits_to_srgb(cls, hex_digits):
        # String is "RRGGBB" format
        int_tuple = cls.__hex_to_rgb(hex_digits)
        return cls.__rgb_to_srgb(int_tuple)

    @classmethod
    def __srgb_to_linear_rgb(cls, srgb_color):
        (sr, sg, sb) = srgb_color
        r = cls.__srgb_to_rgb_value(sr)
        g = cls.__srgb_to_rgb_value(sg)
        b = cls.__srgb_to_rgb_value(sb)
        return r, g, b

    @staticmethod
    def __srgb_to_rgb_value(value):
        # See https://en.wikipedia.org/wiki/SRGB#The_reverse_transformation
        if value < 0.04045:
            return value / 12.92
        return ((value + 0.055) / 1.055) ** 2.4


if __name__ == "__main__":
    hex_digits = "0x2062E92"
    color_value = LDrawColor.get_color_value(hex_digits)
    print(color_value)
    color_value = LDrawColor.get_rgb_color_value(hex_digits)
    print(color_value)

    print(LDrawColor.get_color_value('#efefef'))
    print(LDrawColor.get_color_value('0x24C4C45'))
    print(LDrawColor.get_color_value('4294967295'))
