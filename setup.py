from distutils.core import setup

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
    package_data={'acp_instrument_response_function': ['resources/*']},
    install_requires=[
        'docopt',
        'paramiko',
    ],
    entry_points={'console_scripts': [
        'acp_instrument_response_function = acp_instrument_response_function.main:main',
    ]},
    zip_safe=False,
)
