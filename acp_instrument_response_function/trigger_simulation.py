import numpy as np
import os
from os.path import join
import shutil as sh
import tempfile
import corsika_wrapper as cw
import plenopy as pl
from . import utils as irfutils


def trigger_study(
    acp_response_path,
    output_path,
    past_trigger_path,
    run_number,
    patch_treshold=67,
    integration_time_in_slices=5
):
    run = pl.Run(acp_response_path)
    min_number_neighbors = 3

    trigger_preparation = pl.trigger.prepare_refocus_sum_trigger(
        run.light_field_geometry,
        object_distances=[10e3, 15e3, 20e3])

    event_infos = []
    for event in run:
        info = pl.trigger_study.export_trigger_information(event)
        info['num_air_shower_pulses'] = int(
            event.simulation_truth.detector.number_air_shower_pulses())
        info['refocus_sum_trigger'] = pl.trigger.apply_refocus_sum_trigger(
            event=event,
            trigger_preparation=trigger_preparation,
            min_number_neighbors=min_number_neighbors,
            integration_time_in_slices=integration_time_in_slices)
        event_infos.append(info)

        max_patch_threshold = np.max(
            [p['patch_threshold'] for p in info['refocus_sum_trigger']])

        if max_patch_threshold >= patch_treshold:
            event_filename = '{run:d}{event:06d}'.format(
                run=run_number,
                event=event.number)
            event_path = join(past_trigger_path, event_filename)
            sh.copytree(event._path, event_path)
            pl.tools.acp_format.compress_event_in_place(event_path)
            pl.trigger_study.write_dict_to_file(
                pl.trigger_study.un_numpyify(info['refocus_sum_trigger']),
                join(event_path, 'refocus_sum_trigger.json'))

    pl.trigger_study.write_dict_to_file(
        pl.trigger_study.un_numpyify(event_infos),
        output_path)

def __summarize_response(
    corsika_steering_card,
    corsika_run_header,
    corsika_event_header
):
    cosc = corsika_steering_card
    evth = corsika_event_header
    runh = corsika_run_header

    num_obs_levels = evth[47-1]
    assert num_obs_levels == 1 ("There must be only 1 observation level.")

    num_reuses = evth[98-1]
    assert num_reuses == 1 ("Events must not be reused.")

    assert runh[249-1] == 0. (
        "Expected core-y-scatter = 0 for CORSIKA to throw core in a disc.")

    max_scatter_angle = float(
        np.deg2rad(
            float(
                cosc['VIEWCONE'][0])))
    scatter_cone_azimuth = float(
        np.deg2rad(
            float(
                sc["PHIP"][0].split()[0])))
    scatter_cone_zenith = float(
        np.deg2rad(
            float(
                sc["THETAP"][0].split()[0])))

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

        "max_scatter_radius": float(runh[248-1]*1e-2),
        "max_scatter_angle": max_scatter_angle,

        "cone_azimuth": scatter_cone_azimuth,
        "cone_zenith": scatter_cone_zenith,

        "starting_grammage": float(evth[5-1]),
        "mag_north_vs_x": float(evth[93-1]),
        "obs_level_asl": float(evth[48-1]*1e-2),

        "true_pe_cherenkov": int(
            event.simulation_truth.detector.number_air_shower_pulses()),
    }

    truth["trigger_response"] = np.max(
        [layer['patch_threshold'] for layer in trigger_responses])

    for o in range(len(trigger_responses)):
        truth["trigger_{:d}_object_distance".format(o)] = float(
            trigger_responses[o]['object_distance'])
        truth["trigger_{:d}_respnse".format(o)] = float(
            trigger_responses[o]['patch_threshold'])

    return truth



def evaluate_trigger_and_export_response(
    job,
    acp_response_path,
    trigger_treshold=67,
    integration_time_in_slices=5,
    min_number_neighbors=3,
    object_distances=[10e3, 15e3, 20e3],
):
    run = pl.Run(acp_response_path)

    trigger_preparation = pl.trigger.prepare_refocus_sum_trigger(
        light_field_geometry=run.light_field_geometry,
        object_distances=object_distances)

    thrown = []
    for event in run:
        trigger_responses = pl.trigger.apply_refocus_sum_trigger(
            event=event,
            trigger_preparation=trigger_preparation,
            min_number_neighbors=min_number_neighbors,
            integration_time_in_slices=integration_time_in_slices)

        event_summary = __summarize_response(
            corsika_steering_card=job['corsika_steering_card'],
            corsika_run_header=event.simulation_truth.event.corsika_run_header.raw,
            corsika_event_header=event.simulation_truth.event.corsika_event_header.raw,
            trigger_responses=trigger_responses)

        if summary["trigger_response"] >= trigger_treshold:
            event_filename = '{run:d}{event:06d}'.format(
                run=summary["run"],
                event=summary["event"])
            event_path = join(job["past_trigger_path"], event_filename)
            sh.copytree(event._path, event_path)
            pl.tools.acp_format.compress_event_in_place(event_path)



