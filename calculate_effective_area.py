import numpy as np
import os
import json
import copy
import shutil
import glob
import matplotlib.pyplot as plt

class EffectiveArea(object):
    def __init__(self, energies, scatter_areas, above_threshold_mask, energy_bin_edges):
        self.energy_bin_edges = energy_bin_edges
        self.scatter_areas = scatter_areas
        self.energies = energies
        self.number_thrown = np.histogram(energies, bins=energy_bin_edges)[0]
        self.number_above_theshold = np.histogram(energies[above_threshold_mask], bins=energy_bin_edges)[0]

    def plot(self):
        scatter_area = self.scatter_areas[0]
        plt.step(
            self.energy_bin_edges[:-1], 
            scatter_area*self.number_above_theshold/self.number_thrown)
        plt.xlabel('energy/GeV')
        plt.ylabel('area/m^2')
        plt.show()

class TriggerList(object):
    def __init__(self, input_path):

        self.events = self._load_events_from_json(input_path)
        self._flatten_event_dicts_to_arrays()

    def _load_events_from_json(self, input_path):
        run_paths = glob.glob(os.path.join(input_path, '*.json'))
        events = []
        for run_path in run_paths:
            f = open(run_path, 'r')
            run = json.load(f)
            f.close()
            for evt in run:
                events.append(evt)
            print(run_path)
        return events

    def _flatten_event_dicts_to_arrays(self):
        run_number = []
        event_number = []
        primary_particle_id = []
        primary_particle_energy = []
        scatter_radius = []
        lixel_sum = []

        for event in self.events:
            run_number.append(event['id']['run'])
            event_number.append(event['id']['event'])
            primary_particle_energy.append(event['simulation_truth']['energy'])
            primary_particle_id.append(event['simulation_truth']['primary_particle']['id'])
            scatter_radius.append(event['simulation_truth']['scatter_radius'])
            lixel_sum.append(event['acp']['response']['lixel']['sum'])

        self.run_number = np.array(run_number)
        self.event_number = np.array(event_number)
        self.primary_particle_id = np.array(primary_particle_id)
        self.primary_particle_energy = np.array(primary_particle_energy)
        self.scatter_radius = np.array(scatter_radius)
        self.lixel_sum = np.array(lixel_sum)
        self.scatter_area = np.pi*self.scatter_radius**2.0