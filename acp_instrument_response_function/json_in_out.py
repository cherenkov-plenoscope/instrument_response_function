import os
import gzip
import json


def write_json_dictionary(result, path, indent=None):
    """
    Saves a python dictionary into a json file.
    """
    out = {}
    # un numpyify the arrays to lists
    for key in result:
        out[key] = result[key].tolist()

    if os.path.splitext(path)[1] == '.gz':
        with gzip.open(path, mode="wt") as outfile:
            json.dump(out, outfile)
    else:
        with open(path, 'w') as outfile:
            json.dump(out, outfile, indent=indent)


def read_json_dictionary(path):
    """
    Reads in a dictionay from a json or gzipped json.gz file.
    """
    run = {}
    if os.path.splitext(path)[1] == '.gz':
        with gzip.open(path, "rb") as f:
            run = json.loads(f.read().decode("ascii"))
    else:
        with open(path, 'r') as infile:
            run = json.load(infile)
    return run