def run_job(job):
    with tempfile.TemporaryDirectory(prefix='acp_trigger_') as tmp:
        corsika_run_path = join(tmp, 'airshower.evtio')
        acp_response_path = join(tmp, 'acp_response.acp')

        cor_rc = cw.corsika(
            steering_card=job['corsika_steering_card'],
            output_path=corsika_run_path,
            save_stdout=True)

        sh.copy(corsika_run_path+'.stdout', job['corsika_stdout_path'])
        sh.copy(corsika_run_path+'.stderr', job['corsika_stderr_path'])

        mct_rc = irfutils.merlict_plenoscope_propagator(
            corsika_run_path=corsika_run_path,
            output_path=acp_response_path,
            acp_detector_path=job['acp_detector_path'],
            mct_acp_propagator_path=job['mct_acp_propagator_path'],
            mct_acp_config_path=job['mct_acp_config_path'],
            random_seed=job['run_number'],
            photon_origins=True)

        sh.copy(acp_response_path+'.stdout', job['mct_stdout_path'])
        sh.copy(acp_response_path+'.stderr', job['mct_stderr_path'])

        evaluate_trigger_and_export_response(
            job=job,
            acp_response_path=acp_response_path)
    return {
        'corsika_return_code': cor_rc,
        'mctracer_return_code': mct_rc}


def make_output_directory_and_jobs(
    particle_steering_card_path,
    location_steering_card_path,
    output_path,
    acp_detector_path,
    mct_acp_config_path,
    mct_acp_propagator_path,
    trigger_patch_threshold=67,
    trigger_integration_time_in_slices=5
):
    op = output_path
    imr = 'intermediate_results_of_runs'

    # Copy input
    os.makedirs(op)
    os.makedirs(join(op, 'input'))
    os.makedirs(join(op, imr))
    os.makedirs(join(op, 'stdout'))
    os.makedirs(join(op, 'past_trigger'))
    sh.copy(
        particle_steering_card_path,
        join(op, 'input', 'particle_steering_card.json'))
    sh.copy(
        location_steering_card_path,
        join(op, 'input', 'location_steering_card.json'))
    sh.copy(
        mct_acp_config_path,
        join(op, 'input', 'mct_acp_config.json'))
    mct_acp_config_path = join(op, 'input', 'mct_acp_config.json')
    sh.copytree(
        acp_detector_path,
        join(op, 'input', 'acp_detector'))
    acp_detector_path = join(op, 'input', 'acp_detector')

    # Read input
    particle_steering_card = irfutils.read_json(
        join(op, 'input', 'particle_steering_card.json'))
    location_steering_card = irfutils.read_json(
        join(op, 'input', 'location_steering_card.json'))
    acp_geometry = irfutils.read_acp_design_geometry(
        join(
            op,
            'input',
            'acp_detector',
            'input',
            'scenery',
            'scenery.json'))

    # Prepare simulation
    max_scatter_radius_in_bin, energy_bin_edges = (
        irfutils.energy_bins_and_max_scatter_radius(
            energy=particle_steering_card['energy'],
            max_scatter_radius=particle_steering_card['max_scatter_radius'],
            number_runs=particle_steering_card['number_runs']))

    irfutils.export_max_scatter_radius_vs_energy(
        energy_bin_edges=energy_bin_edges,
        max_scatter_radius_in_bin=max_scatter_radius_in_bin,
        directory=join(op, 'input'))

    jobs = []
    for run in range(particle_steering_card['number_runs']):
        job = {}
        job['run_number'] = run+1
        job['corsika_steering_card'] = irfutils.make_corsika_steering_card(
            random_seed=particle_steering_card['random_seed'],
            run_number=job['run_number'],
            number_events_in_run=particle_steering_card['number_events_in_run'],
            primary_particle=irfutils.primary_particle_to_corsika(
                particle_steering_card['primary_particle']),
            E_start=energy_bin_edges[run],
            E_stop=energy_bin_edges[run + 1],
            max_zenith_scatter_angle_deg=irfutils.max_zenith_scatter_angle_deg(
                particle_steering_card['source_geometry'],
                acp_geometry['max_FoV_diameter_deg']),
            max_scatter_radius=max_scatter_radius_in_bin[run],
            observation_level_altitude_asl=location_steering_card[
                'observation_level_altitude_asl'],
            instrument_radius=acp_geometry[
                'expected_imaging_system_aperture_radius']*1.1,
            atmosphere_model=irfutils.atmosphere_model_to_corsika(
                location_steering_card['atmosphere_model']),
            earth_magnetic_field_x_muT=
                location_steering_card['earth_magnetic_field_x_muT'],
            earth_magnetic_field_z_muT=
                location_steering_card['earth_magnetic_field_z_muT'])
        job['acp_detector_path'] = acp_detector_path
        job['intermediate_path'] = join(
            op, imr, '{:d}.json.gz'.format(run+1))
        job['past_trigger_dir'] = join(op, 'past_trigger')
        job['mct_acp_config_path'] = mct_acp_config_path
        job['mct_acp_propagator_path'] = mct_acp_propagator_path
        job['mct_stdout_path'] = join(
            op, 'stdout',
            '{:d}_mctPlenoscopePropagation.stdout'.format(run+1))
        job['mct_stderr_path'] = join(
            op, 'stdout',
            '{:d}_mctPlenoscopePropagation.stderr'.format(run+1))
        job['corsika_stdout_path'] = join(
            op, 'stdout', '{:d}_corsika.stdout'.format(run+1))
        job['corsika_stderr_path'] = join(
            op, 'stdout', '{:d}_corsika.stderr'.format(run+1))
        job['trigger_patch_threshold'] = trigger_patch_threshold
        job['trigger_integration_time_in_slices'] = (
            trigger_integration_time_in_slices)
        jobs.append(job)
    return jobs
