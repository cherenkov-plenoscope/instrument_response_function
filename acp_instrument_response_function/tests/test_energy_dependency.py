import acp_instrument_response_function as irf
import numpy as np

def test_energy_dependencie():
    NUM_ENERGY_BINS = 100

    particle = {
        "primary_particle": "electron",
        "max_scatter_angle_deg": 3.25,
        "energy":             [0.23, 0.8, 3.0, 35,   81,   432,  1000],
        "max_scatter_radius": [150,  150, 460, 1100, 1235, 1410, 1660]}

    magnetic_deflection = {
        "energy": [10, 5, 3, 1],
        "instrument_x": [1, 5, 10, 15],
        "instrument_y": [10, 50, 250, 1250],
        "azimuth_phi_deg": [-.1, -1, -3, -5],
        "zenith_theta_deg": [1, 5, 10, 25],}

    energy_dependencies = irf._estimate_energy_dependencies(
        particle_config=particle,
        magnetic_deflection_config=magnetic_deflection,
        num_energy_bins=NUM_ENERGY_BINS)
    edp = energy_dependencies

    assert len(edp["energy_bin_edges"]) == NUM_ENERGY_BINS + 1
    assert len(edp["max_scatter_radius_in_bin"]) == NUM_ENERGY_BINS
    assert len(edp["magnetic_deflection_correction"]) == NUM_ENERGY_BINS
    assert len(edp["instrument_x"]) == NUM_ENERGY_BINS
    assert len(edp["instrument_y"]) == NUM_ENERGY_BINS
    assert len(edp["azimuth_phi_deg"]) == NUM_ENERGY_BINS
    assert len(edp["zenith_theta_deg"]) == NUM_ENERGY_BINS

    for energy_bin in range(NUM_ENERGY_BINS):
        if not edp["magnetic_deflection_correction"][energy_bin]:
            assert edp["instrument_x"][energy_bin] == 0.
            assert edp["instrument_y"][energy_bin] == 0.
            assert edp["azimuth_phi_deg"][energy_bin] == 0.
            assert edp["zenith_theta_deg"][energy_bin] == 0.
        else:
            assert edp["instrument_x"][energy_bin] != 0.
            assert edp["instrument_y"][energy_bin] != 0.
            assert edp["azimuth_phi_deg"][energy_bin] != 0.
            assert edp["zenith_theta_deg"][energy_bin] != 0.

    assert np.min(edp["energy_bin_edges"]) == 1.
    assert np.max(edp["energy_bin_edges"]) == 1000.