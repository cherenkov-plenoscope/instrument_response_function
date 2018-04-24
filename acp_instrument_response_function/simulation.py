import plenopy as pl
import corsika_wrapper as cw
import subprocess
import tempfile
import os
import copy
import shutil


def keep_stdout(text_path, out_name, cfg):
    """
    Copies a file from 'text_path' to the stdout directory in the 'main'
    directory.
    """
    shutil.copyfile(
        text_path,
        os.path.join(
            cfg['path']['main']['stdout']['dir'],
            str(cfg['current_run']['number'])+'_'+out_name))


def analyse_acp_response(acp_response_path, output_path):
    """
    Calls plenopy to perform a high level analysis on the ACP responses and
    writes a list of results for each event to the output_path.
    """
    run = pl.Run(acp_response_path)
    event_info = []
    for event in run:
        event_info.append(pl.trigger_study.export_trigger_information(event))
    pl.trigger_study.write_dict_to_file(event_info, output_path)


def acp_response(corsika_run_path, output_path, cfg, photon_origins=False):
    """
    Calls the mctracer ACP propagation and saves the stdout and stderr
    """
    op = output_path
    with open(op+'.stdout', 'w') as out, open(op+'.stderr', 'w') as err:
        call = [
            cfg['mct_acp_propagator'],
            '-l', cfg['path']['main']['input']['acp_detector'],
            '-c', cfg['path']['main']['input']['mct_acp_config'],
            '-i', corsika_run_path,
            '-o', output_path,
            '-r', str(cfg['current_run']['mctracer_seed'])]
        if photon_origins:
            call.append('--all_truth')
        mct_rc = subprocess.call(
            call,
            stdout=out,
            stderr=err)
    return mct_rc


def simulate_acp_response(cfg):
    """
    Simulates and analyses one run.
        - CORSIKA air shower simulation
        - mctracer ACP response simulation
        - plenopy ACP response high level analysis

    Only the high level results of plenopy are stored. The 'airshower.evtio'
    files and the ACP response files 'acp_response.acp' will be removed.
    """
    with tempfile.TemporaryDirectory(prefix='acp_irf_') as tmp_dir:
        corsika_run_path = os.path.join(tmp_dir, 'airshower.evtio')
        acp_response_path = os.path.join(tmp_dir, 'acp_response.acp')

        cor_rc = cw.corsika(
            steering_card=cfg['current_run']['corsika_steering_card'],
            output_path=corsika_run_path,
            save_stdout=True)

        keep_stdout(corsika_run_path+'.stdout', 'corsika.stdout', cfg)
        keep_stdout(corsika_run_path+'.stderr', 'corsika.stderr', cfg)

        mct_rc = acp_response(
            corsika_run_path=corsika_run_path,
            output_path=acp_response_path,
            cfg=cfg)

        keep_stdout(
            acp_response_path+'.stdout',
            'mctPlenoscopePropagation.stdout', cfg)
        keep_stdout(
            acp_response_path+'.stderr',
            'mctPlenoscopePropagation.stderr', cfg)

        analyse_acp_response(
            acp_response_path=acp_response_path,
            output_path=os.path.join(
                cfg['path']['main']['intermediate_results_of_runs']['dir'],
                'run_'+str(cfg['current_run']['number'])+'.json.gz'))
    return {
        'corsika_return_code': cor_rc,
        'mctracer_return_code': mct_rc}


def make_corsika_steering_card_for_current_run(
    steering_card_template,
    run_number
):
    """
    Creates a dedicated CORSIKA-steering-card for the current run based on the
    CORSIKA-steering-card-template and the current run-number.
    """
    # customize RUN-number for specific run
    card = copy.deepcopy(steering_card_template)
    assert len(card['RUNNR']) == 1
    card['RUNNR'][0] = str(run_number)

    # customize seeds for random-number-generator for specific run
    assert len(card['SEED']) == 4
    card['SEED'][0] = str(run_number) + ' 0 0'
    # 1 for the hadron-shower
    card['SEED'][1] = str(run_number+1)+' 0 0'
    # 2 for the EGS4-part
    card['SEED'][2] = str(run_number+2)+' 0 0'
    # 3 for the simulation of Cherenkov-photons (only for CERENKOV-option)
    card['SEED'][3] = str(run_number+3)+' 0 0'
    # 4 for the random-offset of Cherenkov-telescope-systems with respect of
    #   their nominal positions (only for IACT-option)
    # 5 for the HERWIG-routines in the NUPRIM-option
    # 6 for the PARALLEL-option
    # 7 for the CONEX-option
    return card


def make_instructions(cfg):
    """
    Returns a list of configurations for all runs to be processed.
    Each run's configuration is a copy of the main configuration appended with
    run instruction which conatain the run's specific CORSIKA steering card.
    """
    instructions = []
    for run_index in range(cfg['number_of_runs']):
        run_number = run_index + 1
        card = make_corsika_steering_card_for_current_run(
            cfg['corsika_steering_card_template'],
            run_number)
        run_instructions = {
            'number': run_number,
            'corsika_steering_card': card,
            'mctracer_seed': run_number}
        cfg_for_run = copy.deepcopy(cfg)
        cfg_for_run['current_run'] = run_instructions
        instructions.append(cfg_for_run)
    return instructions
