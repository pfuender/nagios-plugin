#!/usr/bin/env python
# -*- coding: utf-8 -*-
'''
@author: Frank Brehm
@contact: frank.brehm@profitbricks.com
@organization: Profitbricks GmbH
@copyright: (c) 2010-2012 by Profitbricks GmbH
@license: GPL3
@summary: test script (and module) for unit tests on NagiosThreshold objects
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

from nagios.plugin.config import NoConfigfileFound

from nagios.plugin.threshold import NagiosThreshold

#---------------------------------------------
# Some module variables

__version__ = '0.1.0'

log = logging.getLogger(__name__)

#==============================================================================
class TestNagiosThreshold(unittest.TestCase):

    #--------------------------------------------------------------------------
    def setUp(self):
        pass

    #--------------------------------------------------------------------------
    def test_threshold_object(self):

        log.info("Testing NagiosThreshold object with two Nones.")
        try:
            t = NagiosThreshold()
            log.debug("NagiosThreshold object: %r", t)
            if t.warning.is_set:
                self.fail("Warning threshold may not be set.")
            log.debug("Warning threshold is not set.")
            if t.critical.is_set:
                self.fail("Critical threshold may not be set.")
            log.debug("Critical threshold is not set.")
        except Exception, e:
            self.fail("Could not instatiate NagiosThreshold by a %s: %s" % (
                    e.__class__.__name__, str(e)))

    #--------------------------------------------------------------------------
    def test_threshold_empty(self):

        log.info("Testing NagiosThreshold object with two empty strings.")
        try:
            t = NagiosThreshold(warning = '', critical = '')
            log.debug("NagiosThreshold object: %r", t)
            if t.warning.is_set:
                self.fail("Warning threshold may not be set.")
            log.debug("Warning threshold is not set.")
            if t.critical.is_set:
                self.fail("Critical threshold may not be set.")
            log.debug("Critical threshold is not set.")
        except Exception, e:
            self.fail("Could not instatiate NagiosThreshold by a %s: %s" % (
                    e.__class__.__name__, str(e)))

    #--------------------------------------------------------------------------
    def test_threshold_critical_80(self):

        log.info("Testing NagiosThreshold object with critical == 80.")
        try:
            t = NagiosThreshold(warning = '', critical = '80')
            log.debug("NagiosThreshold object: %r", t)
            if t.warning.is_set:
                self.fail("Warning threshold may not be set.")
            log.debug("Warning threshold is not set.")
            if not t.critical.is_set:
                self.fail("Critical threshold must be set.")
            if not t.critical.start == 0:
                self.fail("Critical threshold range start must be zero.")
            if not t.critical.end == 80:
                self.fail("Critical threshold range end must be 80.")
        except Exception, e:
            self.fail("Could not instatiate NagiosThreshold by a %s: %s" % (
                    e.__class__.__name__, str(e)))

    #--------------------------------------------------------------------------
    def test_expected_01(self):

        expected_results = {
            -1: nagios.state.critical,
            4: nagios.state.ok,
            79.99999: nagios.state.ok,
            80: nagios.state.ok,
            80.00001: nagios.state.critical,
            102321: nagios.state.critical,
        }

        log.info("Testing NagiosThreshold object with critical == 80.")
        try:

            t = NagiosThreshold(warning = '', critical = '80')
            log.debug("NagiosThreshold object: %r", t)

            for value in sorted(expected_results.keys()):
                exp_result = expected_results[value]
                result = t.get_status(value)
                log.debug("Check %r, result is %r, expected is %r", value,
                        result, exp_result)
                if not exp_result == result:
                    self.fail("Unexpected result of get_status(), checked %r, "
                            "got %r, expected %r." % (value,
                            result, exp_result))

        except Exception, e:
            self.fail("Could not instatiate NagiosThreshold by a %s: %s" % (
                    e.__class__.__name__, str(e)))

    #--------------------------------------------------------------------------
    def test_expected_02(self):

        expected_results = {
            -1: nagios.state.warning,
            4: nagios.state.warning,
            4.99999: nagios.state.warning,
            5: nagios.state.ok,
            14.21: nagios.state.ok,
            33: nagios.state.ok,
            33.00001: nagios.state.warning,
            102321: nagios.state.warning,
        }

        log.info("Testing NagiosThreshold object with warning range 5:33.")
        try:

            t = NagiosThreshold(warning = "5:33", critical = '')
            log.debug("NagiosThreshold object: %r", t)

            for value in sorted(expected_results.keys()):
                exp_result = expected_results[value]
                result = t.get_status(value)
                log.debug("Check %r, result is %r, expected is %r", value,
                        result, exp_result)
                if not exp_result == result:
                    self.fail("Unexpected result of get_status(), checked %r, "
                            "got %r, expected %r." % (value,
                            result, exp_result))

        except Exception, e:
            self.fail("Could not instatiate NagiosThreshold by a %s: %s" % (
                    e.__class__.__name__, str(e)))

    #--------------------------------------------------------------------------
    def test_expected_03(self):

        expected_results = {
            -1: nagios.state.ok,
            4: nagios.state.ok,
            29.99999: nagios.state.ok,
            30: nagios.state.ok,
            30.00001: nagios.state.warning,
            59.99999: nagios.state.warning,
            60: nagios.state.warning,
            60.00001: nagios.state.critical,
            102321: nagios.state.critical,
        }

        log.info("Testing NagiosThreshold object with warning range ~:30 " +
                "and critical range ~:60.")
        try:

            t = NagiosThreshold(warning = "~:30", critical = '~:60')
            log.debug("NagiosThreshold object: %r", t)
            if not t.critical.is_set:
                self.fail("Critical threshold must be set.")
            if not t.warning.is_set:
                self.fail("Warning threshold must be set.")
            if t.critical.start is not None:
                self.fail("Critical range start must be None.")
            self.assertEqual(t.critical.end, 60, "Critical range end must be 60.")
            if t.warning.start is not None:
                self.fail("Warning range start must be None.")
            self.assertEqual(t.warning.end, 30, "Warning range end must be 30.")

            for value in sorted(expected_results.keys()):
                exp_result = expected_results[value]
                result = t.get_status(value)
                log.debug("Check %r, result is %r, expected is %r", value,
                        result, exp_result)
                if not exp_result == result:
                    self.fail("Unexpected result of get_status(), checked %r, "
                            "got %r, expected %r." % (value,
                            result, exp_result))

        except Exception, e:
            self.fail("Could not instatiate NagiosThreshold by a %s: %s" % (
                    e.__class__.__name__, str(e)))

#==============================================================================

if __name__ == '__main__':

    verbose = get_arg_verbose()
    init_root_logger(verbose)

    log.info("Starting tests ...")

    loader = unittest.TestLoader()
    suite = unittest.TestSuite()

    suite.addTests(loader.loadTestsFromName(
            'test_threshold.TestNagiosThreshold.test_threshold_object'))
    suite.addTests(loader.loadTestsFromName(
            'test_threshold.TestNagiosThreshold.test_threshold_empty'))
    suite.addTests(loader.loadTestsFromName(
            'test_threshold.TestNagiosThreshold.test_threshold_critical_80'))
    suite.addTests(loader.loadTestsFromName(
            'test_threshold.TestNagiosThreshold.test_expected_01'))
    suite.addTests(loader.loadTestsFromName(
            'test_threshold.TestNagiosThreshold.test_expected_02'))
    suite.addTests(loader.loadTestsFromName(
            'test_threshold.TestNagiosThreshold.test_expected_03'))

    runner = unittest.TextTestRunner(verbosity = verbose)

    result = runner.run(suite)

#==============================================================================

# vim: tabstop=4 expandtab shiftwidth=4 softtabstop=4 nu
