#!/usr/bin/env python
# -*- coding: utf-8 -*-
'''
@author: Frank Brehm
@contact: frank.brehm@profitbricks.com
@organization: Profitbricks GmbH
@copyright: (c) 2010-2012 by Profitbricks GmbH
@license: GPL3
@summary: test script (and module) for unit tests on NagiosPluginArgparse
          and NagiosPluginConfig objects
'''

import unittest
import os
import sys
import logging

libdir = os.path.abspath(os.path.join(os.path.dirname(sys.argv[0]), '..'))
sys.path.insert(0, libdir)

import general
from general import ColoredFormatter, pp, get_arg_verbose, init_root_logger
from general import NeedConfig, NeedTmpConfig

import nagios
from nagios.plugin.config import NoConfigfileFound
from nagios.plugin.config import NagiosPluginConfig

from nagios.plugin.argparser import NagiosPluginArgparse

log = logging.getLogger(__name__)

#==============================================================================
class TestNagiosPluginArgparse(NeedConfig):

    #--------------------------------------------------------------------------
    def test_argparse_object(self):

        log.info("Testing NagiosPluginArgparse object.")
        na = NagiosPluginArgparse(
                usage = 'Usage: %(prog)s --hello',
                url = 'http://www.google.de',
                blurb = 'Senseless sample Nagios plugin.',
                extra = 'Bla blub',
        )
        log.debug("NagiosPluginArgparse object: %r", na)
        log.debug("NagiosPluginArgparse object: %s", str(na))

    #--------------------------------------------------------------------------
    def test_argparse_parse_help(self):

        log.info("Testing NagiosPluginArgparse generating help.")
        na = NagiosPluginArgparse(
                usage = 'Usage: %(prog)s --hello',
                url = 'http://www.google.de',
                blurb = 'Senseless sample Nagios plugin.',
                extra = 'Bla blub',
        )

        na.parse_args(['-h'])

#==============================================================================

if __name__ == '__main__':

    verbose = get_arg_verbose()
    init_root_logger(verbose)

    log.info("Starting tests ...")

    loader = unittest.TestLoader()
    suite = unittest.TestSuite()

    suite.addTests(loader.loadTestsFromName(
            'test_argparse_01.TestNagiosPluginArgparse.test_argparse_object'))
    suite.addTests(loader.loadTestsFromName(
            'test_argparse_01.TestNagiosPluginArgparse.test_argparse_parse_help'))

    runner = unittest.TextTestRunner(verbosity = verbose)

    result = runner.run(suite)

#==============================================================================

# vim: tabstop=4 expandtab shiftwidth=4 softtabstop=4 nu
