"""
Usage: trigger_study.py [-c=PATH] [-o=PATH] [-n=NUMBER] [-a=PATH] [-p=PATH] [-m=PATH] [-t=NUMBER]

Options:
    -h --help                           Prints this help message.
    -c --steering_card=PATH             [default: resources/acp/71m/gamma_steering.json]
                                            Path to the ACP steering for the
                                            simulation of the trigger with a
                                            scatter-radius which depends on
                                            energy.
    -o --output_path=PATH               [default: examples/trigger_gamma]
                                            Path to write the output directroy.
    -a --acp_detector=PATH              [default: run/light_field_geometry]
                                            Path to the light-field-geometry of
                                            the ACP.
    -p --mct_acp_config=PATH            [default: resources/acp/mct_propagation_config.xml]
                                            Path to the mctracer ACP propagation configuration.
    -m --mct_acp_propagator=PATH        [default: build/mctracer/mctPlenoscopePropagation]
                                            Path to the mctracer ACP propagation executable.
"""
import docopt
import scoop
import numpy as np
import os
from os.path import join
import shutil as sh
import tempfile
import corsika_wrapper as cw
import plenopy as pl
import acp_instrument_response_function as acpirf
import random


if __name__ == '__main__':
    try:
        arguments = docopt.docopt(__doc__)

        jobs = acpirf.trigger_simulation.make_output_directory_and_jobs(
            steering_card_path=arguments['--steering_card'],
            output_path=arguments['--output_path'],
            acp_detector_path=arguments['--acp_detector'],
            mct_acp_config_path=arguments['--mct_acp_config'],
            mct_acp_propagator_path=arguments['--mct_acp_propagator'])

        random.shuffle(jobs)
        return_codes = list(scoop.futures.map(
            acpirf.trigger_simulation.run_job, jobs))

    except docopt.DocoptExit as e:
        print(e)
