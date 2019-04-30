import json
import os


def make_summary_header(cfg):
    out = ''
    out += '# Cherenkov-Plenoscope\n'
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
            out += '# '+'    '+key.replace('\n', '')+' '
            out += entry.replace('\n', '')+'\n'
    return out


def acp_information(cfg):
    acp_path = cfg['path']['main']['input']['acp_detector']
    scenery_path = os.path.join(acp_path, 'input', 'scenery', 'scenery.json')
    with open(scenery_path, "rt") as fin:
        tree = json.loads(fin.read())
    txt = json.dumps(tree, indent=2)
    out = ''
    for line in txt.splitlines():
        out += '#   ' + line
    return out