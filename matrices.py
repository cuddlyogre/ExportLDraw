import math
import mathutils

# import numpy as np

using_np = 'np' in globals()


def Vector(array):
    if using_np:
        return np.array(array)
    else:
        return mathutils.Vector(array)


def Vector4(array):
    if using_np:
        return np.array(array + (1.0,))
    else:
        return mathutils.Vector(array + (1.0,))


def Matrix(array):
    if using_np:
        return np.array(array)
    else:
        return mathutils.Matrix(array)


def set_matrix_world(obj, matrix_world):
    if using_np:
        obj.matrix_world[0] = matrix_world[0]
        obj.matrix_world[1] = matrix_world[1]
        obj.matrix_world[2] = matrix_world[2]
        obj.matrix_world[3] = matrix_world[3]
    else:
        obj.matrix_world = matrix_world


# https://www.kite.com/python/answers/how-to-normalize-an-array-in-numpy-in-python
def normalize(vector):
    if using_np:
        norm = np.linalg.norm(vector)
        normal_array = vector / norm
        return normal_array
    else:
        return vector.normalized()


def determinant(matrix):
    if using_np:
        pass
    else:
        return matrix.determinant()


def is_degenerate(matrix):
    if using_np:
        pass
    else:
        return determinant(matrix) == 0


def is_reversed(matrix):
    if using_np:
        pass
    else:
        return determinant(matrix) < 0


# https://stackoverflow.com/questions/9171158/how-do-you-get-the-magnitude-of-a-vector-in-numpy
def length(vector):
    if using_np:
        return math.sqrt(vector[0] ** 2 + vector[1] ** 2 + vector[2] ** 2)
        return np.sqrt(vector.dot(vector))
        return np.linalg.norm(vector)
    else:
        return vector.length


def dot(a, b):
    if using_np:
        return np.dot(a, b)
    else:
        return a.dot(b)


def cross(a, b):
    if using_np:
        return np.cross(a, b)
    else:
        return a.cross(b)


identity = Matrix((
    (1.0, 0.0, 0.0, 0.0),
    (0.0, 1.0, 0.0, 0.0),
    (0.0, 0.0, 1.0, 0.0),
    (0.0, 0.0, 0.0, 1.0)
)).freeze()

rotation = mathutils.Matrix.Rotation(math.radians(-90), 4, 'X').freeze()
# rotation = Matrix((
#     (1.0, 0.0, 0.0, 0.0),
#     (0.0, -4.371138828673793e-08, 1.0, 0.0),
#     (0.0, -1.0, -4.371138828673793e-08, 0.0),
#     (0.0, 0.0, 0.0, 1.0)
# ))

reverse_rotation = mathutils.Matrix.Rotation(math.radians(90), 4, 'X').freeze()
# reverse_rotation = Matrix((
#     (1.0, 0.0, 0.0, 0.0),
#     (0.0, 7.549790126404332e-08, -1.0, 0.0),
#     (0.0, 1.0, 7.549790126404332e-08, 0.0),
#     (0.0, 0.0, 0.0, 1.0)
# ))

reflection = Matrix((
    (1.0, 0.0, 0.0, 0.0),
    (0.0, 1.0, 0.0, 0.0),
    (0.0, 0.0, -1.0, 0.0),
    (0.0, 0.0, 0.0, 1.0)
)).freeze()


def scaled_matrix(scale=1.0):
    return Matrix((
        (scale, 0.0, 0.0, 0.0),
        (0.0, scale, 0.0, 0.0),
        (0.0, 0.0, scale, 0.0),
        (0.0, 0.0, 0.0, scale)
    )).freeze()


def mt4(matrix):
    if using_np:
        return np.array((
            matrix[0],
            matrix[1],
            matrix[2],
            matrix[3],
        ))
    else:
        return matrix


# https://stackoverflow.com/a/48266808
def unit_vector(vector):
    """ Returns the unit vector of the vector."""
    return vector / np.linalg.norm(vector)


def angle_between(v1, v2):
    """Finds angle between two vectors"""
    v1_u = unit_vector(v1)
    v2_u = unit_vector(v2)
    return np.arccos(np.clip(np.dot(v1_u, v2_u), -1.0, 1.0))


def x_rotation(vector, theta):
    """Rotates 3-D vector around x-axis"""
    R = np.array([[1, 0, 0], [0, np.cos(theta), -np.sin(theta)], [0, np.sin(theta), np.cos(theta)]])
    return np.dot(R, vector)


def y_rotation(vector, theta):
    """Rotates 3-D vector around y-axis"""
    R = np.array([[np.cos(theta), 0, np.sin(theta)], [0, 1, 0], [-np.sin(theta), 0, np.cos(theta)]])
    return np.dot(R, vector)


def z_rotation(vector, theta):
    """Rotates 3-D vector around z-axis"""
    R = np.array([[np.cos(theta), -np.sin(theta), 0], [np.sin(theta), np.cos(theta), 0], [0, 0, 1]])
    return np.dot(R, vector)
