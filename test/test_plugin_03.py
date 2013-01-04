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
from general import ColoredFormatter, pp, get_arg_verbose, init_root_logger
from general import NeedConfig, NeedTmpConfig

import nagios
from nagios import FakeExitError

from nagios.plugin import NagiosPluginError
from nagios.plugin import NagiosPlugin

from nagios.plugin.threshold import NagiosThreshold

from nagios.plugin.config import NoConfigfileFound

log = logging.getLogger(__name__)

#==============================================================================
class TestNagiosPlugin3(NeedConfig):

    #--------------------------------------------------------------------------
    def setUp(self):

        super(TestNagiosPlugin3, self).setUp()

        self.plugin_name = 'TEST_CHECK_MESSAGES'
        self.plugin = NagiosPlugin(shortname = self.plugin_name)

    #--------------------------------------------------------------------------
    def test_plugin_object(self):

        log.info("Testing NagiosPlugin object shortname %r.", self.plugin_name)
        self.assertEqual(self.plugin.shortname, self.plugin_name)

    #--------------------------------------------------------------------------
    def test_codes(self):

        codes = [
            [['Critical'], ['Warning'], nagios.state.critical],
            [[],           ['Warning'], nagios.state.warning],
            [[],           [],          nagios.state.ok],
        ]

        i = 0
        for fields in codes:

            c_msgs = fields[0]
            w_msgs = fields[1]
            exp_code = fields[2]
            i += 1

            (got_code, message) = self.plugin.check_messages(
                    critical = c_msgs, warning = w_msgs)
            log.debug(("Test %d: Crit messages: %r, Warn messages: %r, " +
                    "got code %d, got message: %r."), i, c_msgs, w_msgs,
                    got_code, message)
            self.assertEqual(got_code, exp_code)

#==============================================================================

if __name__ == '__main__':

    verbose = get_arg_verbose()
    init_root_logger(verbose)

    log.info("Starting tests ...")

    loader = unittest.TestLoader()
    suite = unittest.TestSuite()

    suite.addTests(loader.loadTestsFromName(
            'test_plugin_03.TestNagiosPlugin3.test_plugin_object'))
    suite.addTests(loader.loadTestsFromName(
            'test_plugin_03.TestNagiosPlugin3.test_codes'))

    runner = unittest.TextTestRunner(verbosity = verbose)

    result = runner.run(suite)

#==============================================================================

# vim: tabstop=4 expandtab shiftwidth=4 softtabstop=4 nu
