import csv
import io
import pprint

pp = pprint.PrettyPrinter(indent=4, width=120)


def parse_line(line, min_params=0):
    line = line.strip().replace("\t", " ")
    rows = list(csv.reader(io.StringIO(line), delimiter=' ', quotechar='"', skipinitialspace=True))

    if len(rows) == 0:
        return None

    params = rows[0]

    if len(params) == 0:
        return None

    while len(params) < min_params:
        params.append("")

    return params
