#!/usr/bin/env python
# -*- coding: utf-8 -*-
'''
@author: Frank Brehm
@contact: frank.brehm@profitbricks.com
@organization: Profitbricks GmbH
@copyright: (c) 2010-2012 by Profitbricks GmbH
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
from general import ColoredFormatter, pp, get_arg_verbose, init_root_logger

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
class TestNagiosPerf(unittest.TestCase):

    #--------------------------------------------------------------------------
    def setUp(self):
        self.longMessage = True

    #--------------------------------------------------------------------------
    def test_performance_object_00(self):
        log.info("Testing init NagiosPerformance object lap 0.")
        warn_range = NagiosRange('30')
        crit_range = NagiosRange('60')
        th = NagiosThreshold(warning = warn_range, critical = crit_range)
        perf = NagiosPerformance(label = 'bla', value = 10, threshold = th,
                uom = 'MByte', min_data = 0, max_data = 1000)
        log.debug("NagiosPerformance object: %r", perf)
        self.assertEqual(perf.label, 'bla', 'Error testing perf.label')
        self.assertEqual(perf.value, 10, 'Error testing perf.value')
        self.assertEqual(perf.uom, 'MByte', 'Error testing perf.uom')
        self.assertEqual(perf.warning.start, 0, 'Error testing perf.warning.start')
        self.assertEqual(perf.warning.end, 30, 'Error testing perf.warning.end')
        self.assertEqual(perf.critical.start, 0, 'Error testing perf.critical.start')
        self.assertEqual(perf.critical.end, 60, 'Error testing perf.critical.end')
        self.assertEqual(perf.min_data, 0, 'Error testing perf.min_data')
        self.assertEqual(perf.max_data, 1000, 'Error testing perf.max_data')
        self.assertEqual(perf.status(), nagios.state.ok, 'Error testing perf.status()')

    #--------------------------------------------------------------------------
    def test_performance_object_01(self):
        log.info("Testing init NagiosPerformance object lap 1.")
        warn_range = NagiosRange('30')
        crit_range = NagiosRange('~:60')
        perf = NagiosPerformance(label = 'bla', value = 40, warning = warn_range,
                critical = crit_range, uom = 'MByte')
        log.debug("NagiosPerformance object: %r", perf)
        self.assertEqual(perf.label, 'bla', 'Error testing perf.label')
        self.assertEqual(perf.value, 40, 'Error testing perf.value')
        self.assertEqual(perf.uom, 'MByte', 'Error testing perf.uom')
        self.assertEqual(perf.warning.start, 0, 'Error testing perf.warning.start')
        self.assertEqual(perf.warning.end, 30, 'Error testing perf.warning.end')
        self.assertEqual(perf.critical.start, None, 'Error testing perf.critical.start')
        self.assertEqual(perf.critical.end, 60, 'Error testing perf.critical.end')
        self.assertEqual(perf.min_data, None, 'Error testing perf.min_data')
        self.assertEqual(perf.max_data, None, 'Error testing perf.max_data')
        self.assertEqual(perf.status(), nagios.state.warning, 'Error testing perf.status()')

    #--------------------------------------------------------------------------
    def test_performance_object_02(self):
        log.info("Testing init NagiosPerformance object lap 2.")
        perf = NagiosPerformance(label = 'bla', value = 80, warning = '~:30',
                critical = '~:60', uom = 'MByte')
        log.debug("NagiosPerformance object: %r", perf)
        self.assertEqual(perf.label, 'bla', 'Error testing perf.label')
        self.assertEqual(perf.value, 80, 'Error testing perf.value')
        self.assertEqual(perf.uom, 'MByte', 'Error testing perf.uom')
        self.assertEqual(perf.warning.start, None, 'Error testing perf.warning.start')
        self.assertEqual(perf.warning.end, 30, 'Error testing perf.warning.end')
        self.assertEqual(perf.critical.start, None, 'Error testing perf.critical.start')
        self.assertEqual(perf.critical.end, 60, 'Error testing perf.critical.end')
        self.assertEqual(perf.min_data, None, 'Error testing perf.min_data')
        self.assertEqual(perf.max_data, None, 'Error testing perf.max_data')
        self.assertEqual(perf.status(), nagios.state.critical, 'Error testing perf.status()')

    #--------------------------------------------------------------------------
    def test_performance_object_03(self):
        log.info("Testing init NagiosPerformance object lap 3.")
        perf = NagiosPerformance(label = 'bla', value = -10, uom = 'msec')
        log.debug("NagiosPerformance object: %r", perf)
        self.assertEqual(perf.label, 'bla', 'Error testing perf.label')
        self.assertEqual(perf.value, -10, 'Error testing perf.value')
        self.assertEqual(perf.uom, 'msec', 'Error testing perf.uom')
        self.assertFalse(perf.warning.is_set, 'Error testing perf.warning')
        self.assertFalse(perf.critical.is_set, 'Error testing perf.critical')
        self.assertEqual(perf.min_data, None, 'Error testing perf.min_data')
        self.assertEqual(perf.max_data, None, 'Error testing perf.max_data')
        self.assertEqual(perf.status(), nagios.state.ok, 'Error testing perf.status()')


#==============================================================================

if __name__ == '__main__':

    verbose = get_arg_verbose()
    init_root_logger(verbose)

    log.info("Starting tests ...")

    loader = unittest.TestLoader()
    suite = unittest.TestSuite()

    suite.addTests(loader.loadTestsFromName(
            'test_perf_01.TestNagiosPerf.test_performance_object_00'))
    suite.addTests(loader.loadTestsFromName(
            'test_perf_01.TestNagiosPerf.test_performance_object_01'))
    suite.addTests(loader.loadTestsFromName(
            'test_perf_01.TestNagiosPerf.test_performance_object_02'))
    suite.addTests(loader.loadTestsFromName(
            'test_perf_01.TestNagiosPerf.test_performance_object_03'))

    runner = unittest.TextTestRunner(verbosity = verbose)

    result = runner.run(suite)

#==============================================================================

# vim: tabstop=4 expandtab shiftwidth=4 softtabstop=4 nu
