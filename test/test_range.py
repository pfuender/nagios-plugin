#!/usr/bin/env python
# -*- coding: utf-8 -*-
'''
@author: Frank Brehm
@contact: frank.brehm@profitbricks.com
@organization: Profitbricks GmbH
@copyright: © 2010 - 2014 by Profitbricks GmbH
@license: GPL3
@summary: test script (and module) for unit tests on NagiosRange objects
'''

import unittest
import os
import sys
import logging

libdir = os.path.abspath(os.path.join(os.path.dirname(sys.argv[0]), '..'))
sys.path.insert(0, libdir)

import general
from general import ColoredFormatter, get_arg_verbose, init_root_logger
from general import NagiosPluginTestcase

log = logging.getLogger(__name__)

#==============================================================================
class TestNagiosRange(NagiosPluginTestcase):

    #--------------------------------------------------------------------------
    def setUp(self):
        pass

    #--------------------------------------------------------------------------
    def test_import_modules(self):

        log.info("Test importing all appropriate modules ...")

        log.debug("Importing module %r ...", "nagios")
        import nagios

        log.debug("Importing %r from %r ...", 'NagiosRangeError', 'nagios.plugin.range')
        from nagios.plugin.range import NagiosRangeError

        log.debug("Importing %r from %r ...", 'InvalidRangeError', 'nagios.plugin.range')
        from nagios.plugin.range import InvalidRangeError

        log.debug("Importing %r from %r ...", 'InvalidRangeValueError', 'nagios.plugin.range')
        from nagios.plugin.range import InvalidRangeValueError

        log.debug("Importing %r from %r ...", 'NagiosRange', 'nagios.plugin.range')
        from nagios.plugin.range import NagiosRange

    #--------------------------------------------------------------------------
    def test_empty_object(self):

        log.info("Testing uninitialized range object.")

        import nagios
        from nagios.plugin.range import NagiosRange

        try:
            nrange = NagiosRange()
            log.debug("NagiosRange object: %r", nrange)
        except Exception as e:
            self.fail("Could not instatiate NagiosRange by a %s: %s" % (
                    e.__class__.__name__, str(e)))

    #--------------------------------------------------------------------------
    def test_parse_normal(self):

        log.info("Testing initialized range object.")

        import nagios
        from nagios.plugin.range import NagiosRange

        try:
            nrange = NagiosRange('1:10')
            log.debug("NagiosRange object: %r", nrange)
        except Exception as e:
            self.fail("Could not instatiate NagiosRange by a %s: %s" % (
                    e.__class__.__name__, str(e)))

    #--------------------------------------------------------------------------
    def test_parse_float(self):

        log.info("Testing initialized range object with float limits.")

        import nagios
        from nagios.plugin.range import NagiosRange

        try:
            nrange = NagiosRange('1.1:10.999')
            log.debug("NagiosRange object: %r", nrange)
        except Exception as e:
            self.fail("Could not instatiate NagiosRange by a %s: %s" % (
                    e.__class__.__name__, str(e)))

    #--------------------------------------------------------------------------
    def test_invalid(self):

        values = (':', '1:~', 'foo', '1-10', '10:~', '1-10:2.4', '1,10', '5:3',
                    '~:')
        log.info("Checking for invalid ranges ...")

        import nagios
        from nagios.plugin.range import NagiosRange
        from nagios.plugin.range import InvalidRangeError

        for value in values:
            try:
                nrange = NagiosRange(value)
            except InvalidRangeError as e:
                log.debug("Found incorrect range %r.", value)
            else:
                self.fail("Range %r should be incorrect, but lead to %r.",
                        value, nrange)

    #--------------------------------------------------------------------------
    def test_limits(self):

        log.info("Checking range limits ...")

        import nagios
        from nagios.plugin.range import NagiosRange

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
        except Exception as e:
            self.fail("Could not instatiate NagiosRange by a %s: %s" % (
                    e.__class__.__name__, str(e)))

    #--------------------------------------------------------------------------
    def test_limits_infinity(self):

        log.info("Checking neative infinity range limits ...")

        import nagios
        from nagios.plugin.range import NagiosRange

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
        except Exception as e:
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

        log.info("Testing range 0 .. 6")

        import nagios
        from nagios.plugin.range import NagiosRange

        try:
            nrange = NagiosRange('6')
            log.debug("NagiosRange object: %r", nrange)
            nrange_str = str(nrange)
            log.debug("Stringified NagiosRange object: %r", nrange_str)
            if nrange_str != '6':
                self.fail("Stringified NagiosRange should be '6'.")

            for value in sorted(expected_results.keys()):
                exp_result = expected_results[value]
                result = nrange.check(value)
                log.debug("Check %r, result is %r, expected is %r", value,
                        result, exp_result)
                if not exp_result == result:
                    self.fail("Unexpected result of check(), checked %r "
                            "against '0:6', got %r, expected %r." % (value,
                            result, exp_result))

        except Exception as e:
            self.fail("Could not instatiate NagiosRange by a %s: %s" % (
                    e.__class__.__name__, str(e)))

    #--------------------------------------------------------------------------
    def test_check_normal1(self):

        expected_results = {
                -23: False,
                -7: True,
                -1: True,
                0: True,
                4: True,
                23: True,
                23.1: False,
                79.999999: False,
        }

        log.info("Testing range -7 .. 23")

        import nagios
        from nagios.plugin.range import NagiosRange

        try:
            nrange = NagiosRange('-7:23')
            log.debug("NagiosRange object: %r", nrange)
            nrange_str = str(nrange)
            log.debug("Stringified NagiosRange object: %r", nrange_str)
            if nrange_str != '-7:23':
                self.fail("Stringified NagiosRange should be '-7:23'.")

            for value in sorted(expected_results.keys()):
                exp_result = expected_results[value]
                result = nrange.check(value)
                log.debug("Check %r, result is %r, expected is %r", value,
                        result, exp_result)
                if not exp_result == result:
                    self.fail("Unexpected result of check(), checked %r "
                            "against '0:6', got %r, expected %r." % (value,
                            result, exp_result))

        except Exception as e:
            self.fail("Could not instatiate NagiosRange by a %s: %s" % (
                    e.__class__.__name__, str(e)))

    #--------------------------------------------------------------------------
    def test_check_normal2(self):

        expected_results = {
                -1: False,
                0: True,
                4: True,
                5.75: True,
                5.7501: False,
                6: False,
                6.1: False,
                79.999999: False,
        }

        log.info("Testing range 0 .. 5.75")

        import nagios
        from nagios.plugin.range import NagiosRange

        try:
            nrange = NagiosRange(':5.75')
            log.debug("NagiosRange object: %r", nrange)
            nrange_str = str(nrange)
            log.debug("Stringified NagiosRange object: %r", nrange_str)
            if nrange_str != '5.75':
                self.fail("Stringified NagiosRange should be '5.75'.")

            for value in sorted(expected_results.keys()):
                exp_result = expected_results[value]
                result = nrange.check(value)
                log.debug("Check %r, result is %r, expected is %r", value,
                        result, exp_result)
                if not exp_result == result:
                    self.fail("Unexpected result of check(), checked %r "
                            "against '0:6', got %r, expected %r." % (value,
                            result, exp_result))

        except Exception as e:
            self.fail("Could not instatiate NagiosRange by a %s: %s" % (
                    e.__class__.__name__, str(e)))

    #--------------------------------------------------------------------------
    def test_check_infinity1(self):

        expected_results = {
                -1001341: True,
                -96: True,
                -95.999: True,
                -95.99: True,
                -95.989: False,
                -95: False,
                0: False,
                5.7501: False,
                79.999999: False,
        }

        log.info("Testing range negative infinity .. -95.99")

        import nagios
        from nagios.plugin.range import NagiosRange

        try:
            nrange = NagiosRange('~:-95.99')
            log.debug("NagiosRange object: %r", nrange)
            nrange_str = str(nrange)
            log.debug("Stringified NagiosRange object: %r", nrange_str)
            if nrange_str != '~:-95.99':
                self.fail("Stringified NagiosRange should be '~:-95.99'.")

            for value in sorted(expected_results.keys()):
                exp_result = expected_results[value]
                result = nrange.check(value)
                log.debug("Check %r, result is %r, expected is %r", value,
                        result, exp_result)
                if not exp_result == result:
                    self.fail("Unexpected result of check(), checked %r "
                            "against '0:6', got %r, expected %r." % (value,
                            result, exp_result))

        except Exception as e:
            self.fail("Could not instatiate NagiosRange by a %s: %s" % (
                    e.__class__.__name__, str(e)))

    #--------------------------------------------------------------------------
    def test_check_infinity2(self):

        expected_results = {
                -95.999: False,
                -1: False,
                0: False,
                9.91: False,
                10: True,
                11.1: True,
                123456789012346: True,
        }

        log.info("Testing range 10 .. infinity")

        import nagios
        from nagios.plugin.range import NagiosRange

        try:
            nrange = NagiosRange('10:')
            log.debug("NagiosRange object: %r", nrange)
            nrange_str = str(nrange)
            log.debug("Stringified NagiosRange object: %r", nrange_str)
            if nrange_str != '10:':
                self.fail("Stringified NagiosRange should be '10:'.")

            for value in sorted(expected_results.keys()):
                exp_result = expected_results[value]
                result = nrange.check(value)
                log.debug("Check %r, result is %r, expected is %r", value,
                        result, exp_result)
                if not exp_result == result:
                    self.fail("Unexpected result of check(), checked %r "
                            "against '0:6', got %r, expected %r." % (value,
                            result, exp_result))

        except Exception as e:
            self.fail("Could not instatiate NagiosRange by a %s: %s" % (
                    e.__class__.__name__, str(e)))

    #--------------------------------------------------------------------------
    def test_check_zero(self):

        expected_results = {
                0.5: False,
                0: True,
                -10: True,
        }

        log.info("Testing range <= zero")

        import nagios
        from nagios.plugin.range import NagiosRange

        try:
            nrange = NagiosRange('~:0')
            log.debug("NagiosRange object: %r", nrange)
            nrange_str = str(nrange)
            log.debug("Stringified NagiosRange object: %r", nrange_str)
            if nrange_str != '~:0':
                self.fail("Stringified NagiosRange should be '~:0'.")

            for value in sorted(expected_results.keys()):
                exp_result = expected_results[value]
                result = nrange.check(value)
                log.debug("Check %r, result is %r, expected is %r", value,
                        result, exp_result)
                if not exp_result == result:
                    self.fail("Unexpected result of check(), checked %r "
                            "against '0:6', got %r, expected %r." % (value,
                            result, exp_result))

        except Exception as e:
            self.fail("Could not instatiate NagiosRange by a %s: %s" % (
                    e.__class__.__name__, str(e)))

    #--------------------------------------------------------------------------
    def test_method_check_range(self):

        log.info("Testing method check_range() ...")

        import nagios
        from nagios.plugin.range import NagiosRange

        try:
            nrange = NagiosRange(':6')
            log.debug("NagiosRange object: %r", nrange)

            log.debug("Testing check_range(5) == False ...")
            if nrange.check_range(5):
                self.fail("check_range(5) should return False.")

            log.debug("Testing check_range(7) == True ...")
            if not nrange.check_range(7):
                self.fail("check_range(7) should return True.")

        except Exception as e:
            self.fail("Could not instatiate NagiosRange by a %s: %s" % (
                    e.__class__.__name__, str(e)))

    #--------------------------------------------------------------------------
    def test_check_inverse(self):

        expected_results = {
                -134151: True,
                -2: True,
                -1: True,
                0: False,
                0.001: False,
                32.88: False,
                657.8210567: False,
                657.9: True,
                123456789012345: True,
        }

        log.info("Testing range inverse 0 .. 657.8210567")

        import nagios
        from nagios.plugin.range import NagiosRange

        try:
            nrange = NagiosRange('@0:657.8210567')
            log.debug("NagiosRange object: %r", nrange)
            nrange_str = str(nrange)
            log.debug("Stringified NagiosRange object: %r", nrange_str)
            if nrange_str != '@657.8210567':
                self.fail("Stringified NagiosRange should be '@0:657.8210567'.")

            for value in sorted(expected_results.keys()):
                exp_result = expected_results[value]
                result = nrange.check(value)
                log.debug("Check %r, result is %r, expected is %r", value,
                        result, exp_result)
                if not exp_result == result:
                    self.fail("Unexpected result of check(), checked %r "
                            "against '0:6', got %r, expected %r." % (value,
                            result, exp_result))

        except Exception as e:
            self.fail("Could not instatiate NagiosRange by a %s: %s" % (
                    e.__class__.__name__, str(e)))

    #--------------------------------------------------------------------------
    def test_check_singelton(self):

        expected_results = {
                -1: False,
                0: False,
                0.5: False,
                1: True,
                1.001: False,
                5.2: False,
        }

        log.info("Testing range 1 .. 1")

        import nagios
        from nagios.plugin.range import NagiosRange

        try:
            nrange = NagiosRange('1:1')
            log.debug("NagiosRange object: %r", nrange)
            nrange_str = str(nrange)
            log.debug("Stringified NagiosRange object: %r", nrange_str)
            if nrange_str != '1:1':
                self.fail("Stringified NagiosRange should be '1:1'.")

            for value in sorted(expected_results.keys()):
                exp_result = expected_results[value]
                result = nrange.check(value)
                log.debug("Check %r, result is %r, expected is %r", value,
                        result, exp_result)
                if not exp_result == result:
                    self.fail("Unexpected result of check(), checked %r "
                            "against '0:6', got %r, expected %r." % (value,
                            result, exp_result))

        except Exception as e:
            self.fail("Could not instatiate NagiosRange by a %s: %s" % (
                    e.__class__.__name__, str(e)))

    #--------------------------------------------------------------------------
    def test_operator_in(self):

        log.info("Testing overloaded operator 'in' ...")

        import nagios
        from nagios.plugin.range import NagiosRange

        try:
            nrange = NagiosRange('6')
            log.debug("NagiosRange object: %r", nrange)

            log.debug("Checking '7 in range \"%s\"'", nrange)
            if 7 in nrange:
                self.fail("Value 7 should be outside range '%s'." % (nrange))

            log.debug("Checking '5 not in range \"%s\"'", nrange)
            if not 5 in nrange:
                self.fail("Value 5 should be inside range '%s'." % (nrange))

        except Exception as e:
            self.fail("Could not instatiate NagiosRange by a %s: %s" % (
                    e.__class__.__name__, str(e)))

