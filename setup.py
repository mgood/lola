#!/usr/bin/python

import setuptools

setuptools.setup(
  name = 'lola',
  version = '0.1.2',
  license = 'BSD',
  description = 'Lola runs small Python scripts quickly',
  long_description = open('README.txt').read(),
  author = 'Matt Good',
  author_email = 'matt@matt-good.net',
  url = 'http://github.com/mgood/lola/',
  platforms = 'any',

  py_modules = ['lola'],

  zip_safe = True,
  verbose = False,
)
