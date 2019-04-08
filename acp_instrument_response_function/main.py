"""
Usage: acp_instrument_response_function [-s=SCOOP_HOSTS] -c=CORSIKA_CARD -o=OUTPUT -n=NUMBER_RUNS -a=ACP_DETECTOR -p=MCT_ACP_CONFIG -m=MCT_ACP_PROPAGATOR

Options:
    -h --help                                   Prints this help message.
    -s --scoop_hosts=SCOOP_HOSTS                Path to the scoop hosts file.
    -c --corsika_card=CORSIKA_CARD              Path to the corsika steering
                                                card template.
    -o --output_path=OUTPUT                     Path to output directroy.
    -n --number_of_runs=NUMBER_RUNS             Number of simulation runs to be
                                                executed. The number of events
                                                is NUMBER_RUNS times NSHOW in
                                                corsika steering template card.
    -a --acp_detector=ACP_DETECTOR              Path to Atmospheric Cherenkov
                                                Plenoscope (lixel statistics).
    -p --mct_acp_config=MCT_ACP_CONFIG          Path to the merlict ACP
                                                propagation configuration.
    -m --mct_acp_propagator=MCT_ACP_PROPAGATOR  Path to the merlict ACP
                                                propagation executable.
"""
import docopt
import subprocess
import pkg_resources


def main():
    try:
        arguments = docopt.docopt(__doc__)
        acp_irf_main = pkg_resources.resource_filename(
                'acp_instrument_response_function',
                'acp_instrument_response_function.py')
        command = [
            'python',
            '-m', 'scoop',
            acp_irf_main,
            '--corsika_card', arguments['--corsika_card'],
            '--output_path', arguments['--output_path'],
            '--number_of_runs', arguments['--number_of_runs'],
            '--acp_detector', arguments['--acp_detector'],
            '--mct_acp_config', arguments['--mct_acp_config'],
            '--mct_acp_propagator', arguments['--mct_acp_propagator']]
        if arguments['--scoop_hosts']:
            command.insert(3, '--hostfile')
            command.insert(4, arguments['--scoop_hosts'])
        return subprocess.call(command)
    except docopt.DocoptExit as e:
        print(e)

if __name__ == '__main__':
    main()
