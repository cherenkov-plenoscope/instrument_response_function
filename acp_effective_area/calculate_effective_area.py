import numpy as np
import os
import json
import copy
import shutil
import glob
import matplotlib.pyplot as plt


def get_effective_area_histogram(threshold, trigger_list, bins=15):
	E_min_log10 = np.floor(np.log10(trigger_list.primary_particle_energy.min()))
	E_max_log10 = np.ceil(np.log10(trigger_list.primary_particle_energy.max())) 		
	
	bin_edges = np.logspace(E_min_log10, E_max_log10, bins+1)

	above_threshold = trigger_list.raw_lixel_sum > threshold
	survived_energies = trigger_list.primary_particle_energy[above_threshold]	
	thrown_energies = trigger_list.primary_particle_energy

	survived_histogram = np.histogram(
		survived_energies, 
		bins=bin_edges, 	
		weights=trigger_list.scatter_area[above_threshold])[0]
	
	thrown_histogram = np.histogram(
		thrown_energies, 
		bins=bin_edges)[0]

	effective_area_histogram = survived_histogram/thrown_histogram
	return [effective_area_histogram, bin_edges]	


def plot_effective_area(effective_area_histogram, bin_edges):
	plt.figure()
	effective_area_histogram_steps = np.hstack(
		(	effective_area_histogram[0], 
			effective_area_histogram))
	plt.step(bin_edges, effective_area_histogram_steps)	
	plt.xlabel('Energy/GeV')
	plt.ylabel('Area/m^2')
	plt.loglog()