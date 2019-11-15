import numpy as np
import os
import json
from os import path as op
import shutil as sh
import tempfile
import corsika_wrapper as cw
import plenopy as pl
import subprocess
import glob


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


def _write_energy_dependencies(energy_dependencies, path):
    edp = energy_dependencies
    out = {
        "energy_bin_edges": edp["energy_bin_edges"].tolist(),
        "max_scatter_radius_in_bin": edp["max_scatter_radius_in_bin"].tolist(),
        "magnetic_deflection_correction": edp[
            "magnetic_deflection_correction"].tolist(),
        "instrument_x": edp["instrument_x"].tolist(),
        "instrument_y": edp["instrument_y"].tolist(),
        "azimuth_phi_deg": edp["azimuth_phi_deg"].tolist(),
        "zenith_theta_deg": edp["zenith_theta_deg"].tolist(),
    }
    with open(path, "wt") as fout:
        fout.write(json.dumps(out, indent=4))


def _estimate_energy_dependencies(
    particle_config,
    magnetic_deflection_config,
    num_energy_bins
):
    par = particle_config
    _par_sort = np.argsort(par['energy'])
    par_energy = np.array(par['energy'])[_par_sort]
    par_max_scatter_radius = np.array(par['max_scatter_radius'])[_par_sort]

    mdf = magnetic_deflection_config
    _mdf_sort = np.argsort(mdf['energy'])
    mdf_energy = np.array(mdf['energy'])[_mdf_sort]
    mdf_instrument_x = np.array(mdf['instrument_x'])[_mdf_sort]
    mdf_instrument_y = np.array(mdf['instrument_y'])[_mdf_sort]
    mdf_azimuth_phi_deg = np.array(mdf['azimuth_phi_deg'])[_mdf_sort]
    mdf_zenith_theta_deg = np.array(mdf['zenith_theta_deg'])[_mdf_sort]

    _min_energy = np.max([np.min(par_energy), np.min(mdf_energy)])

    energy_bin_edges = np.logspace(
        np.log10(_min_energy),
        np.log10(np.max(par_energy)),
        num_energy_bins + 1)
    _energy_bin_upper_energy = energy_bin_edges[1:]
    _energy_bin_lower_energy = energy_bin_edges[0:-1]

    max_scatter_radius_in_bin = __interpolate_with_power10(
        x=_energy_bin_upper_energy,
        xp=par_energy,
        fp=par_max_scatter_radius)

    cor = np.zeros(num_energy_bins, dtype=np.bool)
    instrument_x = np.zeros(num_energy_bins, dtype=np.float)
    instrument_y = np.zeros(num_energy_bins, dtype=np.float)
    azimuth_phi_deg = np.zeros(num_energy_bins, dtype=np.float)
    zenith_theta_deg = np.zeros(num_energy_bins, dtype=np.float)

    cor[
        _energy_bin_lower_energy < np.max(mdf_energy)] = True

    instrument_x[cor] = np.interp(
        x=_energy_bin_lower_energy,
        xp=mdf_energy,
        fp=mdf_instrument_x)[cor]

    instrument_y[cor] = np.interp(
        x=_energy_bin_lower_energy,
        xp=mdf_energy,
        fp=mdf_instrument_y)[cor]

    azimuth_phi_deg[cor] = np.interp(
        x=_energy_bin_lower_energy,
        xp=mdf_energy,
        fp=mdf_azimuth_phi_deg)[cor]

    zenith_theta_deg[cor] = np.interp(
        x=_energy_bin_lower_energy,
        xp=mdf_energy,
        fp=mdf_zenith_theta_deg)[cor]

    return {
        "energy_bin_edges": energy_bin_edges,
        "max_scatter_radius_in_bin": max_scatter_radius_in_bin,
        "magnetic_deflection_correction": cor,
        "instrument_x": instrument_x,
        "instrument_y": instrument_y,
        "azimuth_phi_deg": azimuth_phi_deg,
        "zenith_theta_deg": zenith_theta_deg}


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
    c += 'CSCAT 1 {:3.3e} .0\n'.format(1e2*run["core_max_scatter_radius"])
    c += 'CERQEF F T F\n'
    c += 'CERSIZ 1.\n'
    c += 'CERFIL F\n'
    c += 'TSTART T\n'
    c += 'EXIT\n'
    return c


