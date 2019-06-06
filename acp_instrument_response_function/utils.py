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
    raise ValueError(
        "The atmosphere_model '{:s}' is not supported".format(model))


def max_zenith_scatter_angle_deg(source_geometry, acp_fov):
    if source_geometry == 'point':
        return 0.0
    elif source_geometry == 'diffuse':
        return acp_fov
    raise ValueError(
        "The source_geometry '{:s}' is not supported".format(source_geometry))


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
    max_scatter_radius_in_bin,
    directory
):
    np.savetxt(
        os.path.join(directory, 'max_scatter_radius_vs_energy.csv'),
        np.c_[energy_bin_edges[1:], max_scatter_radius_in_bin],
        delimiter=', ',
        header='upper bin-edge energy/Gev, max_scatter_radius/m')


def make_corsika_steering_card(
    random_seed,
    run_number,
    number_events_in_run,
    primary_particle,
    E_start,
    E_stop,
    max_zenith_scatter_angle_deg,
    max_scatter_radius,
    observation_level_altitude_asl,
    instrument_radius,
    atmosphere_model,
    earth_magnetic_field_x_muT,
    earth_magnetic_field_z_muT
):
    c = OrderedDict()
    c['RUNNR'] = ['{:d}'.format(run_number)]
    c['EVTNR'] = ['1']
    c['NSHOW'] = ['{:d}'.format(number_events_in_run)]
    c['PRMPAR '] = ['{:d}'.format(primary_particle)]
    c['ESLOPE'] = ['-1.0']
    c['ERANGE'] = [
        '{E_start:3.3e} {E_stop:3.3e}'.format(E_start=E_start, E_stop=E_stop)]
    c['THETAP'] = ['0. {:3.3e}'.format(max_zenith_scatter_angle_deg)]
    c['PHIP'] = ['0.  360.']
    c['SEED'] = [
        '{:d} 0 0'.format(random_seed + run_number),
        '{:d} 0 0'.format(random_seed + run_number + 1),
        '{:d} 0 0'.format(random_seed + run_number + 2),
        '{:d} 0 0'.format(random_seed + run_number + 3), ]
    c['OBSLEV'] = ['{:3.3e}'.format(observation_level_altitude_asl*1e2)]
    c['FIXCHI'] = ['0.']
    c['MAGNET'] = ['{BX:3.3e} {BZ:3.3e}'.format(
        BX=earth_magnetic_field_x_muT,
        BZ=earth_magnetic_field_Z_muT)]
    c['ELMFLG'] = ['T T']
    c['MAXPRT'] = ['1']
    c['PAROUT'] = ['F F']
    c['TELESCOPE'] = ['0. 0. 0. {:3.3e}'.format(instrument_radius*1e2)]
    c['ATMOSPHERE'] = ['{:d} T'.format(atmosphere_model)]
    c['CWAVLG'] = ['250 700']
    c['CSCAT'] = ['1 {:3.3e} 0.0'.format(max_scatter_radius*1e2)]
    c['CERQEF'] = ['F T F']  # pde, atmo, mirror
    c['CERSIZ'] = ['1']
    c['CERFIL'] = ['F']
    c['TSTART'] = ['T']
    c['EXIT'] = []
    return c


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
    number_runs,
):
    assert (energy == np.sort(energy)).all(), (
        "Expected the energies to be sorted")

    energy_bin_edges = np.logspace(
        np.log10(np.min(energy)),
        np.log10(np.max(energy)),
        number_runs + 1)
    max_scatter_radius_in_bin = interpolate_with_power10(
        x=energy_bin_edges[1:],
        xp=energy,
        fp=max_scatter_radius)
    return max_scatter_radius_in_bin, energy_bin_edges


def run_acp(
    corsika_run_path,
    output_path,
    acp_detector_path,
    mct_acp_propagator_path,
    mct_acp_config_path,
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
            mct_acp_propagator_path,
            '-l', acp_detector_path,
            '-c', mct_acp_config_path,
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
