import math


class SpecialBricks:
    studs = ["stud.dat", "stud2.dat"]
    logos = ['logo', 'logo2', 'logo3', 'logo4', 'logo5', 'high-contrast']

    slopes = {
        '962.dat': {45},
        '2341.dat': {-45},
        '2449.dat': {-16},
        '2875.dat': {45},
        '2876.dat': {(40, 63)},
        '3037.dat': {45},
        '3038.dat': {45},
        '3039.dat': {45},
        '3040.dat': {45},
        '3041.dat': {45},
        '3042.dat': {45},
        '3043.dat': {45},
        '3044.dat': {45},
        '3045.dat': {45},
        '3046.dat': {45},
        '3048.dat': {45},
        '3049.dat': {45},
        '3135.dat': {45},
        '3297.dat': {63},
        '3298.dat': {63},
        '3299.dat': {63},
        '3300.dat': {63},
        '3660.dat': {-45},
        '3665.dat': {-45},
        '3675.dat': {63},
        '3676.dat': {-45},
        '3678b.dat': {24},
        '3684.dat': {15},
        '3685.dat': {16},
        '3688.dat': {15},
        '3747.dat': {-63},
        '3747b.dat': {-63},
        '4089.dat': {-63},
        '4161.dat': {63},
        '4286.dat': {63},
        '4287.dat': {-63},
        '4445.dat': {45},
        '4460.dat': {16},
        '4509.dat': {63},
        '4854.dat': {-45},
        '4856.dat': {(-60, -70), -45},
        '4857.dat': {45},
        '4858.dat': {72},
        '4861.dat': {45, 63},
        '4871.dat': {-45},
        '4885.dat': {72},  # blank
        '6069.dat': {72, 45},
        '6153.dat': {(60, 70), (26, 34)},
        '6227.dat': {45},
        '6270.dat': {45},
        '13269.dat': {(40, 63)},
        '13548.dat': {(45, 35)},
        '15571.dat': {45},
        '18759.dat': {-45},
        '22390.dat': {(40, 55)},  # blank
        '22391.dat': {(40, 55)},
        '22889.dat': {-45},
        '28192.dat': {45},  # blank
        '30180.dat': {47},
        '30182.dat': {45},
        '30183.dat': {-45},
        '30249.dat': {35},
        '30283.dat': {-45},
        '30363.dat': {72},
        '30373.dat': {-24},
        '30382.dat': {11, 45},
        '30390.dat': {-45},
        '30499.dat': {16},
        '32083.dat': {45},
        '43708.dat': {(64, 72)},
        '43710.dat': {72, 45},
        '43711.dat': {72, 45},
        '47759.dat': {(40, 63)},
        '52501.dat': {-45},
        '60219.dat': {-45},
        '60477.dat': {72},
        '60481.dat': {24},
        '63341.dat': {45},
        '72454.dat': {-45},
        '92946.dat': {45},
        '93348.dat': {72},
        '95188.dat': {65},
        '99301.dat': {63},
        '303923.dat': {45},
        '303926.dat': {45},
        '304826.dat': {45},
        '329826.dat': {64},
        '374726.dat': {-64},
        '428621.dat': {64},
        '4162628.dat': {17},
        '4195004.dat': {45},
    }

    slope_angles = {}

    lights = {
        '62930.dat': (1.0, 0.373, 0.059, 1.0),
        '54869.dat': (1.0, 0.052, 0.017, 1.0),
    }

    @classmethod
    def reset_caches(cls):
        cls.slope_angles = {}

    @staticmethod
    def build_slope_angles():
        SpecialBricks.reset_caches()

        # Create a regular dictionary of parts with ranges of angles to check
        margin = 5  # Allow 5 degrees either way to compensate for measuring inaccuracies

        for part in SpecialBricks.slopes:
            SpecialBricks.slope_angles[part] = {(c - margin, c + margin) if type(c) is not tuple else (min(c) - margin, max(c) + margin) for c in SpecialBricks.slopes[part]}

        # for part in SpecialBricks.slopes:
        #     for c in SpecialBricks.slopes[part]:
        #         if type(c) is not tuple:
        #             SpecialBricks.slope_angles[part] = {(c - margin, c + margin)}
        #         else:
        #             SpecialBricks.slope_angles[part] = (min(c) - margin, max(c) + margin)

    @staticmethod
    def is_slope_face(part_number, face):
        if part_number not in SpecialBricks.slope_angles:
            return

        # Step 2: Calculate angle of face normal to the ground
        face_normal = face.normal.normalized()

        # Clamp value to range -1 to 1 (ensure we are in the strict range of the acos function, taking account of rounding errors)
        cosine = min(max(face_normal.y, -1.0), 1.0)
        # cosine = min(max(-face_normal.z, -1.0), 1.0)

        # Calculate angle of face normal to the ground (-90 to 90 degrees)
        angle_to_ground_degrees = math.degrees(math.acos(cosine)) - 90

        # debugPrint("Angle to ground {0}".format(angleToGroundDegrees))

        # Step 3: Check angle of normal to ground is within one of the acceptable ranges for this part
        if True in {c[0] <= angle_to_ground_degrees <= c[1] for c in SpecialBricks.slope_angles[part_number]}:
            return True

        return False
