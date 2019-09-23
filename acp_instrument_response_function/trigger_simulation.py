import numpy as np
import os
import json
from os import path as op
import shutil as sh
import tempfile
import corsika_wrapper as cw
import plenopy as pl
from . import utils as irfutils


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



def run_corsika_run(run):
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

        mct_rc = irfutils.merlict_plenoscope_propagator(
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
        run_corsika_run(run=run)
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
    particle_config = irfutils.read_json(
        op.join(od, 'input', 'particle_config.json'))
    location_config = irfutils.read_json(
        op.join(od, 'input', 'location_config.json'))
    plenoscope_geometry = irfutils.read_acp_design_geometry(
        op.join(od, 'input', 'light_field_geometry',
            'input',
            'scenery',
            'scenery.json'))

    # Prepare simulation
    # ------------------
    (
        max_scatter_radius_in_energy_bin,
        energy_bin_edges
    ) = irfutils.energy_bins_and_max_scatter_radius(
        energy=particle_config['energy'],
        max_scatter_radius=particle_config['max_scatter_radius'],
        num_energy_bins=num_energy_bins)

    irfutils.export_max_scatter_radius_vs_energy(
        energy_bin_edges=energy_bin_edges,
        max_scatter_radius_in_energy_bin=max_scatter_radius_in_energy_bin,
        directory=op.join(od, 'input'))

    # Make jobs
    #----------
    jobs = irfutils.make_jobs_with_balanced_runtime(
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
            run['atmosphere_id'] = irfutils.atmosphere_model_to_corsika(
                location_config["atmosphere"])
            run['energy_start'] = energy_bin_edges[energy_bin]
            run['energy_stop'] = energy_bin_edges[energy_bin + 1]
            run['particle_id'] = irfutils.primary_particle_to_corsika(
                particle_config['primary_particle'])
            run['cone_azimuth_deg'] = 0.
            run['cone_zenith_deg'] = 0.
            run['cone_max_scatter_angle_deg'] = particle_config[
                'max_scatter_angle_deg']
            run['instrument_x'] = 0.
            run['instrument_y'] = 0.
            run['instrument_radius'] = plenoscope_geometry[
                    'expected_imaging_system_aperture_radius']*1.1
            run['core_max_scatter_radius'] = max_scatter_radius_in_energy_bin[
                energy_bin]
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
