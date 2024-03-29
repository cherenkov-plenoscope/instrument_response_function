import setuptools
import os

with open("README.md", "r") as f:
    long_description = f.read()

setuptools.setup(
    name='acp_instrument_response_function',
    version='0.0.3',
    description='Simulating the instrument-response of the Portal ' +
    'Cherenkov-plenoscope',
    long_description=long_description,
    long_description_content_type='text/markdown',
    url='https://github.com/cherenkov-plenoscope/' +
    'instrument_response_function.git',
    author='Sebastian Achim Mueller',
    author_email='sebastian-achim.mueller@mpi-hd.mpg.de',
    license='GPL v3',
    packages=[
        'acp_instrument_response_function',
    ],
    package_data={'acp_instrument_response_function': [
        os.path.join('tests', 'resources', '*')]},
    install_requires=[
        'docopt',
        'scoop',
    ],
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: GNU General Public License v3 (GPLv3)",
        "Operating System :: OS Independent",
        "Natural Language :: English",
        "Intended Audience :: Science/Research",
        "Topic :: Scientific/Engineering :: Physics",
        "Topic :: Scientific/Engineering :: Astronomy",
    ],
)
