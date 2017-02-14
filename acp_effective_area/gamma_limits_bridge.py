"""
A bridge to the high level analysis [gamma_limits_sensitivity](
https://github.com/mahnen/gamma_limits_sensitivity) to produce rate plots and 
spectral exclusion zone plots. 
"""
import numpy as np
import matplotlib.pyplot as plt
import corsika_wrapper as cw
from .working_dir import directory_structure
from .json_in_out import read_json_dictionary


def export_effective_area(
    input_path,
    detector_responses_key,
    detector_response_threshold,
    output_path,
    bins=15):
    """
    Outputs a text (CSV) file with the effective area [cm^2], or effective 
    Aperture [sr*cm^2]. Crucial instrument and simulation settings are machine
    written into the text file to keep track of the results. This output is
    intended for the high level analysis bridge [gamma_limits_sensitivity](
    https://github.com/mahnen/gamma_limits_sensitivity)

    Parameter
    ---------
    input_path                      Path to the output directory of the 
                                    effective area production.
    detector_responses_key          The dictionary key to the detector response 
                                    to be taken into account 
                                    (e.g. raw_lixel_sum).
    detector_response_threshold     A threshold upper limit value to the 
                                    detector response in question.
    output_path                     Path to the CSV text file with the high 
                                    level effective Area.
    bins                            The number of bins in the effective area 
                                    energy binning. 
    """
    
    path_cfg = directory_structure(input_path)
    acp_event_responses = read_json_dictionary(
        path_cfg['main']['acp_event_responses'])

    for key in acp_event_responses:
        acp_event_responses[key] = np.array(acp_event_responses[key])

    effective_area = make_effective_area(
        acp_event_responses=acp_event_responses,
        detector_responses_key=detector_responses_key,
        detector_response_threshold=detector_response_threshold,
        bins=bins)

    corsika_steering_card = cw.read_steering_card(
        path_cfg['main']['input']['corsika_steering_card_template'])

    effective_area['scatter_solid_angle'] = scatter_solid_angle(
        max_scatter_zenith_distance_in(corsika_steering_card))

    with open(path_cfg['main']['input']['header'], 'r') as f:
        header = f.read()

    effective_area_csv = make_effective_area_report(effective_area)

    with open(output_path, 'w') as o:
        o.write(header)
        o.write(effective_area_csv)

    save_effective_area_plot(effective_area, output_path+'.png')


def make_effective_area_histogram(
    primary_particle_energies,
    detector_responses,
    detector_response_threshold,
    scatter_area,
    bins=15):
    E_min_log10 = np.floor(np.log10(primary_particle_energies.min()))
    E_max_log10 = np.ceil(np.log10(primary_particle_energies.max()))        
    
    bin_edges = np.logspace(E_min_log10, E_max_log10, bins+1)

    above_threshold = detector_responses > detector_response_threshold
    survived_energies = primary_particle_energies[above_threshold]  
    thrown_energies = primary_particle_energies

    area_survived_vs_energy = np.histogram(
        survived_energies, 
        bins=bin_edges,     
        weights=scatter_area[above_threshold])[0]
    
    number_detected_vs_energy = np.histogram(
        survived_energies, 
        bins=bin_edges)[0] 

    number_thrown_vs_energy = np.histogram(
        thrown_energies, 
        bins=bin_edges)[0]

    return {
        'energy_bin_edges': bin_edges,
        'number_thrown': number_thrown_vs_energy,
        'number_detected': number_detected_vs_energy,
        'area_survived': area_survived_vs_energy,
        'effective_area': area_survived_vs_energy/number_thrown_vs_energy}


def make_effective_area(
    acp_event_responses, 
    detector_responses_key,
    detector_response_threshold,
    bins=15):
    
    scatter_area = np.pi*acp_event_responses['scatter_radius']**2.0

    Aeff = make_effective_area_histogram(
        primary_particle_energies=acp_event_responses['primary_particle_energy'],
        detector_responses=acp_event_responses[detector_responses_key],
        detector_response_threshold=detector_response_threshold,
        scatter_area=scatter_area,
        bins=bins)

    Aeff['detector_responses_key'] = detector_responses_key
    Aeff['detector_response_threshold'] = detector_response_threshold
    return Aeff


def float2str(numeric_value):
    return "{:.9f}".format(numeric_value)


