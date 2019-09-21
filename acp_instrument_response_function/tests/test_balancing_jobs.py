import acp_instrument_response_function as irf
import numpy as np


def test_balanced_jobs():
    jobs = irf.utils.make_jobs_with_balanced_runtime(
        energy_bin_edges=np.geomspace(0.25, 1000, 1001),
        num_events_in_energy_bin=512,
        max_num_events_in_run=128,
        max_cumsum_energy_in_run_in_units_of_highest_event_energy=10)

    expected_cumnum_events = 1000*512
    cumnum_events = 0
    for job in jobs:
        for run in job["runs"]:
            cumnum_events += run["num_events"]
    assert (
        np.abs(cumnum_events - expected_cumnum_events)\
        /expected_cumnum_events < 0.1)

    expected_cumsum_energy_in_job = 10*1000
    for job in jobs:
        cumsum_energy_in_job = 0
        for run in job["runs"]:
            cumsum_energy_in_job += run["mean_energy"]*run["num_events"]
        assert cumsum_energy_in_job <= expected_cumsum_energy_in_job
        assert cumsum_energy_in_job > 0.4*expected_cumsum_energy_in_job

    assert len(jobs) > 1000