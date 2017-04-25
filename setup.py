from distutils.core import setup
import os

def package_files(directory):
    paths = []
    for (path, directories, filenames) in os.walk(directory):
        for filename in filenames:
            paths.append(os.path.join('..', path, filename))
    return paths

setup_py_path = os.path.realpath(__file__)
setup_py_dir = os.path.dirname(setup_py_path)
extra_files = package_files(os.path.join(setup_py_dir,'acp_instrument_response_function','resources'))

setup(
    name='acp_instrument_response_function',
    version='0.0.2',
    description='Simulates the instrument response of the Atmospheric Cherenkov Plenoscope (ACP)',
    url='https://github.com/TheBigLebowSky/instrument_response_function.git',
    author='Sebastian Achim Mueller',
    author_email='sebmuell@phys.ethz.ch',
    license='MIT',
    packages=[
        'acp_instrument_response_function',
    ],
    package_data={'acp_instrument_response_function': extra_files},
    install_requires=[
        'docopt',
        'paramiko',
    ],
    entry_points={'console_scripts': [
        'acp_instrument_response_function = acp_instrument_response_function.main:main',
    ]},
    zip_safe=False,
)
