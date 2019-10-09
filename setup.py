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
    entry_points={'console_scripts': [
        'acp_instrument_response_function = ' +
        'acp_instrument_response_function.main:main',
        'acp_trigger_irf = ' +
        'acp_instrument_response_function.trigger_main:main',
    ]},
)