def __particle_id_run_id_event_id(event_summary):
    out = {}
    for k in ["true_particle_id", "run_id", "event_id"]:
        out[k] = event_summary[k]
    return out


def __summarize_particle_truth(
    corsika_run_header,
    corsika_event_header,
    run_config,
):
    evth = corsika_event_header
    runh = corsika_run_header

    num_obs_levels = evth[47-1]
    assert num_obs_levels == 1, ("There must be only 1 observation level.")

    num_reuses = evth[98-1]
    assert num_reuses == 1, ("Events must not be reused.")

    assert runh[249-1] == 0., (
        "Expected core-y-scatter = 0 for CORSIKA to throw core in a disc.")

    cone_max_scatter_angle = np.deg2rad(
        run_config["cone_max_scatter_angle_deg"])
    cone_azimuth = np.deg2rad(run_config["cone_azimuth_deg"])
    cone_zenith = np.deg2rad(run_config["cone_zenith_deg"])

    truth = {
        "true_particle_id": int(evth[3-1]),
        "run_id": int(runh[2-1]),
        "event_id": int(evth[2-1]),

        "true_particle_energy": float(evth[4-1]),

        "true_particle_momentum_x": float(evth[8-1]),
        "true_particle_momentum_y": float(evth[9-1]),
        "true_particle_momentum_z": float(evth[10-1]),

        "true_particle_azimuth": float(evth[11-1]),
        "true_particle_zenith": float(evth[12-1]),

        "true_particle_core_x": float(evth[99-1]*1e-2),
        "true_particle_core_y": float(evth[119-1]*1e-2),

        "true_particle_first_interaction_z": float(evth[7-1]*1e-2),

        "core_max_scatter_radius": float(runh[248-1]*1e-2),
        "cone_max_scatter_angle": float(cone_max_scatter_angle),

        "cone_azimuth": float(cone_azimuth),
        "cone_zenith": float(cone_zenith),

        "starting_grammage": float(evth[5-1]),
        "mag_north_vs_x": float(evth[93-1]),
        "obs_level_asl": float(evth[48-1]*1e-2),
    }
    return truth


def __summarize_trigger_response(
    unique_id,
    trigger_responses,
    detector_truth,
):
    tr = unique_id.copy()
    tr["true_pe_cherenkov"] = int(detector_truth.number_air_shower_pulses())
    tr["trigger_response"] = int(np.max(
        [layer['patch_threshold'] for layer in trigger_responses]))
    for o in range(len(trigger_responses)):
        tr["trigger_{:d}_object_distance".format(o)] = float(
            trigger_responses[o]['object_distance'])
        tr["trigger_{:d}_respnse".format(o)] = int(
            trigger_responses[o]['patch_threshold'])
    return tr


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

    particle_truth_table = []
    trigger_truth_table = []
    past_trigger_table = []

    for event in run:
        trigger_responses = pl.trigger.apply_refocus_sum_trigger(
            event=event,
            trigger_preparation=trigger_preparation,
            min_number_neighbors=min_number_neighbors,
            integration_time_in_slices=integration_time_in_slices)
        with open(op.join(event._path, "refocus_sum_trigger.json"), "wt") as f:
            f.write(json.dumps(trigger_responses, indent=4))

        crunh = event.simulation_truth.event.corsika_run_header.raw
        cevth = event.simulation_truth.event.corsika_event_header.raw

        particle_truth = __summarize_particle_truth(
            corsika_run_header=crunh,
            corsika_event_header=cevth,
            run_config=run_config)
        particle_truth_table.append(particle_truth)

        trigger_truth = __summarize_trigger_response(
            unique_id=__particle_id_run_id_event_id(particle_truth),
            trigger_responses=trigger_responses,
            detector_truth=event.simulation_truth.detector)
        trigger_truth_table.append(trigger_truth)

        if trigger_truth["trigger_response"] >= trigger_treshold:
            past_trigger_table.append(
                __particle_id_run_id_event_id(particle_truth))
            event_filename = '{run_id:06d}{event_id:06d}'.format(
                run_id=particle_truth["run_id"],
                event_id=particle_truth["event_id"])
            event_path = op.join(
                run_config["past_trigger_dir"],
                event_filename)
            sh.copytree(event._path, event_path)
            pl.tools.acp_format.compress_event_in_place(event_path)

    with open(run_config['particle_truth_table_path'], 'wt') as f:
        for e in particle_truth_table:
            f.write(json.dumps(e)+"\n")

    with open(run_config['trigger_truth_table_path'], 'wt') as f:
        for e in trigger_truth_table:
            f.write(json.dumps(e)+"\n")

    with open(run_config['past_trigger_table_path'], 'wt') as f:
        for e in past_trigger_table:
            f.write(json.dumps(e)+"\n")


