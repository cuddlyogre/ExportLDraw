import bpy
import os
from pathlib import Path

import struct
import base64

try:
    from .definitions import APP_ROOT
except ImportError as e:
    from definitions import APP_ROOT


# http://coreygoldberg.blogspot.com/2013/01/python-verify-png-file-and-get-image.html
def get_image_info(data):
    if is_png(data):
        w, h = struct.unpack(b'>LL', data[16:24])
        width = int(w)
        height = int(h)
    else:
        raise Exception('not a png image')
    return width, height


def is_png(data):
    return data[:8] == b'\211PNG\r\n\032\n' and (data[12:16] == b'IHDR')


# https://blender.stackexchange.com/questions/240137/is-it-possible-to-create-image-data-from-a-base64-encoded-png
def image_from_data(name, data, height=1, width=1):
    # Create image, width and height are dummy values
    img = bpy.data.images.new(name, height, width)
    img.use_fake_user = True  # otherwise it won't save to the file

    # Set packed file data
    img.pack(data=data, data_len=len(data))
    # img.reload()

    # Switch to file source so it uses the packed file
    img.source = 'FILE'

    return img


# TODO: will be used for stud.io parts that have textures
# TexMap.base64_to_png(filename, img_data)
def base64_to_png_data(base64_str):
    if type(base64_str) is str:
        base64_str = bytes(base64_str.encode())
    return base64.decodebytes(base64_str)


def image_from_base64_str(filename, base64_str):
    img_data = base64_to_png_data(base64_str)
    return image_from_data(filename, img_data)


def named_png_from_base64_str(filename, base64_str):
    filename = f"{Path(filename).stem}.png"
    return image_from_base64_str(filename, base64_str)


# basename prevents writing to any place but APP_ROOT
def write_png_data(filename, data):
    filepath = os.path.join(APP_ROOT, f"{os.path.basename(filename)}.png")
    with open(filepath, 'wb') as file:
        file.write(data)
