#!/usr/bin/env python

import os

#from distutils.core import setup
from setuptools import setup

#Read version
with open(os.path.normpath(os.path.join(__file__,'..','demakein','__init__.py')),'rU') as f:
    exec(f.readline())

long_description = """

Demakein is a set of Python tools for designing and making woodwind 
instruments.

This generally consists of two stages:

- The "design" stage is a numerical optimization that chooses the bore shape and the finger hole placement, size, and depth necessary for the instrument to produce the correct notes for a given set of fingerings.

- The "make" stage takes a design and turns it into a 3D object, then then cuts the object into pieces that can be CNC-milled or 3D-printed.

Demakein can either be used via the command "demakein" or as a library in Python. Demakein has been designed to be extensible, and I hope you will find it relatively easy to write code to create your own novel instruments. You can either create subclasses of existing classes in order to tweak a few parameters, or create wholly new classes using existing examples as a template.

See the README for detailed install instructions:

https://github.com/pfh/demakein

Home page:

http://www.logarithmic.net/pfh/design

Author:

Paul Harrison, pfh@logarithmic.net or paul.francis.harrison@gmail.com

"""

setup(name='demakein',
      version=VERSION,
      description='Design woodwind instruments and make them with a 3D printer or CNC mill.',
      long_description=long_description,
      
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
          'cffi' ,
      ],
      
      url = 'https://www.logarithmic.net/pfh/design',
      author = 'Paul Harrison',
      author_email = 'paul.francis.harrison@gmail.com',
)
