#!/usr/bin/env python

import os

#from distutils.core import setup
from setuptools import setup

#Read version
with open(os.path.normpath(os.path.join(__file__,'..','demakein','__init__.py')),'rU') as f:
    exec f.readline()

setup(name='demakein',
      version=VERSION,
      description='Design woodwind instruments and make them with a 3D printer or CNC mill.',
      
      packages = [
          'demakein', 
          'demakein.raphs_curves',
      ],
      
      entry_points = {
          'console_scripts' : [
              'demakein = demakein:main',
          ],
      },

      classifiers = [
          'License :: OSI Approved :: GNU General Public License v2 or later (GPLv2+)',
      ],
      
      install_requires = [ 
          'nesoni', 
          'cffi' ,
      ],
      
      url = 'http://www.logarithmic.net/pfh/design',
      author = 'Paul Harrison',
      author_email = 'pfh@logarithmic.net',
)
