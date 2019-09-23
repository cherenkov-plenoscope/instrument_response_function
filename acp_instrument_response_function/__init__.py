import numpy as np
import os
import json
from os import path as op
import shutil as sh
import tempfile
import corsika_wrapper as cw
import plenopy as pl
import subprocess


def __read_json(path):
    with open(path, 'rt') as fin:
        return json.loads(fin.read())


def __particle_str_to_corsika_id(particle_str):
    if particle_str == 'gamma':
        return 1
    elif particle_str == 'electron':
        return 3
    elif particle_str == 'proton':
        return 14
    raise ValueError(
        "The primary_particle '{:s}' is not supported".format(particle_str))


def __atmosphere_str_to_corsika_id(atmosphere_str):
    if atmosphere_str == "chile-paranal-eso":
        return 26
    elif atmosphere_str == 'canaries-lapalma-winter':
        return 8
    elif atmosphere_str == 'namibia-gamsberg':
        return 10
    raise ValueError(
        "The atmosphere_model '{:s}' is not supported".format(atmosphere_str))


def __read_plenoscope_geometry(scenery_path):
    children = __read_json(scenery_path)['children']
    for child in children:
        if child["type"] == "Frame" and child["name"] == "Portal":
            protal = child.copy()
    for child in protal['children']:
        if child["type"] == "LightFieldSensor":
            light_field_sensor = child.copy()
    return light_field_sensor


def __interpolate_with_power10(x, xp, fp):
    w = np.interp(
        x=np.log10(x),
        xp=np.log10(xp),
        fp=np.log10(fp))
    return 10**w


def __write_max_scatter_radius_vs_energy(
    energy_bin_edges,
    core_max_scatter_radius,
    path
):
    out = {
        "energy_bin_edges/GeV": energy_bin_edges.tolist(),
        "core_max_scatter_radius/m": core_max_scatter_radius.tolist(),}
    with open(path, "wt") as fout:
        fout.write(json.dumps(out, indent=4))


