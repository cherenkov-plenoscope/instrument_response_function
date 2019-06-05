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
    assert s["expected_imaging_system_focal_length"] == 106.5
    assert s["expected_imaging_system_aperture_radius"] == 35.5
    assert s["max_FoV_diameter_deg"] == 6.5
    assert s["hex_pixel_FoV_flat2flat_deg"] == 0.06667
    assert s["num_paxel_on_pixel_diagonal"] == 9
    assert s["housing_overhead"] == 1.1
    assert (
        s["lens_refraction_vs_wavelength"] ==
        "lens_refraction_vs_wavelength")
    assert (
        s["bin_reflection_vs_wavelength"] ==
        "mirror_reflectivity_vs_wavelength")
