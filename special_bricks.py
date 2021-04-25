import math

studs = ["stud.dat", "stud2.dat"]
logos = ["logo", "logo2", "logo3", "logo4", "logo5", "high-contrast"]
slopes = {
    '962.dat': {45},
    '2341.dat': {-45},
    '2449.dat': {-16},
    '2875.dat': {45},
    '2876.dat': {(40, 63)},

    '3037.dat': {45},
    '3037d01.dat': {45},
    '3037d50.dat': {45},
    '3037d51.dat': {45},
    '3037d52.dat': {45},
    '3037d53.dat': {45},
    '3037dq0.dat': {45},
    '3037p05.dat': {45},
    '3037pc0.dat': {45},
    '3037ps0.dat': {45},
    '3037ps1.dat': {45},
    '3037ps2.dat': {45},
    '3037ps3.dat': {45},
    '3037ps4.dat': {45},

    '3038.dat': {45},
    '3038p01.dat': {45},

    '3039.dat': {45},
    '3039p01.dat': {45},
    '3039p02.dat': {45},
    '3039p03.dat': {45},
    '3039p04.dat': {45},
    '3039p05.dat': {45},
    '3039p06.dat': {45},
    '3039p07.dat': {45},
    '3039p08.dat': {45},
    '3039p09.dat': {45},
    '3039p0u.dat': {45},
    '3039p10.dat': {45},
    '3039p11.dat': {45},
    '3039p12.dat': {45},
    '3039p13.dat': {45},
    '3039p15.dat': {45},
    '3039p16.dat': {45},
    '3039p23.dat': {45},
    '3039p32.dat': {45},
    '3039p33.dat': {45},
    '3039p34.dat': {45},
    '3039p58.dat': {45},
    '3039p67.dat': {45},
    '3039p68.dat': {45},
    '3039p70.dat': {45},
    '3039p71.dat': {45},
    '3039p72.dat': {45},
    '3039p73.dat': {45},
    '3039p74.dat': {45},
    '3039p75.dat': {45},
    '3039p76.dat': {45},
    '3039pa0.dat': {45},
    '3039pc0.dat': {45},
    '3039pc1.dat': {45},
    '3039pc2.dat': {45},
    '3039pc3.dat': {45},
    '3039pc4.dat': {45},
    '3039pc5.dat': {45},
    '3039pc6.dat': {45},
    '3039pc7.dat': {45},
    '3039pc8.dat': {45},
    '3039pc9.dat': {45},
    '3039pca.dat': {45},
    '3039pcb.dat': {45},
    '3039pcc.dat': {45},
    '3039pcd.dat': {45},
    '3039pce.dat': {45},
    '3039pcf.dat': {45},
    '3039pcg.dat': {45},
    '3039pch.dat': {45},
    '3039ph1.dat': {45},
    '3039ph2.dat': {45},
    '3039ps1.dat': {45},
    '3039ps2.dat': {45},
    '3039ps3.dat': {45},
    '3039ps4.dat': {45},
    '3039ps5.dat': {45},
    '3039pt1.dat': {45},
    '3039pt2.dat': {45},
    '3039pt3.dat': {45},
    '3039pt4.dat': {45},

    '3040.dat': {45},
    '3040a.dat': {45},
    '3040b.dat': {45},
    '3040p01.dat': {45},
    '3040p02.dat': {45},
    '3040p03.dat': {45},
    '3040p04.dat': {45},
    '3040p05.dat': {45},
    '3040p06.dat': {45},
    '3040p32.dat': {45},
    '3040p33.dat': {45},
    '3040p58.dat': {45},

    '3041.dat': {45},
    '3041p01.dat': {45},

    '3042.dat': {45},
    '3043.dat': {45},

    '3044.dat': {45},
    '3044a.dat': {45},
    '3044b.dat': {45},
    '3044c.dat': {45},

    '3045.dat': {45},
    '3046.dat': {45},

    '3048.dat': {45},
    '3048a.dat': {45},
    '3048b.dat': {45},

    '3049.dat': {45},
    '3049a.dat': {45},
    '3049b.dat': {45},
    '3049c.dat': {45},

    '3135.dat': {45},
    '3135c01.dat': {45},
    '3135c02.dat': {45},
    '3135c03.dat': {45},

    '3297.dat': {63},
    '3297p01.dat': {63},
    '3297p02.dat': {63},
    '3297p03.dat': {63},
    '3297p04.dat': {63},
    '3297p05.dat': {63},
    '3297p06.dat': {63},
    '3297p10.dat': {63},
    '3297p11.dat': {63},
    '3297p14.dat': {63},
    '3297p15.dat': {63},
    '3297p90.dat': {63},
    '3297ps1.dat': {63},

    '3298.dat': {63},
    '3298p01.dat': {63},
    '3298p04.dat': {63},
    '3298p10.dat': {63},
    '3298p11.dat': {63},
    '3298p12.dat': {63},
    '3298p13.dat': {63},
    '3298p15.dat': {63},
    '3298p16.dat': {63},
    '3298p17.dat': {63},
    '3298p18.dat': {63},
    '3298p19.dat': {63},
    '3298p1a.dat': {63},
    '3298p1b.dat': {63},
    '3298p20.dat': {63},
    '3298p21.dat': {63},
    '3298p53.dat': {63},
    '3298p54.dat': {63},
    '3298p55.dat': {63},
    '3298p56.dat': {63},
    '3298p57.dat': {63},
    '3298p61.dat': {63},
    '3298p66.dat': {63},
    '3298p67.dat': {63},
    '3298p68.dat': {63},
    '3298p69.dat': {63},
    '3298p6u.dat': {63},
    '3298p71.dat': {63},
    '3298p72.dat': {63},
    '3298p73.dat': {63},
    '3298p74.dat': {63},
    '3298p75.dat': {63},
    '3298p76.dat': {63},
    '3298p90.dat': {63},
    '3298pa0.dat': {63},
    '3298ps0.dat': {63},
    '3298ps1.dat': {63},
    '3298ps2.dat': {63},

    '3299.dat': {63},
    '3300.dat': {63},

    '3660.dat': {-45},
    '3660p01.dat': {-45},
    '3660p02.dat': {-45},
    '3660p03.dat': {-45},

    '3665.dat': {-45},
    '3665a.dat': {-45},
    '3665b.dat': {-45},

    '3675.dat': {63},

    '3676.dat': {-45},

    '3678.dat': {24},
    '3678a.dat': {24},
    '3678ad01.dat': {24},
    '3678ap01.dat': {24},
    '3678ap4h.dat': {24},
    '3678apc0.dat': {24},
    '3678b.dat': {24},
    '3678bp4w.dat': {24},
    '3678bp4x.dat': {24},
    '3678bph1.dat': {24},
    '3678bpk0.dat': {24},
    '3678p01.dat': {24},
    '3678p4h.dat': {24},
    '3678pc0.dat': {24},

    '3684.dat': {15},
    '3684a.dat': {15},
    '3684adq0.dat': {15},
    '3684adq1.dat': {15},
    '3684adq2.dat': {15},
    '3684adq3.dat': {15},
    '3684ap22.dat': {15},
    '3684c.dat': {15},
    '3684p22.dat': {15},

    '3685.dat': {16},
    '3688.dat': {15},

    '3747.dat': {-63},
    '3747a.dat': {-63},
    '3747b.dat': {-63},

    '4089.dat': {-63},
    '4161.dat': {63},
    '4286.dat': {63},

    '4287.dat': {-63},
    '4287a.dat': {-63},
    '4287b.dat': {-63},
    '4287c.dat': {-63},

    '4445.dat': {45},
    '4445d01.dat': {45},
    '4445d02.dat': {45},

    '4460.dat': {16},
    '4460a.dat': {16},
    '4460b.dat': {16},

    '4509.dat': {63},
    '4854.dat': {-45},
    '4856.dat': {(-60, -70), -45},
    '4857.dat': {45},

    '4858.dat': {72},
    '4858p01.dat': {72},
    '4858p1k.dat': {72},
    '4858p90.dat': {72},
    '4858px4.dat': {72},

    '4867.dat': {72},
    '4867p10.dat': {72},

    '4861.dat': {45, 63},
    '4871.dat': {-45},
    '4885.dat': {72},  # blank

    '6069.dat': {72, 45},
    '6069p01.dat': {72, 45},
    '6069p101.dat': {72, 45},
    '6069ps1.dat': {72, 45},
    '6069ps2.dat': {72, 45},
    '6069ps3.dat': {72, 45},

    '48933.dat': {72, 45},
    '48933ps1.dat': {72, 45},

    '6153.dat': {(60, 70), (26, 34)},
    '6153a.dat': {(60, 70), (26, 34)},
    '6153ap7a.dat': {(60, 70), (26, 34)},
    '6153b.dat': {(60, 70), (26, 34)},
    '6153p7a.dat': {(60, 70), (26, 34)},

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
    '30180p01.dat': {47},
    '30180p02.dat': {47},

    '30182.dat': {45},

    '30183.dat': {-45},
    '30183p01.dat': {-45},

    '30249.dat': {35},
    '30249ps0.dat': {35},

    '30283.dat': {-45},

    '30363.dat': {72},
    '30363p90.dat': {72},
    '30363ps1.dat': {72},
    '30363ps2.dat': {72},

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

    '23949.dat': {45},
    '32802.dat': {45},
    '44571.dat': {45},
    '48165.dat': {45},
    '42862.dat': {45},
    '29115.dat': {(-45, -18)},
    '49618.dat': {67},

    # obsolete
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

# bulbs
# 11013.dat
# 11177.dat
# 11178.dat
# 55972.dat
# 62503.dat
# 64897.dat
# '62930.dat' 47 -> 18 62503.dat
# '54869.dat' 47 -> 36 62503.dat

lights = {
    '62930.dat': (1.0, 0.373, 0.059, 1.0),
    '54869.dat': (1.0, 0.052, 0.017, 1.0),
}


def reset_caches():
    global slope_angles
    slope_angles = {}


def build_slope_angles():
    reset_caches()

    # Create a regular dictionary of parts with ranges of angles to check
    margin = 5  # Allow 5 degrees either way to compensate for measuring inaccuracies

    for part in slopes:
        slope_angle = set()
        for c in slopes[part]:
            if type(c) is tuple:
                slope_angle.add((min(c) - margin, max(c) + margin))
            else:
                slope_angle.add((c - margin, c + margin))
        slope_angles[part] = slope_angle


def is_slope_part(part_number):
    return part_number in slope_angles


def normal_to_angle(normal):
    normal = normal.normalized()

    # Clamp value to range -1 to 1 (ensure we are in the strict range of the acos function, taking account of rounding errors)
    cosine = min(max(normal.y, -1.0), 1.0)

    # Calculate angle of face normal to the ground (-90 to 90 degrees)
    angle_to_ground_degrees = math.degrees(math.acos(cosine)) - 90
    return angle_to_ground_degrees


def is_slope_face(part_number, face):
    if not is_slope_part(part_number):
        return

    angle_to_ground_degrees = normal_to_angle(face.normal)

    # Check angle of normal to ground is within one of the acceptable ranges for this part
    for c in slope_angles[part_number]:
        if c[0] <= angle_to_ground_degrees <= c[1]:
            return True
    return False