def assert_particle_location_and_deflection_do_match(
    particle_config,
    location_config,
    magnetic_deflection_config
):
    pc = particle_config
    loc = location_config
    mdc = magnetic_deflection_config

    assert (
        mdc['input']['corsika_particle_id'] ==
        __particle_str_to_corsika_id(pc['primary_particle']))

    mdc_loc = mdc['input']['site']

    assert (mdc_loc['corsika_atmosphere_model'] ==
        __atmosphere_str_to_corsika_id(loc['atmosphere']))

    tol = 0.05
    obs_l = 'observation_level_altitude_asl'
    assert np.abs(mdc_loc[obs_l] - loc[obs_l]) <= np.abs(tol*loc[obs_l])

    mag_x = 'earth_magnetic_field_x_muT'
    assert np.abs(mdc_loc[mag_x] - loc[mag_x]) <= np.abs(tol*loc[mag_x])

    mag_z = 'earth_magnetic_field_z_muT'
    assert np.abs(mdc_loc[mag_z] - loc[mag_z]) <= np.abs(tol*loc[mag_z])


def run_job(job):
    run = job
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
            save_stdout=True,
            corsika_path=run['corsika_path'])

        sh.copy(corsika_run_path+'.stdout', run['corsika_stdout_path'])
        sh.copy(corsika_run_path+'.stderr', run['corsika_stderr_path'])

        mct_rc = __merlict_plenoscope_propagator(
            corsika_run_path=corsika_run_path,
            output_path=merlict_run_path,
            light_field_geometry_path=run['light_field_geometry_path'],
            merlict_plenoscope_propagator_path=run[
                'merlict_plenoscope_propagator_path'],
            merlict_plenoscope_propagator_config_path=run[
                'merlict_plenoscope_propagator_config_path'],
            random_seed=run['run_id'],
            photon_origins=True)

        sh.copy(merlict_run_path+'.stdout', run['merlict_stdout_path'])
        sh.copy(merlict_run_path+'.stderr', run['merlict_stderr_path'])

        __evaluate_trigger_and_export_response(
            run_config=run,
            merlict_run_path=merlict_run_path)
    return 0


