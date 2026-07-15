import mathutils

import math
import uuid

from . import helpers

texmap_prefix = "0 !: "


def is_texmap_line(line):
    return line.startswith(texmap_prefix)


def clean_line(line):
    # strip only a leading "0 !: " so occurrences inside comments or filenames are untouched
    _line = line.lstrip()
    if _line.startswith(texmap_prefix):
        return _line[len(texmap_prefix):]
    return line


# https://github.com/trevorsandy/lpub3d/blob/e7c39cd3df518cf16521dc2c057a9f125cc3b5c3/lclib/common/lc_meshloader.h#L56
# https://github.com/trevorsandy/lpub3d/blob/e7c39cd3df518cf16521dc2c057a9f125cc3b5c3/lclib/common/lc_meshloader.cpp#L12
# https://github.com/trevorsandy/lpub3d/blob/e7c39cd3df518cf16521dc2c057a9f125cc3b5c3/lclib/common/lc_meshloader.cpp#L1486
# https://stackoverflow.com/questions/53970131/how-to-find-the-clockwise-angle-between-two-vectors-in-python#53970746
class TexMap:
    def __init__(self, method=None):
        self.id = str(uuid.uuid4())
        self.method = method
        self.parameters = None
        self.image_name = None
        self.glossmap_image_name = None

    def is_planar(self):
        return self.method == 'PLANAR'

    def is_cylindrical(self):
        return self.method == 'CYLINDRICAL'

    def is_spherical(self):
        return self.method == 'SPHERICAL'

    def wraps_full_circle(self):
        """
        True for cylindrical/spherical textures that span the full 360 circumference. The
        seam fix in the uv mapping pushes the seam-straddling face's u slightly outside 0..1,
        so the material must wrap u (fract) for that face to sample the wrapped texel instead
        of clipping to transparent, which would leave a hairline of bare part color at the seam.
        """
        if self.is_cylindrical() or self.is_spherical():
            return self.parameters is not None and abs(self.parameters[3]) >= 360.0
        return False

    def uv_unwrap_face(self, bm, face):
        if self.is_planar():
            self.__map_planar(bm, face)
        elif self.is_cylindrical():
            self.__map_cylindrical(bm, face)
        elif self.is_spherical():
            self.__map_spherical(bm, face)

    # https://www.ldraw.org/texmap-spec.html
    # the three points are corners of the texture: point 1 is the origin, point 1 -> point 2 is the
    # u axis and point 1 -> point 3 is the v axis. u and v are the distances from the planes through
    # point 1 (with those edge vectors as normals) divided by the length of the respective edge.
    def __map_planar(self, bm, face):
        a = self.parameters[0]
        b = self.parameters[1]
        c = self.parameters[2]

        ab = b - a
        ac = c - a

        p1_length = ab.length
        p1_normal = ab / p1_length

        p2_length = ac.length
        p2_normal = ac / p2_length

        # https://blender.stackexchange.com/a/53808
        # https://blender.stackexchange.com/questions/53709/bmesh-how-to-map-vertex-based-uv-coordinates-to-loops
        uv_layer = bm.loops.layers.uv.verify()
        uvs = {}
        for loop in face.loops:
            p = loop.vert.co.copy().freeze()
            if p not in uvs:
                du = p1_normal.dot(p - a) / p1_length
                dv = p2_normal.dot(p - a) / p2_length
                # flip v: LDraw texture origin is top-left, Blender's uv origin is bottom-left
                uvs[p] = [du, 1.0 - dv]
            loop[uv_layer].uv = uvs[p]

    # https://www.ldraw.org/texmap-spec.html
    # point 1 is the bottom center of the cylinder, point 2 the top center, point 3 a location on
    # the outer edge of the bottom where the center-bottom of the texture touches. u is the angle
    # around the axis (extents -a/2 .. a/2); v is the distance from the base plane over the height.
    def __map_cylindrical(self, bm, face):
        a = self.parameters[0]
        b = self.parameters[1]
        c = self.parameters[2]
        angle1 = self.parameters[3]

        axis = b - a
        axis_length = axis.length
        axis_n = axis / axis_length if axis_length != 0 else mathutils.Vector((0.0, 0.0, 1.0))
        # radial direction from the axis toward point 3 (the spec measures u as the angle between the
        # vectors from point 1 to point 3 and from point 1 to the point). project out any axial
        # component so u is measured purely around the axis -- otherwise the texture gets squeezed.
        front = c - a
        front = (front - axis_n * front.dot(axis_n)).normalized()
        plane_2_n = axis_n.cross(front).normalized()
        # planes referenced to bottom (point 1) so v=0 at base
        front_plane = mathutils.Vector(tuple(front) + (-front.dot(a),))
        plane_1 = mathutils.Vector(tuple(axis_n) + (-axis_n.dot(a),))
        plane_2 = mathutils.Vector(tuple(plane_2_n) + (-plane_2_n.dot(a),))
        angle_1 = 360.0 / angle1 if angle1 != 0 else 1.0

        uv_layer = bm.loops.layers.uv.verify()
        raw_uvs = []
        for loop in face.loops:
            p = loop.vert.co
            # project the point onto the base plane, then measure its angle around the axis.
            # homogeneous (w=1) vectors keep the plane offsets in the dot products so the angle
            # is measured relative to the axis rather than the world origin
            dot_plane_1 = mathutils.Vector((p[0], p[1], p[2], 1.0)).dot(plane_1)
            point_in_plane_1 = p - mathutils.Vector((plane_1[0], plane_1[1], plane_1[2])) * dot_plane_1
            dot_front_plane = mathutils.Vector((point_in_plane_1[0], point_in_plane_1[1], point_in_plane_1[2], 1.0)).dot(front_plane)
            dot_plane_2 = mathutils.Vector((point_in_plane_1[0], point_in_plane_1[1], point_in_plane_1[2], 1.0)).dot(plane_2)

            _angle_1 = math.atan2(dot_plane_2, dot_front_plane) / math.pi * angle_1
            du = 0.5 + 0.5 * _angle_1
            # v distance from base plane over height (0 at point1 bottom, 1 at top)
            height_frac = dot_plane_1 / axis_length
            # use height_frac directly for final v to match prior behavior (image bottom at cyl bottom)
            # flip v: LDraw texture origin is top-left, Blender's uv origin is bottom-left
            raw_uvs.append([du, height_frac])

        # fix u discontinuity for the face that straddles the atan2 branch cut (the texture seam)
        fixed_uvs = []
        if raw_uvs:
            u0 = raw_uvs[0][0]
            for du, dv in raw_uvs:
                du_adj = du
                while du_adj - u0 > 0.5:
                    du_adj -= 1.0
                while du_adj - u0 < -0.5:
                    du_adj += 1.0
                fixed_uvs.append([du_adj, dv])

        for uv, loop in zip(fixed_uvs, face.loops):
            loop[uv_layer].uv = uv

    # https://www.ldraw.org/texmap-spec.html
    # point 1 is the center of the sphere, point 2 the point the texture center touches, point 3
    # forms plane 1 that bisects the texture horizontally. u is the longitude angle within plane 1
    # (extents -a/2 .. a/2); v is the latitude angle out of plane 1 (extents -b/2 .. b/2).
    def __map_spherical(self, bm, face):
        a = self.parameters[0]
        b = self.parameters[1]
        c = self.parameters[2]
        angle1 = self.parameters[3]
        angle2 = self.parameters[4]

        front = (b - a).normalized()
        plane_1_normal = front.cross(c - a).normalized()
        plane_2_normal = plane_1_normal.cross(front).normalized()
        front_plane = mathutils.Vector(tuple(front) + (-front.dot(a),))
        center = a
        plane_1 = mathutils.Vector(tuple(plane_1_normal) + (-plane_1_normal.dot(a),))
        plane_2 = mathutils.Vector(tuple(plane_2_normal) + (-plane_2_normal.dot(a),))
        angle_1 = 360.0 / angle1 if angle1 != 0 else 1.0
        angle_2 = 180.0 / angle2 if angle2 != 0 else 1.0

        uv_layer = bm.loops.layers.uv.verify()
        raw_uvs = []
        pole_indices = []
        for i, loop in enumerate(face.loops):
            p = loop.vert.co
            vertex_direction = p - center
            r = vertex_direction.length

            if r == 0.0:
                raw_uvs.append([0.5, 0.5])
                continue

            # homogeneous (w=1) vectors keep the plane offsets in the dot products so the angles
            # are measured relative to the sphere center rather than the world origin
            dot_plane_1 = mathutils.Vector((p[0], p[1], p[2], 1.0)).dot(plane_1)
            point_in_plane_1 = p - mathutils.Vector((plane_1[0], plane_1[1], plane_1[2])) * dot_plane_1
            dot_front_plane = mathutils.Vector((point_in_plane_1[0], point_in_plane_1[1], point_in_plane_1[2], 1.0)).dot(front_plane)
            dot_plane_2 = mathutils.Vector((point_in_plane_1[0], point_in_plane_1[1], point_in_plane_1[2], 1.0)).dot(plane_2)

            _angle_1 = math.atan2(dot_plane_2, dot_front_plane) / math.pi * angle_1
            du = 0.5 + 0.5 * _angle_1
            # clamp guards against asin domain errors from floating point rounding at the poles
            _angle_2 = math.asin(helpers.clamp(dot_plane_1 / r, -1.0, 1.0)) / math.pi * angle_2
            dv = 0.5 - _angle_2
            # flip v: LDraw texture origin is top-left, Blender's uv origin is bottom-left
            raw_uvs.append([du, 1.0 - dv])

            if abs(dot_plane_1 / r) > 0.999:
                pole_indices.append(i)

        # fix u discontinuity for the face that straddles the atan2 branch cut (the texture seam)
        # additionally handle poles: pole vertices have undefined longitude (atan2(0,0) -> 0.5);
        # set their u to the average of the face's other (adjusted) u values so polar triangles
        # converge correctly instead of smearing half the texture.
        fixed_uvs = [[du, dv] for du, dv in raw_uvs]
        if raw_uvs:
            # prefer a non-pole vertex for the base u0 so adjustment is local to visible longitudes
            non_pole = [i for i in range(len(raw_uvs)) if i not in pole_indices]
            u0 = raw_uvs[non_pole[0]][0] if non_pole else raw_uvs[0][0]

            for i in range(len(raw_uvs)):
                if i in pole_indices:
                    continue
                du = raw_uvs[i][0]
                du_adj = du
                while du_adj - u0 > 0.5:
                    du_adj -= 1.0
                while du_adj - u0 < -0.5:
                    du_adj += 1.0
                fixed_uvs[i][0] = du_adj

            # override pole u to be consistent with its face's sector (average of non-pole corners)
            for i in pole_indices:
                others = [fixed_uvs[j][0] for j in range(len(fixed_uvs)) if j != i]
                if others:
                    fixed_uvs[i][0] = sum(others) / len(others)

        for uv, loop in zip(fixed_uvs, face.loops):
            loop[uv_layer].uv = uv
