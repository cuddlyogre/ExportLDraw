import csv
import io
import pprint
import re

pp = pprint.PrettyPrinter(indent=4, width=120)


def parse_line(line, min_params=0):
    line = re.sub(r'\s+', ' ', line.strip())

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