def make_effective_area_report(effective_area):

    scatter_solid_angle = effective_area['scatter_solid_angle']
    out ='#\n'
    out+='# Scatter angle of primary particle:\n'
    out+='#     solid angle: '+float2str(scatter_solid_angle)+'sr\n'
    out+='#\n'
    out+='# Detector response:\n'
    out+='#     key: '+effective_area['detector_responses_key']+'\n'
    out+='#     threshold: '+float2str(effective_area['detector_response_threshold'])+'\n'
    out+='#\n'
    if scatter_solid_angle > 0.0:
        out+='# log10(Primary Particle Energy) [log10(TeV)], Effective Aperture [sr*cm^2], '
    else:
        out+='# log10(Primary Particle Energy) [log10(TeV)], Effective Area [cm^2], '
    out+='number thrown [#], number detected [#]\n'
    GeV2TeV = 1e-3
    m2cm = 1e2

    energies = effective_area['energy_bin_edges']
    for i, area in enumerate(effective_area['effective_area']):
        out+=float2str(np.log10(energies[i]*GeV2TeV))+', '
        if scatter_solid_angle > 0.0:
            out+=float2str(area*m2cm*m2cm*scatter_solid_angle)
        else:
            out+=float2str(area*m2cm*m2cm)
        out+=', '   
        out+=str(effective_area['number_thrown'][i])+', '
        out+=str(effective_area['number_detected'][i])+'\n'
    return out


def save_effective_area_plot(effective_area, output_path, overlay_magic_one=False):
    effective_area_vs_energy = effective_area['effective_area']
    energy_bin_edges = effective_area['energy_bin_edges']
    plt.figure()
    effective_area_vs_energy_steps = np.hstack(
        (   effective_area_vs_energy[0], 
            effective_area_vs_energy))
    plt.step(energy_bin_edges, effective_area_vs_energy_steps) 
    plt.xlabel('Energy/GeV')
    plt.ylabel('Area/m^2')
    plt.loglog()

    if overlay_magic_one:
        magic_one = magic_one_collection_area()
        plt.plot(
            magic_one[:,0], 
            magic_one[:,1], 
            'xg'
            label='MAGIC I')

    plt.savefig(output_path)


def max_scatter_zenith_distance_in(corsika_steering_card):
    thetap = corsika_steering_card['THETAP'][0]
    thetap = thetap.strip()
    max_zenith_distance_txt_deg = thetap.split()[1]
    max_zenith_distance_deg = float(max_zenith_distance_txt_deg)
    return np.deg2rad(max_zenith_distance_deg)


def scatter_solid_angle(max_scatter_zenith_distance):
    cap_hight = (1.0 - np.cos(max_scatter_zenith_distance));
    return 2.0*np.pi*cap_hight;


def magic_one_collection_area():
    """
    Returns 2D array 
    column 0: Energy [GeV]
    column 1: Area [m^2]

    5.8 to 384 GeV

    Taken from:
    'Supporting Online Material for: 
    Observation of Pulsed gamma-Rays Above 25 GeV From the Crab Pulsar with
    MAGIC'
    The MAGIC Collaboration,
    www.sciencemag.org/cgi/content/full/1164718/DC1
    Figure 3, sum-trigger, red
    200 percent paper scale
    """
    raw_from_figure = np.array([
    # energy [mm]  area [mm]
        [  1.5,     7.5],
        [  4.0,    15.5],
        [  7.0,    22.5],
        [ 10.0,    25.0],
        [ 13.0,    28.5],
        [ 15.5,    34.5],
        [ 18.5,    37.0],
        [ 21.0,    42.0],
        [ 24.0,    44.5],
        [ 26.5,    47.5],
        [ 29.5,    51.5],
        [ 32.5,    54.0],
        [ 35.5,    59.0],
        [ 38.5,    62.0],
        [ 41.0,    64.0],
        [ 44.0,    65.0],
        [ 46.5,    67.0],
        [ 50.0,    68.0],
        [ 52.5,    69.0],
        [ 55.0,    69.0],
        [ 57.5,    70.0],
        [ 61.0,    71.5],
        [ 63.0,    72.0],
        [ 66.5,    72.0],
        [ 69.0,    72.5],
        [ 72.0,    73.0],
        [ 75.0,    73.0],
        [ 77.5,    73.5],
        [ 81.0,    74.0],
        [ 83.0,    74.0],
        [ 86.5,    73.5],
        [ 89.0,    75.0],
        [ 92.0,    74.0],
        [ 95.0,    74.0],
        [ 97.5,    74.0],
        [ 100.5,    74.0],
        [ 103.5,    75.0],
        [ 106.5,    74.5],
        [ 109.0,    75.0],
    ])
    
    raw_from_figure[:,0] = 10.0**(0.01695*raw_from_figure[:,0]+0.737275)
    raw_from_figure[:,1] = 10.0**(0.06*raw_from_figure[:,1]+0.47)
    return raw_from_figure
