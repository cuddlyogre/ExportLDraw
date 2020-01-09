import math
import mathutils

identity = mathutils.Matrix((
    (1.0, 0.0, 0.0, 0.0),
    (0.0, 1.0, 0.0, 0.0),
    (0.0, 0.0, 1.0, 0.0),
    (0.0, 0.0, 0.0, 1.0)
))

rotation = mathutils.Matrix.Rotation(math.radians(-90), 4, 'X')
reverse_rotation = mathutils.Matrix.Rotation(math.radians(90), 4, 'X')

reflection = mathutils.Matrix((
    (1.0, 0.0, 0.0, 0.0),
    (0.0, 1.0, 0.0, 0.0),
    (0.0, 0.0, -1.0, 0.0),
    (0.0, 0.0, 0.0, 1.0)
))

scale = mathutils.Matrix((
    (1.0, 0.0, 0.0, 0.0),
    (0.0, 1.0, 0.0, 0.0),
    (0.0, 0.0, 1.0, 0.0),
    (0.0, 0.0, 0.0, 1.0)
))


def scaled_matrix(gap_scale=1.0):
    return mathutils.Matrix((
        (gap_scale, 0.0, 0.0, 0.0),
        (0.0, gap_scale, 0.0, 0.0),
        (0.0, 0.0, gap_scale, 0.0),
        (0.0, 0.0, 0.0, 1.0)
    ))
