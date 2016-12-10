from distutils.core import setup

setup(
    name='acp_effective_area',
    version='0.0.1',
    description='Simulate the instrument response of an Atmospheric Cherenkov Plenoscope (ACP)',
    url='https://github.com/thebiglebowsky/effective_area.git',
    author='Sebastian Achim Mueller',
    author_email='sebmuell@phys.ethz.ch',
    license='MIT',
    packages=[
        'acp_effective_area',
    ],
    package_data={'acp_effective_area': ['resources/*']},
    install_requires=[
        'docopt',
    ],
    entry_points={'console_scripts': [
        'acp_effective_area = acp_effective_area.main:main',
    ]},
    zip_safe=False,
)
