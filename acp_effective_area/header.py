import xml.etree.ElementTree
import os

def make_summary_header(cfg):
    out  = ''
    out += '# Atmospheric Cherenkov Plenoscope (ACP)\n'
    out += '#\n'
    out += '# Authors:\n'
    out += '#     Sebastian A. Mueller\n'
    out += '#     Max L. Ahnen\n'
    out += '#     Dominik Neise\n'
    out += '#     (ETH Zurich 2016)\n'
    out += '#\n'
    out += '# Plenoscope light field sensor:\n'
    out += acp_information(cfg)
    out += '#\n'    
    out += '# CORSIKA steering card template:\n'
    out += particle_information(cfg['corsika_steering_card_template'])
    with open(cfg['path']['main']['input']['header'], 'w') as f:
        f.write(out)


def particle_information(steering_card_template):
    out = ''
    for key in steering_card_template:
        for entry in steering_card_template[key]:
            out += '# '+'    '+key.replace('\n', '')+' '+entry.replace('\n', '')+'\n'
    return out


def acp_information(cfg): 
    acp_path = cfg['path']['main']['input']['acp_detector']
    scenery_path = os.path.join(acp_path, 'input/scenery/scenery.xml')
    tree = xml.etree.ElementTree.parse(scenery_path).getroot()

    acp_node = tree.find('frame').find('light_field_sensor').find('set_light_field_sensor')

    info = {
        'expected_imaging_system_focal_length': acp_node.get('expected_imaging_system_focal_length'),
        'expected_imaging_system_aperture_radius': acp_node.get('expected_imaging_system_aperture_radius'),
        'max_FoV_diameter_deg': acp_node.get('max_FoV_diameter_deg'),
        'hex_pixel_FoV_flat2flat_deg': acp_node.get('hex_pixel_FoV_flat2flat_deg'),
        'housing_overhead': acp_node.get('housing_overhead')
    }

    out = ''
    for key in info:
        out += '# '+'    '+key+' '+info[key]+'\n'
    return out