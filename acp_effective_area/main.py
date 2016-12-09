"""
Usage: acp_effective_area -s=SCOOP_HOSTS -i=STEERING_CARD_PATH -o=OUTPUT_PATH -c=CALIB_PATH -p=PROPCONFIG -n=NUMBER_RUNS -m=MCTPROPEXE

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

Run the ACP effective area simulation.

How it is done
--------------
First, the output directory is created (output_path).
Second, all inputs are copied into the output directory.
Third and finally, for each run (number_of_runs) the acp response is simulated:

For each run
------------
  - CORSIKA simulates air showers and outputs Cherenkov photons for each shower.
  - mctracer reads in the Cherenkov photons and simulates the corresponding 
    ACP responses.
  - plenopy reads in the ACP responses and outputs a high level analysis 
    relevant trigger and air shower reconstruction with the ACP.
  - The high level plenopy output is stored permanently, everything else it 
    removed when the run is over.
"""


def main():
    try:
        arguments = docopt.docopt(__doc__)
    
        acp_effective_area_main = pkg_resources.resource_filename(
                'acp_effective_area', 
                'acp_effective_area.py')

        return subprocess.call([
            'python',
            '-m', 'scoop',
            '--hostfile', arguments['--scoop_hosts'],
            acp_effective_area_main,
            '--input_path', arguments['--input_path'],
            '--output_path', arguments['--output_path'],
            '--number_of_runs', arguments['--number_of_runs'],
            '--acp_calibration', arguments['--acp_calibration'],
            '--mctracer_acp_propagation_config', arguments['--mctracer_acp_propagation_config'],
            '--mctracer_acp_propagation', arguments['--mctracer_acp_propagation']
        ])

    except docopt.DocoptExit as e:
        print(e)


if __name__ == '__main__':
    main()