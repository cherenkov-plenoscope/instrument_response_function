import numpy as np

def magic_one_collection_area():
    """
    Returns 2D array 
    column 0: Energy [GeV]
    column 1: Area [m^2]

    5.8 to 384 GeV

    Taken from:
    'Supporting Online Material for: 
    Observation of Pulsed gamma-Rays Above 25 GeV From the Crab Pulsar with
    MAGIC'
    The MAGIC Collaboration,
    www.sciencemag.org/cgi/content/full/1164718/DC1
    Figure 3, sum-trigger, red
    200 percent paper scale
    """
    raw_from_figure = np.array([
    # energy [mm]  area [mm]
        [  1.5,     7.5],
        [  4.0,    15.5],
        [  7.0,    22.5],
        [ 10.0,    25.0],
        [ 13.0,    28.5],
        [ 15.5,    34.5],
        [ 18.5,    37.0],
        [ 21.0,    42.0],
        [ 24.0,    44.5],
        [ 26.5,    47.5],
        [ 29.5,    51.5],
        [ 32.5,    54.0],
        [ 35.5,    59.0],
        [ 38.5,    62.0],
        [ 41.0,    64.0],
        [ 44.0,    65.0],
        [ 46.5,    67.0],
        [ 50.0,    68.0],
        [ 52.5,    69.0],
        [ 55.0,    69.0],
        [ 57.5,    70.0],
        [ 61.0,    71.5],
        [ 63.0,    72.0],
        [ 66.5,    72.0],
        [ 69.0,    72.5],
        [ 72.0,    73.0],
        [ 75.0,    73.0],
        [ 77.5,    73.5],
        [ 81.0,    74.0],
        [ 83.0,    74.0],
        [ 86.5,    73.5],
        [ 89.0,    75.0],
        [ 92.0,    74.0],
        [ 95.0,    74.0],
        [ 97.5,    74.0],
        [ 100.5,    74.0],
        [ 103.5,    75.0],
        [ 106.5,    74.5],
        [ 109.0,    75.0],
    ])
    
    raw_from_figure[:,0] = 10.0**(0.01695*raw_from_figure[:,0]+0.737275)
    raw_from_figure[:,1] = 10.0**(0.06*raw_from_figure[:,1]+0.47)
    return raw_from_figure
