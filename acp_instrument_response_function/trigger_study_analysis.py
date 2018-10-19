import glob
import json
import gzip
import os
import numpy as np
import matplotlib.pyplot as plt
from os.path import join
from . import utils as irfutils


def run_analysis(path, patch_threshold=67):
    figsize = (8, 4)
    dpi = 240
    ax_size = (0.13, 0.13, 0.84, 0.84)

    os.makedirs(join(path, 'results'), exist_ok=True)

    events = []
    for p in glob.glob(os.path.join(path, 'intermediate_results_of_runs', '*.gz')):
        with gzip.open(p, 'rt') as fin:
            d = json.loads(fin.read())
            for item in d:
                events.append(item)

    num_air_shower_photons = []
    exposure_times = []
    thresholds = []
    energies = []
    max_scatter_radii = []
    scatter_radii = []
    zenith_distances = []
    for e in events:
        exposure_times.append(
            e['refocus_sum_trigger'][0]['exposure_time_in_slices'])
        energies.append(e['simulation_truth']['energy'])
        num_air_shower_photons.append(e['num_air_shower_pulses'])
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
        thresholds.append(np.array([t0, t1, t2]))
    thresholds = np.array(thresholds)
    num_air_shower_photons = np.array(num_air_shower_photons)
    exposure_times = np.array(exposure_times)
    energies = np.array(energies)
    max_scatter_radii = np.array(max_scatter_radii)
    scatter_radii = np.array(scatter_radii)
    zenith_distances = np.array(zenith_distances)

    # Trigger
    # -------
    trigger_mask = ((thresholds >= patch_threshold).sum(axis=1)) >= 1

    bins = np.zeros(22)
    bins[1] = 1
    for b in range(bins.shape[0]):
        if b > 1:
            bins[b] = np.sqrt(2)*bins[b-1]

    fig = plt.figure()
    ax1 = fig.add_axes([0.1, 0.75, 0.8, 0.2], xticklabels=[])
    ax2 = fig.add_axes([0.1, 0.1, 0.8, 0.6], ylim=(-0.05, 1.05))

    wt = np.histogram(
        num_air_shower_photons,
        weights=trigger_mask.astype(np.int),
        bins=bins)[0]

    wwot = np.histogram(
        num_air_shower_photons,
        bins=bins)[0]

    relative_uncertainties = np.sqrt(wwot)/wwot

    ax2.step(bins[:-1], wt/wwot, color='C0')

    w = wt/wwot
    w_low = w - w*relative_uncertainties
    w_upp = w + w*relative_uncertainties

    EXPOSURE_TIME = 50e-9
    accidental_rate = 1/(EXPOSURE_TIME/w[0])
    accidental_rate_uncertainty = accidental_rate*(np.sqrt(wwot[0])/wwot[0])

    for i, b in enumerate(bins):
        if i > 0 and i < len(bins) - 1:
            ax2.fill_between(
                [bins[i-1], bins[i]],
                w_low[i],
                w_upp[i],
                alpha=0.2,
                color='C0')

    ax1.set_title(
        'Accidental rate: ' + str(np.round(accidental_rate, 0)) +
        ' +- ' + str(np.round(accidental_rate_uncertainty, 0)) + ' s**(-1)')
    ax1.step(bins[:-1], wwot, 'k')
    ax1.semilogx()
    ax1.semilogy()
    ax1.set_ylabel('# events/1')
    ax2.semilogx()
    ax2.set_xlabel('# detected air-shower-photons/1')
    ax2.set_ylabel('probability to trigger/1')
    plt.savefig(os.path.join(path, 'results', 'trigger.png'))

    with open(join(path, 'results', 'cherenkov_photons.json'), 'wt') as fout:
        fout.write(json.dumps({
            'true_cherenkov_photons_bin_edges':
                bins.tolist(),
            'true_cherenkov_photons_bin_counts_triggered':
                wt.tolist(),
            'true_cherenkov_photons_bin_counts_thrown':
                wwot.tolist()
            },
            indent=2))

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

    area_detected_trigger = np.histogram(
        energies,
        weights=max_scatter_area*trigger_mask,
        bins=energy_bin_edges)[0]

    area_detected_analysis = np.histogram(
        energies,
        weights=max_scatter_area*trigger_mask*(num_air_shower_photons >= 100),
        bins=energy_bin_edges)[0]

    area_detected_100pe = np.histogram(
        energies,
        weights=max_scatter_area*(num_air_shower_photons >= 100),
        bins=energy_bin_edges)[0]

    effective_area_trigger = area_detected_trigger/area_thrown*(
        area_thrown/num_thrown)

    fig = plt.figure(figsize=figsize, dpi=dpi)
    ax = fig.add_axes(ax_size)
    l0, = plt.step(
        energy_bin_edges[:-1],
        effective_area_trigger,
        'k',
        label='trigger')
    ax.legend(handles=[l0])
    ax.semilogx()
    ax.semilogy()
    ax.set_ylabel(r'effective area/m$^2$')
    ax.set_xlabel(r'energy/GeV')
    ax.spines['right'].set_visible(False)
    ax.spines['top'].set_visible(False)
    ax.grid(color='k', linestyle='-', linewidth=0.66, alpha=0.1)
    fig.savefig(os.path.join(path, 'results', 'effective_area.png'))

    steering_card = irfutils.read_json(join(path, 'input', 'steering.json'))
    acp_geometry = irfutils.read_acp_design_geometry(join(
        path, 'input',
        'acp_detector',
        'input',
        'scenery',
        'scenery.xml'))

    max_zenith_scatter = np.deg2rad(irfutils.max_zenith_scatter_angle_deg(
        steering_card['source_geometry'],
        acp_geometry['max_FoV_diameter_deg']))

    scatter_solid_angle = irfutils.scatter_solid_angle(max_zenith_scatter)

    log10_E_TeV = np.log10(energy_bin_edges[0: -1]*1e-3)

    acceptence_cm2 = effective_area_trigger*1e2*1e2

    out =  '# Atmospheric-Cherenkov-Plenoscope\n'
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
        if num_thrown[i] > 0:
            out += '{e:f}, {a:f}, {nt:d}, {nd:d}\n'.format(
                e=log10_E_TeV[i],
                a=acceptence_cm2[i],
                nt=num_thrown[i],
                nd=num_detected[i])

    with open(os.path.join(path, 'results', 'irf.csv'), 'wt') as fout:
        fout.write(out)


    def add_hisogram_semilogy(
        ax,
        bin_counts,
        bin_counts_error_low,
        bin_counts_error_high,
        bin_edges,
        color='k',
        alpha_boxes=0.1):
        for i, y in enumerate(bin_counts):
            ax.plot(
                [bin_edges[i], bin_edges[i + 1]],
                [bin_counts[i], bin_counts[i]],
                color)

        for i, y in enumerate(bin_counts):
            ax.fill_between(
                x=[bin_edges[i], bin_edges[i + 1]],
                y1=[bin_counts_error_low[i], bin_counts_error_low[i]],
                y2=[bin_counts_error_high[i], bin_counts_error_high[i]],
                color=color,
                alpha=alpha_boxes,
                linewidth=0)


    # Visualize impact-scatter-range
    scatter_radius_squared_bin_edges = np.linspace(
        0,
        np.max(scatter_radii[trigger_mask])**2,
        np.int(np.sqrt(np.sum(trigger_mask))/2))

    scatter_radius_squared_bin_counts_triggered = np.histogram(
        scatter_radii[trigger_mask]**2,
        scatter_radius_squared_bin_edges)[0]

    scatter_radius_squared_bin_counts_thrown = np.histogram(
        scatter_radii**2,
        scatter_radius_squared_bin_edges)[0]

    with open(join(path, 'results', 'scatter_radius.json'), 'wt') as fout:
        fout.write(json.dumps({
            'scatter_radius_squared_bin_edges':
                scatter_radius_squared_bin_edges.tolist(),
            'scatter_radius_squared_bin_counts_triggered':
                scatter_radius_squared_bin_counts_triggered.tolist(),
            'scatter_radius_squared_bin_counts_thrown':
                scatter_radius_squared_bin_counts_thrown.tolist()
            },
            indent=2))

    count_error = (np.sqrt(scatter_radius_squared_bin_counts_triggered)/
        scatter_radius_squared_bin_counts_triggered)
    count_ratio = (
            scatter_radius_squared_bin_counts_triggered/
            scatter_radius_squared_bin_counts_thrown)

    fig = plt.figure(figsize=figsize, dpi=dpi)
    ax = fig.add_axes(ax_size)
    add_hisogram_semilogy(
        ax=ax,
        bin_counts=1e2*count_ratio,
        bin_counts_error_low=1e2*count_ratio*(1 - count_error),
        bin_counts_error_high=1e2*count_ratio*(1 + count_error),
        bin_edges=1e-6*scatter_radius_squared_bin_edges,)
    ax.set_xlabel(r'(Scatter-radius)$^2$/(km)$^2$')
    ax.set_ylabel(r'Trigger-probability/%')
    ax.spines['right'].set_visible(False)
    ax.spines['top'].set_visible(False)
    ax.grid(color='k', linestyle='-', linewidth=0.66, alpha=0.1)
    fig.savefig(os.path.join(path, 'results', 'scatter_radius.png'))


    fig = plt.figure(figsize=figsize, dpi=dpi)
    ax = fig.add_axes(ax_size)
    for i in range(scatter_radius_squared_bin_counts_triggered.shape[0]):
        ax.plot(
            1e-6*np.array([scatter_radius_squared_bin_edges[i], scatter_radius_squared_bin_edges[i + 1]]),
            [scatter_radius_squared_bin_counts_triggered[i], scatter_radius_squared_bin_counts_triggered[i]],
            'k--')
        ax.plot(
            1e-6*np.array([scatter_radius_squared_bin_edges[i], scatter_radius_squared_bin_edges[i + 1]]),
            [scatter_radius_squared_bin_counts_thrown[i], scatter_radius_squared_bin_counts_thrown[i]],
            'k')
    ax.semilogy()
    ax.set_xlabel(r'(Scatter-radius)$^2$/(km)$^2$')
    ax.set_ylabel(r'Number events/1')
    ax.spines['right'].set_visible(False)
    ax.spines['top'].set_visible(False)
    ax.grid(color='k', linestyle='-', linewidth=0.66, alpha=0.1)
    fig.savefig(join(path, 'results', 'scatter_radius_thrown_and_triggered.png'))


    if np.max(zenith_distances[trigger_mask])**2 > 0.0:
        scatter_angle_squared_bin_edges = np.linspace(
            0,
            np.max(np.rad2deg(zenith_distances[trigger_mask]))**2,
            np.int(np.sqrt(np.sum(trigger_mask))/2))

        scatter_angle_squared_bin_counts_triggered = np.histogram(
            np.rad2deg(zenith_distances[trigger_mask])**2,
            scatter_angle_squared_bin_edges)[0]

        scatter_angle_squared_bin_counts_thrown = np.histogram(
            np.rad2deg(zenith_distances)**2,
            scatter_angle_squared_bin_edges)[0]

        with open(join(path, 'results', 'scatter_angle.json'), 'wt') as fout:
            fout.write(json.dumps({
                'scatter_angle_squared_bin_edges':
                    scatter_angle_squared_bin_edges.tolist(),
                'scatter_angle_squared_bin_counts_triggered':
                    scatter_angle_squared_bin_counts_triggered.tolist(),
                'scatter_angle_squared_bin_counts_thrown':
                    scatter_angle_squared_bin_counts_thrown.tolist(),
                },
                indent=2))

        count_error = (np.sqrt(scatter_angle_squared_bin_counts_triggered)/
            scatter_angle_squared_bin_counts_triggered)
        count_ratio = (
                scatter_angle_squared_bin_counts_triggered/
                scatter_angle_squared_bin_counts_thrown)

        fig = plt.figure(figsize=figsize, dpi=dpi)
        ax = fig.add_axes(ax_size)
        add_hisogram_semilogy(
            ax=ax,
            bin_counts=1e2*count_ratio,
            bin_counts_error_low=1e2*count_ratio*(1 - count_error),
            bin_counts_error_high=1e2*count_ratio*(1 + count_error),
            bin_edges=scatter_angle_squared_bin_edges,)
        ax.set_xlabel(r'(Scatter-angle)$^2$/(deg)$^2$')
        ax.set_ylabel(r'Trigger-probability/%')
        ax.spines['right'].set_visible(False)
        ax.spines['top'].set_visible(False)
        ax.grid(color='k', linestyle='-', linewidth=0.66, alpha=0.1)
        ax.axvline(x=3.25**2, color='k', linestyle=':')
        fig.savefig(os.path.join(path, 'results', 'scatter_angle.png'))


        fig = plt.figure(figsize=figsize, dpi=dpi)
        ax = fig.add_axes(ax_size)
        for i in range(scatter_angle_squared_bin_counts_triggered.shape[0]):
            ax.plot(
                [scatter_angle_squared_bin_edges[i], scatter_angle_squared_bin_edges[i + 1]],
                [scatter_angle_squared_bin_counts_triggered[i], scatter_angle_squared_bin_counts_triggered[i]],
                'k--')
            ax.plot(
                [scatter_angle_squared_bin_edges[i], scatter_angle_squared_bin_edges[i + 1]],
                [scatter_angle_squared_bin_counts_thrown[i], scatter_angle_squared_bin_counts_thrown[i]],
                'k')
        ax.semilogy()
        ax.set_xlabel(r'(Scatter-angle)$^2$/(deg)$^2$')
        ax.set_ylabel(r'Number events/1')
        ax.spines['right'].set_visible(False)
        ax.spines['top'].set_visible(False)
        ax.grid(color='k', linestyle='-', linewidth=0.66, alpha=0.1)
        ax.axvline(x=3.25**2, color='k', linestyle=':')
        fig.savefig(join(path, 'results', 'scatter_angle_thrown_and_triggered.png'))

    plt.close('all')
