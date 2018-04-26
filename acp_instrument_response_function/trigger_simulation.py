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
    pathch_treshold=67,
):
    run = pl.Run(acp_response_path)
    integration_time_in_slices = 5
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

        if max_patch_threshold >= pathch_treshold:
            event_filename = '{run:d}{event:06d}'.format(
                run=run_number,
                event=event.number)
            event_path = join(past_trigger_path, event_filename)
            sh.copytree(event._path, event_path)
            pl.trigger_study.write_dict_to_file(
                pl.trigger_study.un_numpyify(info['refocus_sum_trigger']),
                join(event_path, 'refocus_sum_trigger.json'))

    pl.trigger_study.write_dict_to_file(
        pl.trigger_study.un_numpyify(event_infos),
        output_path)


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

        mct_rc = irfutils.run_acp(
            corsika_run_path=corsika_run_path,
            output_path=acp_response_path,
            acp_detector_path=job['acp_detector_path'],
            mct_acp_propagator_path=job['mct_acp_propagator_path'],
            mct_acp_config_path=job['mct_acp_config_path'],
            random_seed=job['run_number'],
            photon_origins=True)

        sh.copy(acp_response_path+'.stdout', job['mct_stdout_path'])
        sh.copy(acp_response_path+'.stderr', job['mct_stderr_path'])

        trigger_study(
            acp_response_path=acp_response_path,
            output_path=job['intermediate_path'],
            past_trigger_path=job['past_trigger_dir'],
            run_number=job['run_number'],
            pathch_treshold=job['trigger_threshold'])
    return {
        'corsika_return_code': cor_rc,
        'mctracer_return_code': mct_rc}


def make_output_directory_and_jobs(
    steering_card_path,
    output_path,
    acp_detector_path,
    mct_acp_config_path,
    mct_acp_propagator_path
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
        steering_card_path,
        join(op, 'input', 'steering.json'))
    steering_card_path = join(op, 'input', 'steering.json')
    sh.copy(
        mct_acp_config_path,
        join(op, 'input', 'mct_acp_config.xml'))
    mct_acp_config_path = join(op, 'input', 'mct_acp_config.xml')
    sh.copytree(
        acp_detector_path,
        join(op, 'input', 'acp_detector'))
    acp_detector_path = join(op, 'input', 'acp_detector')

    # Read input
    steering_card = irfutils.read_json(
        join(
            op,
            'input',
            'steering.json'))
    acp_geometry = irfutils.read_acp_design_geometry(
        join(
            op,
            'input',
            'acp_detector',
            'input',
            'scenery',
            'scenery.xml'))

    # Prepare simulation
    max_scatter_radius_in_bin, energy_bin_edges = (
        irfutils.energy_bins_and_max_scatter_radius(
            energy=steering_card['energy'],
            max_scatter_radius=steering_card['max_scatter_radius'],
            number_runs=steering_card['number_runs']))

    irfutils.export_max_scatter_radius_vs_energy(
        energy_bin_edges=energy_bin_edges,
        max_scatter_radius_in_bin=max_scatter_radius_in_bin,
        directory=join(op, 'input'))

    jobs = []
    for run in range(steering_card['number_runs']):
        job = {}
        job['run_number'] = run+1
        job['corsika_steering_card'] = irfutils.make_corsika_steering_card(
            random_seed=steering_card['random_seed'],
            run_number=job['run_number'],
            number_events_in_run=steering_card['number_events_in_run'],
            primary_particle=irfutils.primary_particle_to_corsika(
                steering_card['primary_particle']),
            E_start=energy_bin_edges[run],
            E_stop=energy_bin_edges[run + 1],
            max_zenith_scatter_angle_deg=irfutils.max_zenith_scatter_angle_deg(
                steering_card['source_geometry'],
                acp_geometry['max_FoV_diameter_deg']),
            max_scatter_radius=max_scatter_radius_in_bin[run],
            observation_level_altitude_asl=steering_card[
                'observation_level_altitude_asl'],
            instrument_radius=acp_geometry[
                'expected_imaging_system_aperture_radius']*1.1,
            atmosphere_model=irfutils.atmosphere_model_to_corsika(
                steering_card['atmosphere_model']))
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
        job['trigger_threshold'] = steering_card['trigger_threshold']
        jobs.append(job)
    return jobs
