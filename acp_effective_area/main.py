"""
Usage: acp_effective_area [-s=SCOOP_HOSTS] -c=CORSIKA_CARD -o=OUTPUT -n=NUMBER_RUNS -a=ACP_DETECTOR -p=MCT_CONFIG -m=MCT_PROPAGATOR

Options:
    -h --help                               Prints this help message.
    -s --scoop_hosts=SCOOP_HOSTS            Path to the scoop hosts text file.
    -c --corsika_card=CORSIKA_CARD          Path to the corsika steering card
                                            template.
    -o --output_path=OUTPUT                 Path to write the output directroy.                                    
    -n --number_of_runs=NUMBER_RUNS         Number of simulation runs to be 
                                            executed. The total number of events
                                            is NUMBER_RUNS times NSHOW of the 
                                            corsika steering template card.
    -a --acp_detector=ACP_DETECTOR          Path to the ACP's light field
                                            calibration output folder.
    -p --mct_acp_config=MCT_CONFIG          Path to the mctracer ACP propagation
                                            configuration.
    -m --mct_acp_propagator=MCT_PROPAGATOR  Path to the mctracer ACP propagation
                                            executable.
"""
import docopt
import subprocess
import pkg_resources


def main():
    try:
        arguments = docopt.docopt(__doc__)
    
        acp_effective_area_main = pkg_resources.resource_filename(
                'acp_effective_area', 
                'acp_effective_area.py')

        command = [
            'python',
            '-m', 'scoop',
            acp_effective_area_main,
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