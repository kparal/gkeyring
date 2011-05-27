#!/usr/bin/env python

from setuptools import setup
import gkeyring

setup(name='gkeyring',
      version=gkeyring._version,
      py_modules=['gkeyring'],
      entry_points = {
        'console_scripts': ['gkeyring = gkeyring:main'],
      },
      author='Kamil Paral',
      author_email='kamil.paral@gmail.com',
      description='Tool for shell access to GNOME keyring',
      long_description='A small Python tool for shell access to GNOME keyring. It provides simple querying for and creating of keyring items.',
      keywords='gnome keyring access commandline',
      license='GNU Affero GPL v3',
      url='https://code.launchpad.net/gkeyring',
      download_url='https://launchpad.net/gkeyring/+download',
      classifiers=[
        'Development Status :: 5 - Production/Stable',
        'Environment :: Console',
        'Environment :: X11 Applications :: Gnome',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: GNU Affero General Public License v3',
        'Natural Language :: English',
        'Operating System :: POSIX',
        'Operating System :: POSIX :: Linux',
        'Programming Language :: Python :: 2',
        'Topic :: Desktop Environment :: Gnome',
        'Topic :: Utilities'
      ])
