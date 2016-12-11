import numpy as np
import matplotlib.pyplot as plt
from .working_dir import directory_structure
from .json_in_out import read_json_dictionary


def export_effective_area(
    input_path,
    detector_responses_key,
    detector_response_threshold,
    output_path,
    bins=15):
    
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

    survived_histogram = np.histogram(
        survived_energies, 
        bins=bin_edges,     
        weights=scatter_area[above_threshold])[0]
    
    thrown_histogram = np.histogram(
        thrown_energies, 
        bins=bin_edges)[0]

    return {
        'energy_bin_edges': bin_edges,
        'thrown': thrown_histogram,
        'survived': survived_histogram,
        'survived_over_thrown': survived_histogram/thrown_histogram}


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
    out =''
    out+='#\n'
    out+='# Detector response:\n'
    out+='#     key: '+effective_area['detector_responses_key']+'\n'
    out+='#     threshold: '+float2str(effective_area['detector_response_threshold'])+'\n'
    out+='#\n'
    out+='# Energy [TeV], Area[cm^2]\n'

    GeV2TeV = 1e-3
    m2cm = 1e2 

    energies = effective_area['energy_bin_edges']
    for i, area in enumerate(effective_area['survived_over_thrown']):
        out+=float2str(energies[i]*GeV2TeV)+', '+float2str(area*m2cm*m2cm)+'\n'
    return out


def save_effective_area_plot(effective_area, output_path):
    effective_area_histogram = effective_area['survived_over_thrown']
    energy_bin_edges = effective_area['energy_bin_edges']
    plt.figure()
    effective_area_histogram_steps = np.hstack(
        (   effective_area_histogram[0], 
            effective_area_histogram))
    plt.step(energy_bin_edges, effective_area_histogram_steps) 
    plt.xlabel('Energy/GeV')
    plt.ylabel('Area/m^2')
    plt.loglog()
    plt.savefig(output_path)