def __energy_bins_and_max_scatter_radius(
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
    max_scatter_radius_in_bin = __interpolate_with_power10(
        x=energy_bin_edges[1:],
        xp=energy,
        fp=max_scatter_radius)
    return max_scatter_radius_in_bin, energy_bin_edges


def __merlict_plenoscope_propagator(
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


def __make_jobs_with_balanced_runtime(
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


def __make_corsika_steering_card_str(run):
    c = ''
    c += 'RUNNR {:d}\n'.format(run["run_id"])
    c += 'EVTNR 1\n'
    c += 'NSHOW {:d}\n'.format(run["num_events"])
    c += 'PRMPAR {:d}\n'.format(run["particle_id"])
    c += 'ESLOPE {:3.3e}\n'.format(-1.)
    c += 'ERANGE {:3.3e} {:3.3e}\n'.format(
        run["energy_start"],
        run["energy_stop"])
    c += 'THETAP {:3.3e} {:3.3e}\n'.format(
        run["cone_zenith_deg"],
        run["cone_zenith_deg"])
    c += 'PHIP {:3.3e} {:3.3e}\n'.format(
        run["cone_azimuth_deg"], run["cone_azimuth_deg"])
    c += 'VIEWCONE .0 {:3.3e}\n'.format(run["cone_max_scatter_angle_deg"])
    c += 'SEED {:d} 0 0\n'.format(run["run_id"] + 0)
    c += 'SEED {:d} 0 0\n'.format(run["run_id"] + 1)
    c += 'SEED {:d} 0 0\n'.format(run["run_id"] + 2)
    c += 'SEED {:d} 0 0\n'.format(run["run_id"] + 3)
    c += 'OBSLEV {:3.3e}\n'.format(1e2*run["observation_level_altitude_asl"])
    c += 'FIXCHI .0\n'
    c += 'MAGNET {Bx:3.3e} {Bz:3.3e}\n'.format(
            Bx=run["earth_magnetic_field_x_muT"],
            Bz=run["earth_magnetic_field_z_muT"])
    c += 'ELMFLG T T\n'
    c += 'MAXPRT 1\n'
    c += 'PAROUT F F\n'
    c += 'TELESCOPE {x:3.3e} {y:3.3e} .0 {r:3.3e}\n'.format(
            x=1e2*run["instrument_x"],
            y=1e2*run["instrument_y"],
            r=1e2*run["instrument_radius"])
    c += 'ATMOSPHERE {:d} T\n'.format(run["atmosphere_id"])
    c += 'CWAVLG 250 700\n'
    c += 'CSCAT 1 {:3.3e} .0\n'.format(run["core_max_scatter_radius"])
    c += 'CERQEF F T F\n'
    c += 'CERSIZ 1.\n'
    c += 'CERFIL F\n'
    c += 'TSTART T\n'
    c += 'EXIT\n'
    return c


def __summarize_response(
    run_config,
    corsika_run_header,
    corsika_event_header,
    trigger_responses,
    detector_truth,
):
    evth = corsika_event_header
    runh = corsika_run_header

    num_obs_levels = evth[47-1]
    assert num_obs_levels == 1, ("There must be only 1 observation level.")

    num_reuses = evth[98-1]
    assert num_reuses == 1, ("Events must not be reused.")

    assert runh[249-1] == 0., (
        "Expected core-y-scatter = 0 for CORSIKA to throw core in a disc.")

    cone_max_scatter_angle = np.deg2rad(run_config["cone_max_scatter_angle_deg"])
    cone_azimuth = np.deg2rad(run_config["cone_azimuth_deg"])
    cone_zenith = np.deg2rad(run_config["cone_zenith_deg"])

    truth = {
        "run_id": int(runh[2-1]),
        "event_id": int(evth[2-1]),
        "true_particle_id": int(evth[3-1]),

        "true_particle_energy": float(evth[4-1]),

        "true_particle_momentum_x": float(evth[8-1]),
        "true_particle_momentum_y": float(evth[9-1]),
        "true_particle_momentum_z": float(evth[10-1]),

        "true_particle_azimuth": float(evth[11-1]),
        "true_particle_zenith": float(evth[12-1]),

        "true_particle_core_x": float(evth[ 99-1]*1e-2),
        "true_particle_core_y": float(evth[119-1]*1e-2),

        "true_particle_first_interaction_z": float(evth[7-1]*1e-2),

        "core_max_scatter_radius": float(runh[248-1]*1e-2),
        "cone_max_scatter_angle": float(cone_max_scatter_angle),

        "cone_azimuth": float(cone_azimuth),
        "cone_zenith": float(cone_zenith),

        "starting_grammage": float(evth[5-1]),
        "mag_north_vs_x": float(evth[93-1]),
        "obs_level_asl": float(evth[48-1]*1e-2),

        "true_pe_cherenkov": int(detector_truth.number_air_shower_pulses()),
    }

    truth["trigger_response"] = int(np.max(
        [layer['patch_threshold'] for layer in trigger_responses]))

    for o in range(len(trigger_responses)):
        truth["trigger_{:d}_object_distance".format(o)] = float(
            trigger_responses[o]['object_distance'])
        truth["trigger_{:d}_respnse".format(o)] = int(
            trigger_responses[o]['patch_threshold'])
    return truth


def __particle_id_run_id_event_id(event_summary):
    out = {}
    for k in ["true_particle_id", "run_id", "event_id"]:
        out[k] = event_summary[k]
    return out


def __evaluate_trigger_and_export_response(
    run_config,
    merlict_run_path,
    trigger_treshold=67,
    integration_time_in_slices=5,
    min_number_neighbors=3,
    object_distances=[10e3, 15e3, 20e3],
):
    run = pl.Run(merlict_run_path)
    trigger_preparation = pl.trigger.prepare_refocus_sum_trigger(
        light_field_geometry=run.light_field_geometry,
        object_distances=object_distances)

    thrown = []
    triggered = []

    for event in run:
        trigger_responses = pl.trigger.apply_refocus_sum_trigger(
            event=event,
            trigger_preparation=trigger_preparation,
            min_number_neighbors=min_number_neighbors,
            integration_time_in_slices=integration_time_in_slices)

        event_summary = __summarize_response(
            run_config=run_config,
            corsika_run_header=event.simulation_truth.event.corsika_run_header.raw,
            corsika_event_header=event.simulation_truth.event.corsika_event_header.raw,
            trigger_responses=trigger_responses,
            detector_truth=event.simulation_truth.detector)

        thrown.append(event_summary)

        if event_summary["trigger_response"] >= trigger_treshold:
            triggered.append(__particle_id_run_id_event_id(event_summary))
            event_filename = '{run_id:06d}{event_id:06d}'.format(
                run_id=event_summary["run_id"],
                event_id=event_summary["event_id"])
            event_path = op.join(
                run_config["past_trigger_dir"],
                event_filename)
            sh.copytree(event._path, event_path)
            pl.tools.acp_format.compress_event_in_place(event_path)

    with open(run_config['thrown_path'], 'wt') as fout:
        for event_summary in thrown:
            fout.write(json.dumps(event_summary)+"\n")

    with open(run_config['triggered_path'], 'wt') as fout:
        for event_id in triggered:
            fout.write(json.dumps(event_id)+"\n")



def __run_corsika_run(run):
    with tempfile.TemporaryDirectory(prefix='plenoscope_irf_') as tmp:
        corsika_card_path = op.join(tmp, 'corsika_card.txt')
        corsika_run_path = op.join(tmp, 'cherenkov_photons.evtio')
        merlict_run_path = op.join(tmp, 'plenoscope_response.acp')

        with open(corsika_card_path, "wt") as fout:
            card_str = __make_corsika_steering_card_str(run=run)
            fout.write(card_str)

        cor_rc = cw.corsika(
            steering_card=cw.read_steering_card(corsika_card_path),
            output_path=corsika_run_path,
            save_stdout=True)

        sh.copy(corsika_run_path+'.stdout', run['corsika_stdout_path'])
        sh.copy(corsika_run_path+'.stderr', run['corsika_stderr_path'])

        mct_rc = irfutils.__merlict_plenoscope_propagator(
            corsika_run_path=corsika_run_path,
            output_path=merlict_run_path,
            light_field_geometry_path=run['light_field_geometry_path'],
            merlict_plenoscope_propagator_path=\
                run['merlict_plenoscope_propagator_path'],
            merlict_plenoscope_propagator_config_path=\
                run['merlict_plenoscope_propagator_config_path'],
            random_seed=run['run_id'],
            photon_origins=True)

        sh.copy(merlict_run_path+'.stdout', run['merlict_stdout_path'])
        sh.copy(merlict_run_path+'.stderr', run['merlict_stderr_path'])

        __evaluate_trigger_and_export_response(
            run_config=run,
            merlict_run_path=merlict_run_path)


def run_job(job):
    for run in job["runs"]:
        __run_corsika_run(run=run)
    return 0


def make_output_directory_and_jobs(
    output_dir="__example_irf",
    num_energy_bins=31,
    num_events_in_energy_bin=50,
    max_num_events_in_run=10,
    particle_config_path=op.join(
        "resources",
        "acp",
        "71m",
        "gamma_calib.json"),
    location_config_path=op.join(
        "resources",
        "acp",
        "71m",
        "chile_paranal.json"),
    light_field_geometry_path=op.join(
        "run20190724_10",
        "light_field_calibration"),
    merlict_plenoscope_propagator_path=op.join(
        "build",
        "merlict",
        "merlict-plenoscope-propagation"),
    merlict_plenoscope_propagator_config_path=op.join(
        "resources",
        "acp",
        "merlict_propagation_config.json"),
    corsika_path=op.join(
        "build",
        "corsika",
        "corsika-75600",
        "run",
        "corsika75600Linux_QGSII_urqmd"),
    trigger_patch_threshold=67,
    trigger_integration_time_in_slices=5
):
    od = output_dir
    thrown_dir = op.join(od, '__thrown')
    triggered_dir = op.join(od, '__triggered')

    # Make directory tree
    #--------------------
    os.makedirs(od)
    os.makedirs(op.join(od, 'input'))
    os.makedirs(thrown_dir)
    os.makedirs(triggered_dir)
    os.makedirs(op.join(od, 'stdout'))
    os.makedirs(op.join(od, 'past_trigger'))

    # Copy input
    #-----------
    sh.copy(
        particle_config_path,
        op.join(od, 'input', 'particle_config.json'))
    sh.copy(
        location_config_path,
        op.join(od, 'input', 'location_config.json'))
    sh.copy(
        merlict_plenoscope_propagator_config_path,
        op.join(od, 'input', 'merlict_plenoscope_propagator_config.json'))
    merlict_plenoscope_propagator_config_path = op.join(
        od, 'input', 'merlict_plenoscope_propagator_config.json')
    sh.copytree(
        light_field_geometry_path,
        op.join(od, 'input', 'light_field_geometry'))
    light_field_geometry_path = op.join(od, 'input', 'light_field_geometry')

    # Read input
    #-----------
    particle_config = __read_json(
        op.join(od, 'input', 'particle_config.json'))
    location_config = __read_json(
        op.join(od, 'input', 'location_config.json'))
    plenoscope_geometry = __read_plenoscope_geometry(
        op.join(od, 'input', 'light_field_geometry',
            'input',
            'scenery',
            'scenery.json'))

    # Prepare simulation
    # ------------------
    (
        core_max_scatter_radius,
        energy_bin_edges
    ) = irfutils.__energy_bins_and_max_scatter_radius(
        energy=particle_config['energy'],
        max_scatter_radius=particle_config['max_scatter_radius'],
        num_energy_bins=num_energy_bins)

    irfutils.__write_max_scatter_radius_vs_energy(
        energy_bin_edges=energy_bin_edges,
        core_max_scatter_radius=core_max_scatter_radius,
        path=os.path.join(od, 'input', 'max_scatter_radius_vs_energy.csv'))

    # Make jobs
    #----------
    jobs = irfutils.__make_jobs_with_balanced_runtime(
        energy_bin_edges=energy_bin_edges,
        num_events_in_energy_bin=num_events_in_energy_bin,
        max_num_events_in_run=max_num_events_in_run,
        max_cumsum_energy_in_run_in_units_of_highest_event_energy=10)

    for j in range(len(jobs)):
        for r in range(len(jobs[j]["runs"])):
            # already set
            # -----------
            # run_id
            # energy_bin
            # num_events

            run = jobs[j]["runs"][r]
            run_id = run["run_id"]
            energy_bin = run["energy_bin"]
            run['observation_level_altitude_asl'] = location_config[
                'observation_level_altitude_asl']
            run['earth_magnetic_field_x_muT'] = location_config[
                'earth_magnetic_field_x_muT']
            run['earth_magnetic_field_z_muT'] = location_config[
                'earth_magnetic_field_z_muT']
            run['atmosphere_id'] = irfutils.__atmosphere_str_to_corsika_id(
                location_config["atmosphere"])
            run['energy_start'] = energy_bin_edges[energy_bin]
            run['energy_stop'] = energy_bin_edges[energy_bin + 1]
            run['particle_id'] = irfutils.__particle_str_to_corsika_id(
                particle_config['primary_particle'])
            run['cone_azimuth_deg'] = 0.
            run['cone_zenith_deg'] = 0.
            run['cone_max_scatter_angle_deg'] = particle_config[
                'max_scatter_angle_deg']
            run['instrument_x'] = 0.
            run['instrument_y'] = 0.
            run['instrument_radius'] = plenoscope_geometry[
                    'expected_imaging_system_aperture_radius']*1.1
            run['core_max_scatter_radius'] = \
                core_max_scatter_radius[energy_bin]
            run['light_field_geometry_path'] = light_field_geometry_path
            run['thrown_path'] = op.join(
                thrown_dir,
                '{:06d}.jsonl'.format(run_id))
            run['triggered_path'] = op.join(
                triggered_dir,
                '{:06d}.jsonl'.format(run_id))
            run['past_trigger_dir'] = op.join(
                od,
                'past_trigger')
            run['merlict_plenoscope_propagator_config_path'] = \
                merlict_plenoscope_propagator_config_path
            run['merlict_plenoscope_propagator_path'] = \
                merlict_plenoscope_propagator_path
            run['corsika_path'] = corsika_path
            run['merlict_stdout_path'] = op.join(
                od,
                'stdout',
                '{:06d}_merlict.stdout'.format(run_id))
            run['merlict_stderr_path'] = op.join(
                od,
                'stdout',
                '{:06d}_merlict.stderr'.format(run_id))
            run['corsika_stdout_path'] = op.join(
                od,
                'stdout',
                '{:06d}_corsika.stdout'.format(run_id))
            run['corsika_stderr_path'] = op.join(
                od,
                'stdout',
                '{:06d}_corsika.stderr'.format(run_id))
            run['trigger_patch_threshold'] = trigger_patch_threshold
            run['trigger_integration_time_in_slices'] = \
                trigger_integration_time_in_slices
            jobs[j]["runs"][r] = run
    return jobs
