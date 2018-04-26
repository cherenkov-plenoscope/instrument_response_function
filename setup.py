from distutils.core import setup

setup(
    name='acp_instrument_response_function',
    version='0.0.3',
    description='Simulates the instrument response of the ' +
    'Atmospheric-Cherenkov-Plenoscope (ACP)',
    url='https://github.com/TheBigLebowSky/instrument_response_function.git',
    author='Sebastian Achim Mueller',
    author_email='sebmuell@phys.ethz.ch',
    license='GPL v3',
    packages=[
        'acp_instrument_response_function',
    ],
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
    zip_safe=False,
)
