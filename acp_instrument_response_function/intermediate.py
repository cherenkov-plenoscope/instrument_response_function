import numpy as np
import os
import glob
from .json_in_out import write_json_dictionary
from .json_in_out import read_json_dictionary
import json


def list_run_paths_in(path):
    """
    Returns a list of all '.json' or '.json.gz' files in path.
    """
    return glob.glob(os.path.join(path, '*.json*'))


def make_flat_run(run_path):
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
    json_dict = read_json_dictionary(run_path)
    return flatten_run_dict(json_dict)


def condese_intermediate_runs(intermediate_runs_dir, output_path):
    """
    Reads in the intermediate run results and condeses the ACP event responses
    in these run_XXX.josn.gz files into one singel dictionary which is stored
    into a JSON file.
    (single thread)

    Parameter
    ---------
    intermediate_runs_dir       Path to the intermediate run results directory.
    output_path                 Path to the output JSON of the ACP event
                                responses.

    """
    run_paths = list_run_paths_in(intermediate_runs_dir)
    runs = []
    for i, run_path in enumerate(run_paths):
        json_dict = read_json_dictionary(run_path)
        flat_run = flatten_run_dict(json_dict)
        runs.append(flat_run)
        print(str(i)+' of '+str(len(run_paths)))

    all_runs = concatenate_runs(runs)
    write_json_dictionary(all_runs, output_path)


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

    raw_lixel_sum = []

    primary_particle_id = []
    primary_particle_energy = []
    core_x = []
    core_y = []
    zenith = []
    azimuth = []
    scatter_radius = []

    for event in run_dict:
        run_number.append(event['id']['run'])
        event_number.append(event['id']['event'])

        raw_lixel_sum.append(event['acp']['response']['raw_lixel']['sum'])

        primary_particle_id.append(
            event['simulation_truth']['primary_particle']['id'])
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

        'primary_particle_id': np.array(primary_particle_id, dtype=np.int32),
        'primary_particle_energy': np.array(
            primary_particle_energy, dtype=np.float32),
        'core_position_x': np.array(core_x, dtype=np.float32),
        'core_position_y': np.array(core_y, dtype=np.float32),
        'zenith': np.array(zenith, dtype=np.float32),
        'azimuth': np.array(azimuth, dtype=np.float32),
        'scatter_radius': np.array(scatter_radius, dtype=np.float32),
    }

def reduce(intermediate_runs_dir, out_path):
    intermediate_run_paths = list_run_paths_in(intermediate_runs_dir)
    with open(out_path, "wt") as fout:
        for run_path in intermediate_run_paths:
            intermediate_run = read_json_dictionary(run_path)
            out = {}
            for evt in intermediate_run:
                # id
                out["run"] = evt["id"]["run"]
                out["event"] = evt["id"]["event"]
                out["true_particle_id"] = int(
                    evt["simulation_truth"]["primary_particle"]["id"])
                # trigger
                out["trigger_patch_threshold_0"] = \
                    evt["refocus_sum_trigger"][0]["patch_threshold"]
                out["trigger_patch_threshold_1"] = \
                    evt["refocus_sum_trigger"][1]["patch_threshold"]
                out["trigger_patch_threshold_2"] = \
                    evt["refocus_sum_trigger"][2]["patch_threshold"]
                # particle truth
                # out["true_particle_id"]
                st = evt["simulation_truth"]
                out["true_particle_energy"] = st["energy"]
                out["true_particle_zenith"] = st["zenith"]
                out["true_particle_azimuth"] = st["azimuth"]
                out["true_particle_core_x"] = st["core_position"]["x"]
                out["true_particle_core_y"] = st["core_position"]["y"]
                out["true_particle_max_core_scatter_radius"] = \
                    st["scatter_radius"]
                out["true_particle_first_interaction_height"] = \
                    st["first_interaction_height"]
                fout.write(json.dumps(out))
                fout.write("\n")
