import numpy as np
import os
import gzip, json
import glob
import tqdm


def make_list_of_all_json_files(path):
    """
    Returns a list of all '.json' or '.json.gz' files in path.
    """
    return glob.glob(os.path.join(path, '*.json*'))


def make_flat_run(path):
    """
    Reads in a json run dictionary and returns a 'flat' run dictionary.

    Example for flat and non flat
    -----------------------------
    non-flat:
        event 0: {energy: 1, color: 2, height: 4.5},
        event 1: {energy: 2, color: 8, height: 4.3},
        event 2: {energy: 5, color: 9, height: 4.1},

    flat: { event: [0,1,2],
            energy: [1,2,5],
            color: [2,8,9],
            height: [4.5, 4.3, 4.1],}
    """
    json_dict = json2dict(run_path)
    return flatten_run_dict(json_dict)   


def read_all_results(path):
    """
    Reads in and returns the condensed intermediate instrument responses.
    (single thread)
    """
    run_paths = make_list_of_all_json_files(path)
    runs = []
    for run_path in tqdm.tqdm(run_paths):
        json_dict = json2dict(run_path)
        flat_run = flatten_run_dict(json_dict)
        runs.append(flat_run)

    all_runs = concatenate_runs(runs)
    return all_runs


def save_result_to_json(result, path):
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
            json.dump(out, outfile)


def concatenate_runs(runs):
    keys = []
    assert len(runs) > 0
    for key in runs[0]:
        keys.append(key)

    concat_run = {}
    for key in keys:
        concat_run[key] = []

    for key in keys:
        for run in runs:
            concat_run[key].append(run[key])

    for key in keys:
        concat_run[key] = np.concatenate(concat_run[key])

    return concat_run


def json2dict(path):
    """
    Read in dictionaries from a json or gzipped json.gz file.
    """
    run = {}
    if os.path.splitext(path)[1] == '.gz':
        with gzip.open(path, "rb") as f:
            run = json.loads(f.read().decode("ascii"))
    else:
        with open(path, 'r') as infile:
            run = json.load(infile)
    return run


def flatten_run_dict(run_dict):
    """
    Returns a flat copy dictionary of the run dictionary

    Parameter
    ---------
    run_dict        The non-flat run dictionary as it is stored in the 
                    intermediate plenoscope responses (json files)

    Example for flat and non flat
    -----------------------------
    non-flat:
        event 0: {energy: 1, color: 2, height: 4.5},
        event 1: {energy: 2, color: 8, height: 4.3},
        event 2: {energy: 5, color: 9, height: 4.1},

    flat: { event: [0,1,2],
            energy: [1,2,5],
            color: [2,8,9],
            height: [4.5, 4.3, 4.1],}
    """
    run_number = []
    event_number = []

    lixel_sum = []
    raw_lixel_sum = []

    primary_particle_id = []
    primary_particle_energy = []
    core_x = []
    core_y = []
    zenith = []
    azimuth =[]
    scatter_radius = []

    for event in run_dict:
        run_number.append(event['id']['run'])
        event_number.append(event['id']['event'])

        lixel_sum.append(event['acp']['response']['lixel']['sum'])
        raw_lixel_sum.append(event['acp']['response']['raw_lixel']['sum'])

        primary_particle_id.append(event['simulation_truth']['primary_particle']['id'])
        primary_particle_energy.append(event['simulation_truth']['energy'])

        core_x.append(event['simulation_truth']['core_position']['x'])
        core_y.append(event['simulation_truth']['core_position']['y'])
        zenith.append(event['simulation_truth']['zenith'])
        azimuth.append(event['simulation_truth']['azimuth'])

        scatter_radius.append(event['simulation_truth']['scatter_radius'])

    return {
        'run_number': np.array(run_number, dtype=np.int32),
        'event_number': np.array(event_number, dtype=np.int32),

        'raw_lixel_sum': np.array(raw_lixel_sum, dtype=np.float32),
        'lixel_sum': np.array(lixel_sum, dtype=np.float32),

        'primary_particle_id': np.array(primary_particle_id, dtype=np.int32),
        'primary_particle_energy': np.array(primary_particle_energy, dtype=np.float32),
        'core_position_x': np.array(core_x, dtype=np.float32),
        'core_position_y': np.array(core_y, dtype=np.float32),
        'zenith': np.array(zenith, dtype=np.float32),
        'azimuth': np.array(azimuth, dtype=np.float32),
        'scatter_radius': np.array(scatter_radius, dtype=np.float32),
    }