#==============================================================================

if __name__ == '__main__':

    verbose = get_arg_verbose()
    if verbose is None:
        verbose = 0
    init_root_logger(verbose)

    log.info("Starting tests ...")

    suite = unittest.TestSuite()

    suite.addTest(TestNagiosRange('test_import_modules', verbose))
    suite.addTest(TestNagiosRange('test_empty_object', verbose))
    suite.addTest(TestNagiosRange('test_parse_normal', verbose))
    suite.addTest(TestNagiosRange('test_parse_float', verbose))
    suite.addTest(TestNagiosRange('test_invalid', verbose))
    suite.addTest(TestNagiosRange('test_limits', verbose))
    suite.addTest(TestNagiosRange('test_limits_infinity', verbose))
    suite.addTest(TestNagiosRange('test_check_simple', verbose))
    suite.addTest(TestNagiosRange('test_check_normal1', verbose))
    suite.addTest(TestNagiosRange('test_check_normal2', verbose))
    suite.addTest(TestNagiosRange('test_check_infinity1', verbose))
    suite.addTest(TestNagiosRange('test_check_infinity2', verbose))
    suite.addTest(TestNagiosRange('test_check_zero', verbose))
    suite.addTest(TestNagiosRange('test_method_check_range', verbose))
    suite.addTest(TestNagiosRange('test_check_inverse', verbose))
    suite.addTest(TestNagiosRange('test_check_singelton', verbose))
    suite.addTest(TestNagiosRange('test_operator_in', verbose))

    runner = unittest.TextTestRunner(verbosity = verbose)

    result = runner.run(suite)

#==============================================================================

# vim: tabstop=4 expandtab shiftwidth=4 softtabstop=4