def make_output_directory_and_jobs(
    output_dir="__example_irf",
    num_energy_bins=3,
    num_events_in_energy_bin=10,
    particle_config_path=op.join(
        "resources",
        "acp",
        "71m",
        "electron_calibration.json"),
    magnetic_deflection_config_path=op.join(
        "resources",
        "acp",
        "71m",
        "magnetic_deflection_electron_chile_paranal.json"),
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
    trigger_integration_time_in_slices=5,
    particle_truth_table_dirname='__particle_truth_table',
    trigger_truth_table_dirname='__trigger_truth_table',
    past_trigger_table_dirname='__past_trigger_table'
):
    od = output_dir
    particle_truth_table_dir = op.join(od, particle_truth_table_dirname)
    trigger_truth_table_dir = op.join(od, trigger_truth_table_dirname)
    past_trigger_table_dir = op.join(od, past_trigger_table_dirname)

    # Make directory tree
    # -------------------
    os.makedirs(od)
    os.makedirs(op.join(od, 'input'))
    os.makedirs(particle_truth_table_dir)
    os.makedirs(trigger_truth_table_dir)
    os.makedirs(past_trigger_table_dir)
    os.makedirs(op.join(od, 'stdout'))
    os.makedirs(op.join(od, 'past_trigger'))

    # Copy input
    # ----------
    sh.copy(
        particle_config_path,
        op.join(od, 'input', 'particle_config.json'))
    sh.copy(
        location_config_path,
        op.join(od, 'input', 'location_config.json'))
    sh.copy(
        magnetic_deflection_config_path,
        op.join(od, 'input', 'magnetic_deflection_config.json'))
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
    # ----------
    particle_config = __read_json(
        op.join(od, 'input', 'particle_config.json'))
    location_config = __read_json(
        op.join(od, 'input', 'location_config.json'))
    magnetic_deflection_config = __read_json(
        op.join(od, 'input', 'magnetic_deflection_config.json'))
    plenoscope_geometry = __read_plenoscope_geometry(
        op.join(
            od,
            'input',
            'light_field_geometry',
            'input',
            'scenery',
            'scenery.json'))

    assert_particle_location_and_deflection_do_match(
        particle_config=particle_config,
        location_config=location_config,
        magnetic_deflection_config=magnetic_deflection_config)

    # Prepare simulation
    # ------------------
    energy_dependencies = _estimate_energy_dependencies(
        particle_config=particle_config,
        magnetic_deflection_config=magnetic_deflection_config,
        num_energy_bins=num_energy_bins)
    edp = energy_dependencies

    _write_energy_dependencies(
        energy_dependencies=edp,
        path=os.path.join(od, 'input', 'energy_dependencies.json'))

    # Make jobs
    # ---------
    jobs = []
    for energy_bin in range(num_energy_bins):

        run = {}
        run_id = energy_bin + 1
        run_id_str = '{:06d}'.format(run_id)
        run["run_id"] = run_id
        run["energy_bin"] = energy_bin
        run["num_events"] = num_events_in_energy_bin
        run['energy_start'] = edp["energy_bin_edges"][energy_bin]
        run['energy_stop'] = edp["energy_bin_edges"][energy_bin + 1]

        run['magnetic_deflection_correction'] = edp[
            "magnetic_deflection_correction"][energy_bin]
        run['cone_azimuth_deg'] = edp["azimuth_phi_deg"][energy_bin]
        run['cone_zenith_deg'] = edp["zenith_theta_deg"][energy_bin]
        run['instrument_x'] = edp["instrument_x"][energy_bin]
        run['instrument_y'] = edp["instrument_y"][energy_bin]
        run['core_max_scatter_radius'] = edp[
            "max_scatter_radius_in_bin"][energy_bin]

        run['observation_level_altitude_asl'] = location_config[
            'observation_level_altitude_asl']
        run['earth_magnetic_field_x_muT'] = location_config[
            'earth_magnetic_field_x_muT']
        run['earth_magnetic_field_z_muT'] = location_config[
            'earth_magnetic_field_z_muT']
        run['atmosphere_id'] = __atmosphere_str_to_corsika_id(
            location_config["atmosphere"])

        run['particle_id'] = __particle_str_to_corsika_id(
            particle_config['primary_particle'])
        run['cone_max_scatter_angle_deg'] = particle_config[
            'max_scatter_angle_deg']
        run['instrument_radius'] = plenoscope_geometry[
                'expected_imaging_system_aperture_radius']*1.1
        run['light_field_geometry_path'] = light_field_geometry_path
        run['particle_truth_table_path'] = op.join(
            particle_truth_table_dir, run_id_str+".jsonl")
        run['trigger_truth_table_path'] = op.join(
            trigger_truth_table_dir, run_id_str+".jsonl")
        run['past_trigger_table_path'] = op.join(
            past_trigger_table_dir, run_id_str+".jsonl")
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
            run_id_str+'_merlict.stdout')
        run['merlict_stderr_path'] = op.join(
            od,
            'stdout',
            run_id_str+'_merlict.stderr')
        run['corsika_stdout_path'] = op.join(
            od,
            'stdout',
            run_id_str+'_corsika.stdout')
        run['corsika_stderr_path'] = op.join(
            od,
            'stdout',
            run_id_str+'_corsika.stderr')
        run['trigger_patch_threshold'] = trigger_patch_threshold
        run['trigger_integration_time_in_slices'] = \
            trigger_integration_time_in_slices
        jobs.append(run)
    return jobs


def concatenate_files(wildcard_path, out_path):
    in_paths = glob.glob(wildcard_path)
    with open(out_path, "wt") as fout:
        for in_path in in_paths:
            with open(in_path, "rt") as fin:
                fout.write(fin.read())
