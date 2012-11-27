#!/usr/bin/env python
# -*- coding: utf-8 -*-
'''
@author: Frank Brehm
@contact: frank.brehm@profitbricks.com
@organization: Profitbricks GmbH
@copyright: (c) 2010-2012 by Profitbricks GmbH
@license: GPL3
@summary: test script (and module) for unit tests on NagiosRange objects
'''

import unittest
import os
import sys
import logging

libdir = os.path.abspath(os.path.join(os.path.dirname(sys.argv[0]), '..'))
sys.path.insert(0, libdir)

from pb_logging.colored import ColoredFormatter
from pb_base.common import pp

import nagios
from nagios.plugin.range import NagiosRangeError
from nagios.plugin.range import InvalidRangeError
from nagios.plugin.range import InvalidRangeValueError
from nagios.plugin.range import NagiosRange

log = logging.getLogger(__name__)

#==============================================================================
class TestNagiosRange(unittest.TestCase):

    #--------------------------------------------------------------------------
    def setUp(self):
        pass

    #--------------------------------------------------------------------------
    def test_empty_object(self):

        try:
            nrange = NagiosRange()
            log.debug("NagiosRange object: %r", nrange)
        except Exception, e:
            self.fail("Could not instatiate NagiosRange by a %s: %s" % (
                    e.__class__.__name__, str(e)))

    #--------------------------------------------------------------------------
    def test_parse_normal(self):

        try:
            nrange = NagiosRange('1:10')
            log.debug("NagiosRange object: %r", nrange)
        except Exception, e:
            self.fail("Could not instatiate NagiosRange by a %s: %s" % (
                    e.__class__.__name__, str(e)))

    #--------------------------------------------------------------------------
    def test_parse_float(self):

        try:
            nrange = NagiosRange('1.1:10.999')
            log.debug("NagiosRange object: %r", nrange)
        except Exception, e:
            self.fail("Could not instatiate NagiosRange by a %s: %s" % (
                    e.__class__.__name__, str(e)))

    #--------------------------------------------------------------------------
    def test_invalid(self):

        values = (':', '1:~', 'foo', '1-10', '10:~', '1-10:2.4', '1,10', '5:3',
                    '~:')
        for value in values:
            try:
                nrange = NagiosRange(value)
            except InvalidRangeError, e:
                log.debug("Found incorrect range %r.", value)
            else:
                self.fail("Range %r should be incorrect, but lead to %r.",
                        value, nrange)

    #--------------------------------------------------------------------------
    def test_limits(self):

        try:
            nrange = NagiosRange('6')
            log.debug("NagiosRange object: %r", nrange)
            if not (nrange.start is not None and nrange.start == 0):
                self.fail("Start limit should be zero.")
            if not (nrange.end is not None and nrange.end == 6):
                self.fail("End limit should be 6.")
            nrange_str = str(nrange)
            log.debug("Stringified NagiosRange object: %r", nrange_str)
            if nrange_str != '6':
                self.fail("Stringified NagiosRange should be '6'.")
        except Exception, e:
            self.fail("Could not instatiate NagiosRange by a %s: %s" % (
                    e.__class__.__name__, str(e)))

    #--------------------------------------------------------------------------
    def test_limits_infinity(self):

        try:
            nrange = NagiosRange('~:6')
            log.debug("NagiosRange object: %r", nrange)
            if nrange.start is not None:
                self.fail("Start limit should be None.")
            if not (nrange.end is not None and nrange.end == 6):
                self.fail("End limit should be 6.")
            nrange_str = str(nrange)
            log.debug("Stringified NagiosRange object: %r", nrange_str)
            if nrange_str != '~:6':
                self.fail("Stringified NagiosRange should be '~:6'.")
        except Exception, e:
            self.fail("Could not instatiate NagiosRange by a %s: %s" % (
                    e.__class__.__name__, str(e)))

    #--------------------------------------------------------------------------
    def test_check_simple(self):

        expected_results = {
                -1: False,
                0: True,
                4: True,
                6: True,
                6.1: False,
                79.99999: False,
        }

        try:
            nrange = NagiosRange('6')
            log.debug("NagiosRange object: %r", nrange)

            for value in sorted(expected_results.keys()):
                exp_result = expected_results[value]
                result = nrange.check(value)
                log.debug("Check %r, result is %r, expected is %r", value,
                        result, exp_result)
                if not exp_result == result:
                    self.fail("Unexpected result of check(), checked %r "
                            "against '0:6', got %r, expected %r." % (value,
                            result, exp_result))

        except Exception, e:
            self.fail("Could not instatiate NagiosRange by a %s: %s" % (
                    e.__class__.__name__, str(e)))


#==============================================================================

if __name__ == '__main__':

    import argparse

    arg_parser = argparse.ArgumentParser()
    arg_parser.add_argument("-v", "--verbose", action = "count",
            dest = 'verbose', help = 'Increase the verbosity level')
    args = arg_parser.parse_args()

    root_log = logging.getLogger()
    root_log.setLevel(logging.INFO)
    if args.verbose:
         root_log.setLevel(logging.DEBUG)

    appname = os.path.basename(sys.argv[0])
    format_str = appname + ': '
    if args.verbose:
        if args.verbose > 1:
            format_str += '%(name)s(%(lineno)d) %(funcName)s() '
        else:
            format_str += '%(name)s '
    format_str += '%(levelname)s - %(message)s'
    formatter = None
    formatter = ColoredFormatter(format_str)

    # create log handler for console output
    lh_console = logging.StreamHandler(sys.stderr)
    if args.verbose:
        lh_console.setLevel(logging.DEBUG)
    else:
        lh_console.setLevel(logging.INFO)
    lh_console.setFormatter(formatter)

    root_log.addHandler(lh_console)

    log.info("Starting tests ...")

    loader = unittest.TestLoader()
    suite = unittest.TestSuite()

    suite.addTests(loader.loadTestsFromName(
            'test_range.TestNagiosRange.test_empty_object'))
    suite.addTests(loader.loadTestsFromName(
            'test_range.TestNagiosRange.test_parse_normal'))
    suite.addTests(loader.loadTestsFromName(
            'test_range.TestNagiosRange.test_parse_float'))
    suite.addTests(loader.loadTestsFromName(
            'test_range.TestNagiosRange.test_invalid'))
    suite.addTests(loader.loadTestsFromName(
            'test_range.TestNagiosRange.test_limits'))
    suite.addTests(loader.loadTestsFromName(
            'test_range.TestNagiosRange.test_limits_infinity'))
    suite.addTests(loader.loadTestsFromName(
            'test_range.TestNagiosRange.test_check_simple'))

    runner = unittest.TextTestRunner(verbosity = args.verbose)

    result = runner.run(suite)

#==============================================================================

# vim: tabstop=4 expandtab shiftwidth=4 softtabstop=4 nu
