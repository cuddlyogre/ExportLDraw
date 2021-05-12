import math
import numpy as np

identity = np.array((
    (1.0, 0.0, 0.0, 0.0),
    (0.0, 1.0, 0.0, 0.0),
    (0.0, 0.0, 1.0, 0.0),
    (0.0, 0.0, 0.0, 1.0)
))

# rotation = mathutils.Matrix.Rotation(math.radians(-90), 4, 'X')
rotation = np.array((
    (1.0, 0.0, 0.0, 0.0),
    (0.0, -4.371138828673793e-08, 1.0, 0.0),
    (0.0, -1.0, -4.371138828673793e-08, 0.0),
    (0.0, 0.0, 0.0, 1.0)
))

# reverse_rotation = mathutils.Matrix.Rotation(math.radians(90), 4, 'X')
reverse_rotation = np.array((
    (1.0, 0.0, 0.0, 0.0),
    (0.0, 7.549790126404332e-08, -1.0, 0.0),
    (0.0, 1.0, 7.549790126404332e-08, 0.0),
    (0.0, 0.0, 0.0, 1.0)
))

reflection = np.array((
    (1.0, 0.0, 0.0, 0.0),
    (0.0, 1.0, 0.0, 0.0),
    (0.0, 0.0, -1.0, 0.0),
    (0.0, 0.0, 0.0, 1.0)
))


# https://www.kite.com/python/answers/how-to-normalize-an-array-in-numpy-in-python
def normalize(an_array):
    norm = np.linalg.norm(an_array)
    normal_array = an_array / norm
    return normal_array


# https://stackoverflow.com/questions/9171158/how-do-you-get-the-magnitude-of-a-vector-in-numpy
def length(vector):
    return math.sqrt(vector[0] ** 2 + vector[1] ** 2 + vector[2] ** 2)
    return np.sqrt(vector.dot(vector))
    return np.linalg.norm(vector)


def scaled_matrix(scale=1.0):
    return np.array((
        (scale, 0.0, 0.0, 0.0),
        (0.0, scale, 0.0, 0.0),
        (0.0, 0.0, scale, 0.0),
        (0.0, 0.0, 0.0, scale)
    ))


def mt4(matrix):
    return np.array((
        matrix[0],
        matrix[1],
        matrix[2],
        matrix[3],
    ))
