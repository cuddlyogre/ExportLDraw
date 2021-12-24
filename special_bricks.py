from . import helpers

part_slopes = {}


# bulbs
# 11013.dat
# 11177.dat
# 11178.dat
# 55972.dat
# 62503.dat
# 64897.dat
# '62930.dat' 47 -> 18 62503.dat
# '54869.dat' 47 -> 36 62503.dat

# lights
# '62930.dat': (1.0, 0.373, 0.059, 1.0),
# '54869.dat': (1.0, 0.052, 0.017, 1.0),


def get_part_slopes(filename):
    if filename in part_slopes:
        return part_slopes[filename]
    else:
        return None


def reset():
    read_part_slopes()


def read_part_slopes():
    global part_slopes
    part_slopes = helpers.read_json('content', 'part_slopes.json', {})


# after writing, it will be one giant line
# paste unformatted in something like vs2019 to format it in a nice way
def write_part_slopes():
    helpers.write_json('content', 'part_slopes.json', part_slopes)
