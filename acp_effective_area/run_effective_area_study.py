"""
Run Trigger study

Usage: run_trigger_study -i=STEERING_CARD_PATH -o=OUTPUT_PATH -c=CALIB_PATH -p=PROPCONFIG -n=NUMBER_RUNS -m=MCTPROPEXE

Options:
    -i --input_path=STEERING_CARD_PATH          Path to corsika steering card
                                                template.
    -o --output_path=OUTPUT_PATH                Directory to collect trigger 
                                                study results of rach run.
    -n --number_runs=NUMBER_RUNS
    -c --calib_plenoscope_path=CALIB_PATH 
    -p --propagation_config_path=PROPCONFIG_PATH
    -m --mctracer=MCTPROPEXE
"""
import docopt
import numpy as np
import plenopy as pl
import corsika_wrapper as cw

from scoop import shared
from scoop import futures
import scoop as sc
from subprocess import call
import tempfile
import os
import json
import copy
import shutil

def mctPlenoscopePropagation_path():
    return sc.shared.getConst('mctPlenoscopePropagation', timeout=5)


def mct_propagation_config_path():
    return sc.shared.getConst('mct_propagation_config', timeout=5)


def plenoscope_calibration_path():
    return sc.shared.getConst('plenoscope_calibration', timeout=5)


def stdout_path():
    return sc.shared.getConst('stdout_path', timeout=5)


def copy_file_to_std_out_path(text_file_path, steering):
    shutil.copyfile(
        text_file_path, 
        os.path.join(
            stdout_path(), 
            str(steering['run_number'])+'_'+os.path.basename(text_file_path)
        )
    )


def analyse_plenoscope_response(plenoscope_response_path, output_path):
    run = pl.Run(plenoscope_response_path)
    trigger_info = []
    for event in run:
        trigger_info.append(pl.trigger_study.export_trigger_information(event))
    pl.trigger_study.write_dict_to_file(trigger_info, output_path)


def make_plenoscope_response(corsika_run_path, plenoscope_response_path, prng_seed):
    stdout = open(plenoscope_response_path+'.stdout', 'w')
    stderr = open(plenoscope_response_path+'.stderr', 'w')
    call([
        mctPlenoscopePropagation_path(),
        '-l', plenoscope_calibration_path(),
        '-c', mct_propagation_config_path(),
        '-i', corsika_run_path,
        '-o', plenoscope_response_path,
        '-r', str(prng_seed)],
        stdout=stdout,
        stderr=stderr)
    stderr.close()
    stdout.close()            


def trigger_study_run(steering):
    with tempfile.TemporaryDirectory(prefix='acp_effective_area_') as temp_path:
        corsika_run_path = os.path.join(temp_path, 'corsika_run.evtio')
        plenoscope_response_path = os.path.join(temp_path, 'response.pleno')

        cw.corsika(
            steering_card=steering['steering_card'],
            output_path=corsika_run_path, 
            save_stdout=True)

        copy_file_to_std_out_path(corsika_run_path+'.stdout', steering)
        copy_file_to_std_out_path(corsika_run_path+'.stderr', steering)

        make_plenoscope_response(
            corsika_run_path=corsika_run_path,
            plenoscope_response_path=plenoscope_response_path,
            prng_seed=steering['mctracer_seed'])

        copy_file_to_std_out_path(plenoscope_response_path+'.stderr', steering)
        copy_file_to_std_out_path(plenoscope_response_path+'.stdout', steering)

        analyse_plenoscope_response(
            plenoscope_response_path=plenoscope_response_path,
            output_path=steering['output_path'])
    return True


if __name__ == '__main__':
    def make_corsika_steering_cards(steering_card_template, output_path, number_of_runs=1):
        steering = []
        for run_index in range(number_of_runs):
            run_number = run_index + 1
            
            card = copy.deepcopy(steering_card_template)
            assert len(card['RUNNR']) == 1
            card['RUNNR'][0] = str(run_number)
            assert len(card['SEED']) == 2
            card['SEED'][0] = str(run_number)+' 0 0'
            card['SEED'][1] = str(run_number+1)+' 0 0'

            steering.append({
                'steering_card': card,
                'output_path': os.path.join(output_path, str(int(run_number))+'.json'),
                'run_number': run_number,
                'mctracer_seed': run_number
            })
        return steering

    try:
        arguments = docopt.docopt(__doc__)
        sc.shared.setConst(mctPlenoscopePropagation=arguments['--mctracer'])
        sc.shared.setConst(plenoscope_calibration=arguments['--calib_plenoscope_path'])
        sc.shared.setConst(mct_propagation_config=arguments['--propagation_config_path'])
        output_path=arguments['--output_path']
        sc.shared.setConst(stdout_path=os.path.join(output_path, 'std'))
        
        if not os.path.exists(output_path):
            os.mkdir(output_path)

        if not os.path.exists(stdout_path()):
            os.mkdir(stdout_path())

        steering_card_template = cw.read_steering_card(
            arguments['--input_path'])

        steering = make_corsika_steering_cards(
            steering_card_template=steering_card_template,
            output_path=output_path,
            number_of_runs=int(arguments['--number_runs']))

        results = list(sc.futures.map(trigger_study_run, steering))
    except docopt.DocoptExit as e:
        print(e)

