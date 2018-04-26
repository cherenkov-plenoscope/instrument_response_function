"""
Usage: acp_trigger_irf [-s=PATH] -c=PATH -o=PATH -a=PATH -p=PATH -m=PATH

Options:
    -h --help                       Prints this help message.
    -s --scoop_hosts=PATH           Path to the scoop hosts file.
    -c --steering_card=PATH         Path to the ACP steering for the
                                    simulation of the trigger with a
                                    scatter-radius which depends on energy.
    -o --output_path=PATH           Path to write the output directroy.
    -a --acp_detector=PATH          Path to the light-field-geometry of the
                                    ACP.
    -p --mct_acp_config=PATH        Path to the mctracer ACP propagation
                                    configuration.
    -m --mct_acp_propagator=PATH    Path to the mctracer ACP propagation
                                    executable.
"""
import docopt
import subprocess
import pkg_resources


def main():
    try:
        arguments = docopt.docopt(__doc__)
        acp_irf_main = pkg_resources.resource_filename(
                'acp_instrument_response_function', 'trigger_study.py')
        command = [
            'python', '-m', 'scoop',
            acp_irf_main,
            '--steering_card', arguments['--steering_card'],
            '--output_path', arguments['--output_path'],
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
