import csv
import io


def parse_line(line, padding=0):
    line = line.replace("\t", " ")
    rows = list(csv.reader(io.StringIO(line), delimiter=' ', quotechar='"', skipinitialspace=True))

    if len(rows) == 0:
        return None

    params = rows[0]

    if len(params) == 0:
        return None

    while len(params) < padding:
        params.append("")

    return params
