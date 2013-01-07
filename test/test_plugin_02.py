#!/usr/bin/env python
# -*- coding: utf-8 -*-
'''
@author: Frank Brehm
@contact: frank.brehm@profitbricks.com
@organization: Profitbricks GmbH
@copyright: © 2010-2013 by Profitbricks GmbH
@license: GPL3
@summary: test script (and module) for unit tests on NagiosPlugin objects
'''

import unittest
import os
import sys
import logging
import re

from collections import OrderedDict

libdir = os.path.abspath(os.path.join(os.path.dirname(sys.argv[0]), '..'))
sys.path.insert(0, libdir)

import general
from general import ColoredFormatter, get_arg_verbose, init_root_logger
from general import NeedConfig, NeedTmpConfig

import nagios
from nagios import FakeExitError

from nagios.plugin import NagiosPluginError
from nagios.plugin import NagiosPlugin

from nagios.plugin.threshold import NagiosThreshold

from nagios.plugin.config import NoConfigfileFound

log = logging.getLogger(__name__)

#==============================================================================
class TestNagiosPlugin2(NeedConfig):

    #--------------------------------------------------------------------------
    def setUp(self):

        super(TestNagiosPlugin2, self).setUp()

        self.plugin_name = 'TEST_PLUGIN'
        self.plugin = NagiosPlugin(shortname = self.plugin_name)

    #--------------------------------------------------------------------------
    def test_plugin_object(self):

        log.info("Testing NagiosPlugin object shortname.")
        self.assertEqual(self.plugin.shortname, self.plugin_name)

    #--------------------------------------------------------------------------
    def test_nagios_exit(self):

        log.info("Testing nagios_exit() ...")
        ok = [
            [nagios.state.ok,        'OK',        'test the first', ],
            [nagios.state.warning,   'WARNING',   'test the second' ],
            [nagios.state.critical,  'CRITICAL',  'test the third', ],
            [nagios.state.unknown,   'UNKNOWN',   'test the fourth',],
            [nagios.state.dependent, 'DEPENDENT', 'test the fifth', ],
        ]

        for fields in ok:

            code = fields[0]
            marker = fields[1]
            msg = fields[2]

            # Test for numeric return codes
            with self.assertRaises(FakeExitError) as cm:
                self.plugin.nagios_exit(code, msg)
            e = cm.exception
            ret_code = e.exit_value
            e_msg = e.msg
            log.debug("Exit with value %d and the message %r.", ret_code, e_msg)
            self.assertEqual(ret_code, code)
            pattern = r'%s\b.*%s\b.*\b%s$' % (self.plugin_name, marker, msg)
            log.debug("Checking for pattern %r.", pattern)
            regex = re.compile(pattern)
            self.assertRegexpMatches(e_msg, regex)

            # Test for string return codes
            with self.assertRaises(FakeExitError) as cm:
                self.plugin.nagios_exit(marker, msg)
            e = cm.exception
            ret_code = e.exit_value
            e_msg = e.msg
            log.debug("Exit with value %d and the message %r.", ret_code, e_msg)
            self.assertEqual(ret_code, code)
            pattern = r'%s\b.*%s\b.*\b%s$' % (self.plugin_name, marker, msg)
            log.debug("Checking for pattern %r.", pattern)
            regex = re.compile(pattern)
            self.assertRegexpMatches(e_msg, regex)

    #--------------------------------------------------------------------------
    def test_nagios_exit_ugly_code(self):

        log.info("Testing nagios_exit() with ugly codes ...")
        ugly = [
            [      -1, 'testing code -1'],
            [       7, 'testing code 7'],
            [    None, 'testing code None'],
            [      '', "testing code ''"],
            ['string', "testing code 'string'"],
        ]

        for fields in ugly:

            code = fields[0]
            msg = fields[1]

            with self.assertRaises(FakeExitError) as cm:
                self.plugin.nagios_exit(code, msg)
            e = cm.exception
            ret_code = e.exit_value
            e_msg = e.msg
            log.debug("Exit with value %d and the message %r.", ret_code, e_msg)
            self.assertEqual(ret_code, nagios.state.unknown)
            pattern = r'%s\b.*UNKNOWN\b.*\b%s$' % (self.plugin_name, msg)
            log.debug("Checking for pattern %r.", pattern)
            regex = re.compile(pattern)
            self.assertRegexpMatches(e_msg, regex)

    #--------------------------------------------------------------------------
    def test_nagios_exit_ugly_msg(self):

        log.info("Testing nagios_exit() with ugly messages ...")

        ugly = ['', None, nagios.state.unknown]

        for msg in ugly:

            with self.assertRaises(FakeExitError) as cm:
                self.plugin.nagios_exit(nagios.state.critical, msg)
            e = cm.exception
            ret_code = e.exit_value
            e_msg = e.msg
            log.debug("Exit with value %d and the message %r.", ret_code, e_msg)
            self.assertEqual(ret_code, nagios.state.critical)
            display = msg
            if display is None:
                display = ''
            pattern = r'%s\b.*CRITICAL\b.*\b%s$' % (self.plugin_name, display)
            log.debug("Checking for pattern %r.", pattern)
            regex = re.compile(pattern)
            self.assertRegexpMatches(e_msg, regex)

    #--------------------------------------------------------------------------
    def test_nagios_die(self):

        log.info("Testing nagios_die() ...")

        ugly = ['die you dog', '', None]

        for msg in ugly:

            with self.assertRaises(FakeExitError) as cm:
                self.plugin.nagios_die(msg)
            e = cm.exception
            ret_code = e.exit_value
            e_msg = e.msg
            log.debug("Exit with value %d and the message %r.", ret_code, e_msg)
            self.assertEqual(ret_code, nagios.state.unknown)
            display = msg
            if display is None:
                display = ''
            pattern = r'%s\b.*UNKNOWN\b.*\b%s$' % (self.plugin_name, display)
            log.debug("Checking for pattern %r.", pattern)
            regex = re.compile(pattern)
            self.assertRegexpMatches(e_msg, regex)

#==============================================================================

if __name__ == '__main__':

    verbose = get_arg_verbose()
    init_root_logger(verbose)

    log.info("Starting tests ...")

    loader = unittest.TestLoader()
    suite = unittest.TestSuite()

    suite.addTests(loader.loadTestsFromName(
            'test_plugin_02.TestNagiosPlugin2.test_plugin_object'))
    suite.addTests(loader.loadTestsFromName(
            'test_plugin_02.TestNagiosPlugin2.test_nagios_exit'))
    suite.addTests(loader.loadTestsFromName(
            'test_plugin_02.TestNagiosPlugin2.test_nagios_exit_ugly_code'))
    suite.addTests(loader.loadTestsFromName(
            'test_plugin_02.TestNagiosPlugin2.test_nagios_exit_ugly_msg'))
    suite.addTests(loader.loadTestsFromName(
            'test_plugin_02.TestNagiosPlugin2.test_nagios_die'))

    runner = unittest.TextTestRunner(verbosity = verbose)

    result = runner.run(suite)

#==============================================================================

# vim: tabstop=4 expandtab shiftwidth=4 softtabstop=4 nu
