"""
Usage: acp_effective_area -i=STEERING_CARD_PATH -o=OUTPUT_PATH -c=CALIB_PATH -p=PROPCONFIG -n=NUMBER_RUNS -m=MCTPROPEXE

Options:
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
import docopt
import plenopy as pl
import corsika_wrapper as cw

import scoop
import subprocess
import tempfile
import os
import copy
import shutil


def keep_stdout(text_path, cfg):
    shutil.copyfile(
        text_path, 
        os.path.join(
            cfg['output']['stdout'], 
            str(cfg['run']['number'])+'_'+os.path.basename(text_path)))


def analyse_plenoscope_response(acp_response_path, output_path):
    run = pl.Run(acp_response_path)
    event_info = []
    for event in run:
        event_info.append(pl.trigger_study.export_trigger_information(event))
    pl.trigger_study.write_dict_to_file(event_info, output_path)


def acp_response(corsika_run_path, output_path, cfg):
    with open(output_path+'.stdout', 'w') as out, open(output_path+'.stderr', 'w') as err:
        subprocess.call([
            cfg['mctracer_acp_propagation'],
            '-l', cfg['input']['acp_calibration'],
            '-c', cfg['input']['mctracer_acp_propagation_config'],
            '-i', corsika_run_path,
            '-o', output_path,
            '-r', str(cfg['run']['mctracer_seed'])],
            stdout=out,
            stderr=err)        


def simulate_acp_response(cfg):
    with tempfile.TemporaryDirectory(prefix='acp_effective_area_') as tmp_dir:
        corsika_run_path = os.path.join(tmp_dir, 'airshower.evtio')
        acp_response_path = os.path.join(tmp_dir, 'acp_response.acp')

        cw.corsika(
            steering_card=cfg['run']['corsika_steering_card'],
            output_path=corsika_run_path, 
            save_stdout=True)

        keep_stdout(corsika_run_path+'.stdout', cfg)
        keep_stdout(corsika_run_path+'.stderr', cfg)

        acp_response(
            corsika_run_path=corsika_run_path,
            output_path=acp_response_path,
            cfg=cfg)

        keep_stdout(acp_response_path+'.stderr', cfg)
        keep_stdout(acp_response_path+'.stdout', cfg)

        analyse_plenoscope_response(
            acp_response_path=acp_response_path,
            output_path=os.path.join(
                cfg['output']['directory'], 
                str(run_number)+'json.gz'))
    return True


def make_instructions_for_all_runs(cfg):

    steering_card_template = cw.read_steering_card(
        cfg['input']['corsika_steering_template'])

    instructions = []
    for run_index in range(cfg['number_of_runs']):
        run_number = run_index + 1
        
        # customize RUN number for specific run
        card = copy.deepcopy(steering_card_template)
        assert len(card['RUNNR']) == 1
        card['RUNNR'][0] = str(run_number)

        # customize seeds for specific run
        assert len(card['SEED']) == 2
        card['SEED'][0] = str(run_number)+' 0 0'
        card['SEED'][1] = str(run_number+1)+' 0 0'

        run_instructions = {
            'number': run_number,
            'corsika_steering_card': card,
            'mctracer_seed': run_number,
        }

        cfg_for_run = copy.deepcopy(cfg)
        cfg_for_run['run'] = run_instructions
        instructions.append(cfg_for_run)
    return instructions


if __name__ == '__main__':

    try:
        arguments = docopt.docopt(__doc__)
        
        cfg = {}
        cfg['number_of_runs'] = int(arguments['--number_of_runs'])
        cfg['mctracer_acp_propagation'] = arguments['--mctracer_acp_propagation']

        # Set up output directories
        cfg['output'] = {}
        cfg['output']['directory'] = arguments['--output_cfg']
        path['output']['stdout'] = os.path.join(cfg['output']['directory'], 'stdout')

        os.mkdir(cfg['output'])
        os.mkdir(cfg['stdoutput'])

        # Copy all the input files
        cfg['input'] = {}
        cfg['input']['directory'] = os.path.join(cfg['output'], 'input')
        cfg['input']['acp_calibration'] = os.path.join(cfg['input']['directory'], 'acp_calibration')
        cfg['input']['mctracer_acp_propagation_config'] = os.path.join(cfg['input']['directory'], 'mctracer_acp_propagation_config.xml')
        cfg['input']['corsika_steering_template'] = os.path.join(cfg['input']['directory'], 'corsika_steering_template.txt')

        os.mkdir(cfg['input']['directory'])
        shutil.copytree(arguments['--calib_plenoscope_path'], cfg['input']['acp_calibration'])
        shutil.copy(arguments['--mctracer_acp_propagation_config'], cfg['input']['mctracer_acp_propagation_config'])
        shutil.copy(arguments['--input_path'], cfg['input']['corsika_steering_template'])

        instructions = make_instructions_for_all_runs(cfg)

        results = list(scoop.futures.map(simulate_acp_response, instructions))
    except docopt.DocoptExit as e:
        print(e)