import csv
import io
import pprint
import re
import codecs

pp = pprint.PrettyPrinter(indent=4, width=120)


def get_params(line, command):
    l = " ".join(line.split())[len(command):].split()
    return [x.lower() for x in l]


def split_line(line):
    return line.strip().split()


def clean_line(line):
    line = " ".join(split_line(line))
    # line = re.sub(r'\s+', ' ', str(line)).strip()
    # line = fix_string_encoding(line)
    return line


def parse_csv_line(line, min_params=0):
    try:
        parts = list(csv.reader(io.StringIO(line), delimiter=' ', quotechar='"', skipinitialspace=True))
    except csv.Error as e:
        parts = [re.split(r"\s+", line)]

    if len(parts) == 0:
        return None

    params = parts[0]

    if len(params) == 0:
        return None

    while len(params) < min_params:
        params.append("")
    return params


def parse_line(line, min_params=0):
    params = split_line(line)
    while len(params) < min_params:
        params.append("")
    return params


def fix_string_encoding(string):
    new_string = string
    if type(string) is str:
        new_string = bytes(string.encode())
    for codec in [codecs.BOM_UTF8, codecs.BOM_UTF16, codecs.BOM_UTF32]:
        new_string = new_string.replace(codec, b'')
    new_string = new_string.decode()
    return new_string
