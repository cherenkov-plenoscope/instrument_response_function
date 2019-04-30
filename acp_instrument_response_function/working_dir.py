import os
import shutil
import corsika_wrapper as cw


def directory_structure(working_dir):
    p = {}
    p['main'] = {}
    p['main']['dir'] = os.path.abspath(working_dir)

    p['main']['input'] = {}
    p['main']['input']['dir'] = os.path.join(p['main']['dir'], 'input')

    p['main']['stdout'] = {}
    p['main']['stdout']['dir'] = os.path.join(p['main']['dir'], 'stdout')

    p['main']['intermediate_results_of_runs'] = {}
    p['main']['intermediate_results_of_runs']['dir'] = os.path.join(
        p['main']['dir'],
        'intermediate_results_of_runs')

    p['main']['input']['acp_detector'] = os.path.join(
        p['main']['input']['dir'],
        'acp_detector')

    p['main']['input']['corsika_steering_card_template'] = os.path.join(
        p['main']['input']['dir'],
        'corsika_steering_card_template.txt')

    p['main']['input']['mct_acp_config'] = os.path.join(
        p['main']['input']['dir'],
        'mct_acp_config.json')

    p['main']['acp_event_responses'] = os.path.join(
        p['main']['dir'],
        'acp_event_responses.json.gz')

    p['main']['input']['header'] = os.path.join(
        p['main']['input']['dir'],
        'header.txt')

    return p
