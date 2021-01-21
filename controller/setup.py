from distutils.core import setup
import os
from glob import glob
from setuptools import setup, find_packages

setup(
    name='vplotter-controller',
    version='1.0',
    packages=find_packages(),
    url='',
    download_url='ssh://a-server:/srv/git/attolock.git',
    license='',
    author='Tobias Witting',
    author_email='tobias.witting@posteo.de',
    description='PyQt GUI for controlling V-Plotter',
    entry_points={'console_scripts':['vplotter-controller=vplottercontroller:main']}
)
