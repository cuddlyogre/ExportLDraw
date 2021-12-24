import csv
import io
import re
import codecs
import json
from pathlib import Path
import os


# remove multiple spaces
def clean_line(line):
    return " ".join(line.strip().split())


# assumes cleaned line being passed
def get_params(clean_line, command, lowercase=True):
    no_command = clean_line[len(command):]
    no_command_parts = no_command.split()
    if lowercase:
        return [x.lower() for x in no_command_parts]
    return no_command_parts


def parse_csv_line(line, min_params=0):
    try:
        parts = list(csv.reader(io.StringIO(line), delimiter=' ', quotechar='"', skipinitialspace=True))
    except csv.Error as e:
        parts = [re.split(r"\s+", line)]

    if len(parts) == 0:
        return None

    _params = parts[0]

    if len(_params) == 0:
        return None

    while len(_params) < min_params:
        _params.append("")
    return _params


def fix_string_encoding(string):
    new_string = string
    if type(string) is str:
        new_string = bytes(string.encode())
    for codec in [codecs.BOM_UTF8, codecs.BOM_UTF16, codecs.BOM_UTF32]:
        new_string = new_string.replace(codec, b'')
    new_string = new_string.decode()
    return new_string


def write_json(folder, filename, dictionary):
    try:
        this_script_dir = os.path.dirname(os.path.realpath(__file__))
        folder = os.path.join(this_script_dir, folder)
        Path(folder).mkdir(parents=True, exist_ok=True)
        file_path = os.path.join(folder, filename)

        with open(file_path, 'w', encoding='utf-8', newline="\n") as file:
            file.write(json.dumps(dictionary))
    except Exception as e:
        print(e)


def read_json(folder, filename, default=None):
    try:
        this_script_dir = os.path.dirname(os.path.realpath(__file__))
        folder = os.path.join(this_script_dir, folder)
        file_path = os.path.join(folder, filename)

        with open(file_path, 'r', encoding='utf-8') as file:
            return json.load(file)
    except Exception as e:
        print(e)
        return default
