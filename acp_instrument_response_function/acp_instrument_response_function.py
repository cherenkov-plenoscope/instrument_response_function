"""
Usage: acp_instrument_response_function -c=CORSIKA_CARD -o=OUTPUT -n=NUMBER_RUNS -a=ACP_DETECTOR -p=MCT_ACP_CONFIG -m=MCT_ACP_PROPAGATOR

Options:
    -h --help                               Prints this help message.
    -c --corsika_card=CORSIKA_CARD          Path to the corsika steering card
                                            template.
    -o --output_path=OUTPUT                 Path to write the output directroy.                                    
    -n --number_of_runs=NUMBER_RUNS         Number of simulation runs to be 
                                            executed. The total number of events
                                            is NUMBER_RUNS times NSHOW of the 
                                            corsika steering template card.
    -a --acp_detector=ACP_DETECTOR          Path to the Atmospheric Cherenkov
                                            Plenoscope (lixel statistics).
    -p --mct_acp_config=MCT_ACP_CONFIG      Path to the merlict ACP propagation
                                            configuration.
    -m --mct_acp_propagator=MCT_ACP_PROPAGATOR      Path to the merlict ACP 
                                                    propagation executable.
"""
import docopt
import scoop
import os
import copy
import shutil
import acp_instrument_response_function as irf
import corsika_wrapper as cw


if __name__ == '__main__':
    try:
        arguments = docopt.docopt(__doc__)
        
        # Set up configuration and directory environment
        cfg = {}
        cfg['path'] = irf.working_dir.directory_structure(
            arguments['--output_path'])

        os.mkdir(cfg['path']['main']['dir'])
        os.mkdir(cfg['path']['main']['input']['dir'])
        os.mkdir(cfg['path']['main']['stdout']['dir'])
        os.mkdir(cfg['path']['main']['intermediate_results_of_runs']['dir'])

        shutil.copy(
            arguments['--corsika_card'], 
            cfg['path']['main']['input']['corsika_steering_card_template'])
        shutil.copytree(
            arguments['--acp_detector'], 
            cfg['path']['main']['input']['acp_detector'])
        shutil.copy(
            arguments['--mct_acp_config'], 
            cfg['path']['main']['input']['mct_acp_config'])

        cfg['number_of_runs'] = int(arguments['--number_of_runs'])
        cfg['mct_acp_propagator'] = arguments['--mct_acp_propagator']

        cfg['corsika_steering_card_template'] = cw.read_steering_card(
            cfg['path']['main']['input']['corsika_steering_card_template'])

        irf.header.make_summary_header(cfg)

        # STAGE 1, SIMULATION
        simulation_instructions = irf.simulation.make_instructions(cfg)
        return_codes = list(scoop.futures.map(
            irf.simulation.simulate_acp_response, 
            simulation_instructions))

        # STAGE 2, CONDENSATION
        condensation_instructions = irf.intermediate.list_run_paths_in(
            cfg['path']['main']['intermediate_results_of_runs']['dir'])
        flat_runs = list(scoop.futures.map(
            irf.intermediate.make_flat_run, 
            condensation_instructions))

        acp_event_responses = irf.intermediate.concatenate_runs(flat_runs)

        # Save results
        irf.intermediate.write_json_dictionary(
            result=acp_event_responses, 
            path=cfg['path']['main']['acp_event_responses'])

    except docopt.DocoptExit as e:
        print(e)