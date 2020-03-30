import os
import urllib.request
import urllib.error
from pathlib import Path


def download_file(url, destination, headers=None):
    if headers is None:
        headers = {}

    try:
        request = urllib.request.Request(url, headers=headers)
        response = urllib.request.urlopen(request).read()

        new_dir = os.path.dirname(destination)
        Path(new_dir).mkdir(parents=True, exist_ok=True)

        with open(destination, 'wb') as file:
            file.write(response)
    except urllib.error.HTTPError as e:
        print(e.code)
        print(e.reason)
    except urllib.error.ContentTooShortError as e:
        print(str(e))
    except urllib.error.URLError as e:
        print(e.reason)


# url = "https://www.ldraw.org/library/official/p/stud3.dat"
# url = "https://www.ldraw.org/library/official/parts/s/78s01.dat"
# url = "https://www.ldraw.org/library/official/parts/4515p01.dat"
# url = "https://www.ldraw.org/library/unofficial/parts/685p04.dat"
# filename = os.path.basename(url)

def download_ldraw(path, filename):
    ldraw_org_url = "https://www.ldraw.org/library"
    texture_path = os.path.join(path, filename)
    texture_url = os.path.join(ldraw_org_url, texture_path)

    home = str(Path.home())
    ldraw_path = os.path.join(home, "ldraw")
    destination = os.path.join(ldraw_path, texture_path)

    headers = {'User-Agent': "Blender LDraw Importer"}
    download_file(texture_url, destination, headers)


def download_texture(filename):
    path = f"unofficial/parts/textures"
    download_ldraw(path, filename)


download_texture("685p04.png")
