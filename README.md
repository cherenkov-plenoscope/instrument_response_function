Effective Area Simulation
-------------------------
for the Atmospheric Cherenkov Plenoscope (ACP)

A collection of tools to deploy and run an observation simulation of an ACP. This includes the full cycle of:
- Air shower simulations [CORSIKA](https://github.com/TheBigLebowSky/custom_corsika)
- ACP response simulation [mctracer](https://github.com/TheBigLebowSky/mctracer)
- ACP event analysis [plenopy](https://github.com/TheBigLebowSky/plenopy)

Runs with python [scoop](https://github.com/soravux/scoop) for massive parallel deployment.

## Install
```bash
pip install git+https://github.com/TheBigLebowSky/effective_area
```

## How to use
```bash
user@machine:~$ acp_effective_area -s=SCOOP_HOSTS -i=STEERING_CARD_PATH -o=OUTPUT_PATH -c=CALIB_PATH -p=PROPCONFIG -n=NUMBER_RUNS -m=MCTPROPEXE
```

## What does it do?
When started, an output directory is created ```OUTPUT_PATH``` and all input (corsika steering card, plenoscope scenery, and calibration) is copied into the output path first. Next, all the corsika steering cards are created using the template card in ```STEERING_CARD_PATH```. Only the run number and random seeds are adjusted for each run. Now scoop is used to deploy the simulation jobs onto your cluster ```SCOOP_HOSTS```. A single production job runs the CORSIKA [threadsafe](https://github.com/fact-project/corsika_wrapper) air shower simulation which writes a temporary file of Cherenkov photons. Only the copied input is used during the simulation. Next the [mctracer](https://github.com/TheBigLebowSky/mctracer) simulates the plensocope responses and also writes them to a temporary file. Next [plenopy](https://github.com/TheBigLebowSky/plenopy) runs an analysis on the temporary plenoscope response and extracts high level information which are stored permanently in the output path. After all simulation jobs are done, the intermediate analysis results by plenopy are condensed in one single ```result.json.gz``` in the output path.
