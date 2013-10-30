#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import sys
import glob
import pprint
import inspect

from distutils.core import setup, Command

# own modules:
cur_dir = os.getcwd()
if sys.argv[0] != '' and sys.argv[0] != '-c':
    cur_dir = os.path.dirname(sys.argv[0])

libdir = os.path.join(cur_dir, 'nagios')
if os.path.exists(libdir) and os.path.isdir(libdir):
    sys.path.insert(0, os.path.abspath(cur_dir))
del libdir
del cur_dir

import nagios

packet_version = nagios.__version__

pp = pprint.PrettyPrinter(indent=4)

def read(fname):
    return open(os.path.join(os.path.dirname(__file__), fname)).read()

plugins = glob.glob(os.path.join('bin', '*'))
os_module_file = inspect.getfile(os)
global_lib_dir = os_module_file[:os_module_file.index('/python')]
plugin_dir = os.path.join(global_lib_dir, 'nagios', 'plugins', 'pb')

datafiles = []
datafiles.append((plugin_dir, plugins))
#print pp.pformat(datafiles)

setup(
    name = 'nagios',
    version = packet_version,
    description = 'Base module for Nagios check plugins written in Python.',
    long_description = read('README.txt'),
    author = 'Frank Brehm',
    author_email = 'frank.brehm@profitbricks.com',
    url = 'ssh://git.profitbricks.localdomain/srv/git/python/nagios-plugin.git',
    license = 'LGPLv3+',
    platforms = ['posix'],
    packages = [
        'nagios',
        'nagios.plugin',
        'nagios.plugins',
    ],
    classifiers = [
        'Development Status :: 2 - Pre-Alpha',
        'Environment :: Console',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: GNU Lesser General Public License v3 or later (LGPLv3+)',
        'Natural Language :: English',
        'Operating System :: POSIX :: Linux',
        'Programming Language :: Python :: 2.6',
        'Programming Language :: Python :: 2.7',
        'Topic :: Software Development :: Libraries :: Python Modules',
    ],
    data_files = datafiles,
    requires = [
        #'pb_base (>= 0.3.10)',
    ]
)




#========================================================================

# vim: fileencoding=utf-8 filetype=python ts=4 expandtab
