"""
Usage: acp_effective_area [-s=SCOOP_HOSTS] -i=STEERING_CARD_PATH -o=OUTPUT_PATH -c=CALIB_PATH -p=PROPCONFIG -n=NUMBER_RUNS -m=MCTPROPEXE

Options:
    -s --scoop_hosts=SCOOP_HOSTS                Path the the scoop hostfile
    -i --input_path=STEERING_CARD_PATH          Path to corsika steering card
                                                template.
    -o --output_path=OUTPUT_PATH                Directory to collect simulation
                                                results.
    -n --number_of_runs=NUMBER_RUNS
    -c --acp_calibration=CALIB_PATH 
    -p --mctracer_acp_propagation_config=PROPCONFIG_PATH
    -m --mctracer_acp_propagation=MCTPROPEXE
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
            '--input_path', arguments['--input_path'],
            '--output_path', arguments['--output_path'],
            '--number_of_runs', arguments['--number_of_runs'],
            '--acp_calibration', arguments['--acp_calibration'],
            '--mctracer_acp_propagation_config', arguments['--mctracer_acp_propagation_config'],
            '--mctracer_acp_propagation', arguments['--mctracer_acp_propagation']] 

        if arguments['--scoop_hosts']:
            command.insert(3, '--hostfile')
            command.insert(4, arguments['--scoop_hosts'])

        return subprocess.call(command)

    except docopt.DocoptExit as e:
        print(e)


if __name__ == '__main__':
    main()