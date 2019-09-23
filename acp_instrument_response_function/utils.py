import numpy as np
import json
from collections import OrderedDict
import os
import subprocess


def primary_particle_to_corsika(particle):
    if particle == 'gamma':
        return 1
    elif particle == 'electron':
        return 3
    elif particle == 'proton':
        return 14
    raise ValueError(
        "The primary_particle '{:s}' is not supported".format(particle))


def atmosphere_model_to_corsika(model):
    if model == "chile-paranal-eso":
        return 26
    elif model == 'canaries-lapalma-winter':
        return 8
    elif model == 'namibia-gamsberg':
        return 10
    raise ValueError(
        "The atmosphere_model '{:s}' is not supported".format(model))


def read_json(path):
    with open(path, 'rt') as fin:
        return json.loads(fin.read())


def interpolate_with_power10(x, xp, fp):
    w = np.interp(
        x=np.log10(x),
        xp=np.log10(xp),
        fp=np.log10(fp))
    return 10**w


def export_max_scatter_radius_vs_energy(
    energy_bin_edges,
    max_scatter_radius_in_energy_bin,
    directory
):
    np.savetxt(
        os.path.join(directory, 'max_scatter_radius_vs_energy.csv'),
        np.c_[energy_bin_edges[1:], max_scatter_radius_in_energy_bin],
        delimiter=', ',
        header='upper bin-edge energy/Gev, max_scatter_radius/m')


def read_acp_design_geometry(scenery_path):
    children = read_json(scenery_path)['children']
    for child in children:
        if child["type"] == "Frame" and child["name"] == "Portal":
            protal = child.copy()
    for child in protal['children']:
        if child["type"] == "LightFieldSensor":
            light_field_sensor = child.copy()
    return light_field_sensor


def energy_bins_and_max_scatter_radius(
    energy,
    max_scatter_radius,
    num_energy_bins,
):
    assert (energy == np.sort(energy)).all(), (
        "Expected the energies to be sorted")
    energy_bin_edges = np.logspace(
        np.log10(np.min(energy)),
        np.log10(np.max(energy)),
        num_energy_bins + 1)
    max_scatter_radius_in_bin = interpolate_with_power10(
        x=energy_bin_edges[1:],
        xp=energy,
        fp=max_scatter_radius)
    return max_scatter_radius_in_bin, energy_bin_edges


def merlict_plenoscope_propagator(
    corsika_run_path,
    output_path,
    light_field_geometry_path,
    merlict_plenoscope_propagator_path,
    merlict_plenoscope_propagator_config_path,
    random_seed,
    photon_origins=True
):
    """
    Calls the merlict Cherenkov-plenoscope propagation
    and saves the stdout and stderr
    """
    op = output_path
    with open(op+'.stdout', 'w') as out, open(op+'.stderr', 'w') as err:
        call = [
            merlict_plenoscope_propagator_path,
            '-l', light_field_geometry_path,
            '-c', merlict_plenoscope_propagator_config_path,
            '-i', corsika_run_path,
            '-o', output_path,
            '-r', '{:d}'.format(random_seed)]
        if photon_origins:
            call.append('--all_truth')
        mct_rc = subprocess.call(call, stdout=out, stderr=err)
    return mct_rc


def scatter_solid_angle(max_scatter_zenith_distance):
    cap_hight = (1.0 - np.cos(max_scatter_zenith_distance))
    return 2.0*np.pi*cap_hight


def make_jobs_with_balanced_runtime(
    energy_bin_edges=np.geomspace(0.25, 1000, 1001),
    num_events_in_energy_bin=512,
    max_num_events_in_run=128,
    max_cumsum_energy_in_run_in_units_of_highest_event_energy=10,
):
    """
    Make a list of jobs with similar work-load, based on the particle's energy.
    """
    num_energy_bins = energy_bin_edges.shape[0] - 1
    mean_energy_in_energy_bins = energy_bin_edges[1:]

    highest_event_enrgy = np.max(mean_energy_in_energy_bins)
    max_cumsum_energy_in_run = highest_event_enrgy*\
        max_cumsum_energy_in_run_in_units_of_highest_event_energy

    num_events_left_in_energy_bin = num_events_in_energy_bin*np.ones(
        num_energy_bins,
        dtype=np.int)

    runs = []
    run_id = 0
    for energy_bin in range(num_energy_bins):
        while num_events_left_in_energy_bin[energy_bin] > 0:
            run_id += 1
            num_events_in_run = int(
                max_cumsum_energy_in_run//
                mean_energy_in_energy_bins[energy_bin])

            if num_events_in_run > max_num_events_in_run:
                num_events_in_run = max_num_events_in_run
            run = {}
            run["run_id"] = run_id
            run["energy_bin"] = energy_bin
            run["mean_energy"] = mean_energy_in_energy_bins[energy_bin]
            run["num_events"] = num_events_in_run
            run["cumsum_energy"] = run["num_events"]*run["mean_energy"]
            num_events_left_in_energy_bin[energy_bin] -= num_events_in_run
            runs.append(run)
    jobs = []
    job_id = 0
    run_id = 0
    while run_id < len(runs):
        job_id += 1
        job = {}
        job["job_id"] = job_id
        job["cumsum_energy"] = 0
        job["runs"] = []
        while (
            run_id < len(runs) and
            job["cumsum_energy"] + runs[run_id]["cumsum_energy"] <=
                max_cumsum_energy_in_run
        ):
            job["runs"].append(runs[run_id])
            job["cumsum_energy"] += runs[run_id]["cumsum_energy"]
            run_id += 1
        jobs.append(job)
    return jobs
