ARCHIVED
========
This repository is out of service.
This estimate of the instrument-response-function was not able to simulate air-showers with particle-energies below the geomagnetic-cutoff. The whole population-algorithm of the instrument-response was changed to account for this and lifes on in ```starter_kit/plenoirf```.

Thanks to Dominik Neise and Max L. Ahnen for their contribution in the early days of the cherenkov-plenoscope.

Instrument Response Function (IRF)
----------------------------------

[![License: GPL v3](https://img.shields.io/badge/License-GPL%20v3-blue.svg)](https://www.gnu.org/licenses/gpl-3.0)

For the Atmospheric Cherenkov Plenoscope (ACP)

- Air shower simulations [CORSIKA](https://github.com/cherenkov-plenoscope/corsika_install)
- ACP response simulation [merlict](https://github.com/cherenkov-plenoscope/merlict_development_kit)
- ACP event analysis [plenopy](https://github.com/cherenkov-plenoscope/plenopy)

Runs with python [scoop](https://github.com/soravux/scoop) for massive parallel deployment over many machines, but also runs on a single machine.

## Install
```bash
pip install git+https://github.com/cherenkov-plenoscope/instrument_response_function
```

## How to run a simulation
```bash
user@machine:~$ acp_instrument_response_function [-s=SCOOP_HOSTS] -c=CORSIKA_CARD -o=OUTPUT -n=NUMBER_RUNS -a=ACP_DETECTOR -p=MCT_CONFIG -m=MCT_PROPAGATOR
```

## How to explore the results
```python
In [1]: import acp_instrument_response_function as acp_irf

In [2]: acp_irf.analysis.export_effective_area(
	input_path='/home/sebastian/Desktop/electron_2016Dec10_01h19m/', 
	detector_responses_key='raw_lixel_sum', 
	detector_response_threshold=100, 
	output_path='/home/sebastian/Desktop/Aeff.csv', 
	bins=31)
```

![img](example/example_effective_area_50mACP_electron_above_100pe.png)

## What does it do?
When started, an output directory is created ```OUTPUT_PATH``` and all input (corsika steering card, plenoscope scenery, and calibration) is copied into the output path first. Only the copied input is used during the simulation. Next, all the corsika steering cards are created using the template card in ```CORSIKA_CARD```. Only the run number and random seeds are adjusted for each run. Now scoop is used to deploy the simulation jobs onto your cluster ```SCOOP_HOSTS```. A single production job runs the CORSIKA [threadsafe](https://github.com/fact-project/merlict_development_kit) air shower simulation which writes a temporary file of Cherenkov photons. Next the [merlict](https://github.com/cherenkov-plenoscope/merlict_development_kit) simulates the plensocope responses and also writes them to a temporary file. Next [plenopy](https://github.com/cherenkov-plenoscope/plenopy) runs an analysis on the temporary plenoscope response and extracts high level information which are stored permanently in the output path. After all simulation jobs are done, the intermediate analysis results by plenopy are condensed in one single ```acp_event_responses.json.gz``` in the output path.
