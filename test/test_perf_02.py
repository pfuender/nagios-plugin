#!/usr/bin/env python
# -*- coding: utf-8 -*-
'''
@author: Frank Brehm
@contact: frank.brehm@profitbricks.com
@organization: Profitbricks GmbH
@copyright: © 2010 - 2015 by Profitbricks GmbH
@license: GPL3
@summary: test script (and module) for unit tests on NagiosPerfomance objects
'''

import unittest
import os
import sys
import logging

libdir = os.path.abspath(os.path.join(os.path.dirname(sys.argv[0]), '..'))
sys.path.insert(0, libdir)

import general
from general import ColoredFormatter, get_arg_verbose, init_root_logger

import nagios

from nagios.plugin.range import NagiosRangeError
from nagios.plugin.range import InvalidRangeError
from nagios.plugin.range import InvalidRangeValueError
from nagios.plugin.range import NagiosRange

from nagios.plugin.config import NoConfigfileFound

from nagios.plugin.threshold import NagiosThreshold

from nagios.plugin.performance import NagiosPerformanceError
from nagios.plugin.performance import NagiosPerformance

#---------------------------------------------
# Some module variables

__version__ = '0.1.0'

log = logging.getLogger(__name__)

#==============================================================================
class TestNagiosPerf1(unittest.TestCase):

    #--------------------------------------------------------------------------
    def setUp(self):
        self.longMessage = True

    #--------------------------------------------------------------------------
    def test_parse_perfoutput_01(self):
        log.info("Testingparsing performance data output output lap 1.")

        perfoutput = "/=382MB;15264;15269;0;32768 /var=218MB;9443;9448"

        plist = NagiosPerformance.parse_perfstring(perfoutput)
        log.debug("perfoutput: %r", plist)

#==============================================================================

if __name__ == '__main__':

    verbose = get_arg_verbose()
    init_root_logger(verbose)

    log.info("Starting tests ...")

    loader = unittest.TestLoader()
    suite = unittest.TestSuite()

    suite.addTests(loader.loadTestsFromName(
            'test_perf_02.TestNagiosPerf1.test_parse_perfoutput_01'))

    runner = unittest.TextTestRunner(verbosity = verbose)

    result = runner.run(suite)

#==============================================================================

# vim: tabstop=4 expandtab shiftwidth=4 softtabstop=4
