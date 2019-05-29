import acp_instrument_response_function as irf
import pkg_resources
import os

scenery_path = pkg_resources.resource_filename(
    'acp_instrument_response_function',
    os.path.join(
        'tests',
        'resources',
        'scenery.json'))

def test_parse_scenery():
    s = irf.utils.read_acp_design_geometry(scenery_path)