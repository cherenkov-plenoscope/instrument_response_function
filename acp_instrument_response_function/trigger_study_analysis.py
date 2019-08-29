import glob
import json
import gzip
import os
import numpy as np
from . import utils as irfutils
from . import json_in_out


def read_intermediate_results(path):
    events = []
    for p in glob.glob(os.path.join(path, '*.gz')):
        with gzip.open(p, 'rt') as fin:
            d = json.loads(fin.read())
            for item in d:
                events.append(item)
    return events


def flatten(events):
    event_ids = []
    run_ids = []
    num_true_cherenkov_photons = []
    num_exposure_time_slices = []
    time_slice_durations = []
    num_trigger_integration_time_slices = []
    trigger_responses = []
    energies = []
    max_scatter_radii = []
    scatter_radii = []
    zenith_distances = []
    first_interaction_height = []
    for e in events:
        event_ids.append(e['id']['event'])
        run_ids.append(e['id']['run'])
        num_exposure_time_slices.append(
            e['refocus_sum_trigger'][0]['exposure_time_in_slices'])
        time_slice_durations.append(
            e['acp']['light_field_sensor']['time_slice_duration'])
        num_trigger_integration_time_slices.append(
            e['refocus_sum_trigger'][0]['integration_time_in_slices'])
        energies.append(e['simulation_truth']['energy'])
        num_true_cherenkov_photons.append(e['num_air_shower_pulses'])
        max_scatter_radii.append(e['simulation_truth']['scatter_radius'])
        scatter_radii.append(
            np.hypot(
                e['simulation_truth']['core_position']['x'],
                e['simulation_truth']['core_position']['y']))
        zenith_distances.append(
            e['simulation_truth']['zenith'])
        t0 = e['refocus_sum_trigger'][0]['patch_threshold']
        t1 = e['refocus_sum_trigger'][1]['patch_threshold']
        t2 = e['refocus_sum_trigger'][2]['patch_threshold']
        trigger_responses.append(np.array([t0, t1, t2]))
        first_interaction_height.append(
            e['simulation_truth']['first_interaction_height'])
    return {
        'run_ids': np.array(run_ids),
        'event_ids': np.array(event_ids),
        'trigger_responses': np.array(trigger_responses),
        'num_true_cherenkov_photons': np.array(num_true_cherenkov_photons),
        'num_exposure_time_slices': np.array(num_exposure_time_slices),
        'time_slice_durations': np.array(time_slice_durations),
        'energies': np.array(energies),
        'max_scatter_radii': np.array(max_scatter_radii),
        'scatter_radii': np.array(scatter_radii),
        'zenith_distances': np.array(zenith_distances),
        'first_interaction_height': np.array(first_interaction_height),
    }


def append_trigger_mask(events, patch_threshold):
    trigger_layer_mask = events['trigger_responses'] >= patch_threshold
    events['trigger_mask'] = trigger_layer_mask.sum(axis=1) >= 1
    return events


def estimate_effective_area(
    max_scatter_radii,
    energies,
    trigger_mask,
):
    max_scatter_area = np.pi*max_scatter_radii**2
    num_energy_bins = int(np.sqrt(energies.shape[0])/6)

    number_energy_bins = int(np.sqrt(energies.shape[0])/4)
    energy_bin_edges = np.logspace(
        np.log10(np.min(energies)),
        np.log10(np.max(energies)),
        number_energy_bins)

    num_thrown = np.histogram(
        energies,
        bins=energy_bin_edges)[0]

    num_detected = np.histogram(
        energies,
        weights=trigger_mask.astype(np.int),
        bins=energy_bin_edges)[0]

    area_thrown = np.histogram(
        energies,
        weights=max_scatter_area,
        bins=energy_bin_edges)[0]

    area_detected = np.histogram(
        energies,
        weights=max_scatter_area*trigger_mask,
        bins=energy_bin_edges)[0]

    effective_area = area_detected/area_thrown*(
        area_thrown/num_thrown)

    return {
        'energy_bin_edges': energy_bin_edges,
        'num_thrown': num_thrown,
        'num_detected': num_detected,
        'area_thrown': area_thrown,
        'area_detected': area_detected,
        'effective_area': effective_area, }


def export_acceptance(
    path,
    effective_area,
    steering_card,
    acp_geometry,
):
    max_zenith_scatter = np.deg2rad(irfutils.max_zenith_scatter_angle_deg(
        steering_card['source_geometry'],
        acp_geometry['max_FoV_diameter_deg']))

    scatter_solid_angle = irfutils.scatter_solid_angle(max_zenith_scatter)

    log10_E_TeV = np.log10(
        effective_area['energy_bin_edges'][0: -1]*1e-3)

    acceptence_cm2 = effective_area['effective_area']*1e2*1e2

    out = '# Atmospheric-Cherenkov-Plenoscope\n'
    out += '# --------------------------------\n'
    out += '#\n'
    out += '# Sebastian A. Mueller\n'
    out += '# Max Ludwig Ahnen\n'
    out += '# Dominik Neise\n'
    out += '# Adrian Biland\n'
    out += '#\n'
    out += '# steering card\n'
    out += '# -------------\n'
    card_json = json.dumps(steering_card, indent=2).split('\n')
    for line in card_json:
        out += '# ' + line + '\n'
    out += '#\n'
    if scatter_solid_angle > 0.0:
        out += '# log10(Primary Particle Energy) [log10(TeV)], '
        out += 'Effective Acceptance [sr*cm^2], '
        acceptence_cm2 *= scatter_solid_angle
    else:
        out += '# log10(Primary Particle Energy) [log10(TeV)], '
        out += 'Effective Area [cm^2], '
    out += 'number thrown [#], number detected [#]\n'

    for i in range(len(log10_E_TeV)):
        if effective_area['num_thrown'][i] > 0:
            out += '{e:f}, {a:f}, {nt:d}, {nd:d}\n'.format(
                e=log10_E_TeV[i],
                a=acceptence_cm2[i],
                nt=effective_area['num_thrown'][i],
                nd=effective_area['num_detected'][i])

    with open(path, 'wt') as fout:
        fout.write(out)


def run_analysis(path, patch_threshold=67):
    os.makedirs(os.path.join(path, 'results'), exist_ok=True)
    events = flatten(
        read_intermediate_results(
            os.path.join(path, 'intermediate_results_of_runs')))
    events = append_trigger_mask(
        events=events,
        patch_threshold=patch_threshold)

    effective_area = estimate_effective_area(
        max_scatter_radii=events['max_scatter_radii'],
        energies=events['energies'],
        trigger_mask=events['trigger_mask'])

    steering_card = irfutils.read_json(
        os.path.join(path, 'input', 'particle_steering_card.json'))
    acp_geometry = irfutils.read_acp_design_geometry(
        os.path.join(
            path, 'input', 'acp_detector', 'input', 'scenery', 'scenery.json'))

    export_acceptance(
        path=os.path.join(path, 'results', 'irf.csv'),
        effective_area=effective_area,
        steering_card=steering_card,
        acp_geometry=acp_geometry,)

    json_in_out.write_json_dictionary(
        result=effective_area,
        path=os.path.join(path, 'results', 'effective_area.json'),
        indent=2)

    json_in_out.write_json_dictionary(
        result=events,
        path=os.path.join(path, 'results', 'events.json'),
        indent=2)
