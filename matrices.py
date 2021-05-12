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
