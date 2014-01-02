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
class TestNagiosPlugin3(NeedConfig):

    #--------------------------------------------------------------------------
    def setUp(self):

        super(TestNagiosPlugin3, self).setUp()

        self.plugin_name = 'TEST_CHECK_MESSAGES'
        self.plugin = NagiosPlugin(shortname = self.plugin_name)

        self.msgs = {
                'critical': 'A B C',
                'warning':  'D E F',
                'ok':       'G I H',
        }

    #--------------------------------------------------------------------------
    def test_plugin_object(self):

        log.info("Testing NagiosPlugin object shortname %r.", self.plugin_name)
        self.assertEqual(self.plugin.shortname, self.plugin_name)

    #--------------------------------------------------------------------------
    def test_codes(self):

        log.info("Testing check_messages() return code.")
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

    #--------------------------------------------------------------------------
    def test_messages(self):

        log.info("Testing check_messages() return message.")
        arrays = {
            'critical': ['A', 'B', 'C'],
            'warning':  ['D', 'E', 'F'],
            'ok':       ['G', 'H', 'I'],
        }

        messages = {}
        for key in arrays:
            messages[key] = ' '.join(arrays[key])

        (code, message) = self.plugin.check_messages(
                critical = arrays['critical'], warning = arrays['warning'])
        log.debug("Checking code %d, message %r.", code, message)
        self.assertEqual(code, nagios.state.critical)
        self.assertEqual(message, messages['critical'])

        (code, message) = self.plugin.check_messages(
                critical = arrays['critical'], warning = arrays['warning'],
                ok = 'G H I')
        log.debug("Checking code %d, message %r.", code, message)
        self.assertEqual(code, nagios.state.critical)
        self.assertEqual(message, messages['critical'])

        (code, message) = self.plugin.check_messages(
                warning = arrays['warning'])
        log.debug("Checking code %d, message %r.", code, message)
        self.assertEqual(code, nagios.state.warning)
        self.assertEqual(message, messages['warning'])

        (code, message) = self.plugin.check_messages(
                warning = arrays['warning'], ok = 'G H I')
        log.debug("Checking code %d, message %r.", code, message)
        self.assertEqual(code, nagios.state.warning)
        self.assertEqual(message, messages['warning'])

        (code, message) = self.plugin.check_messages(ok = arrays['ok'])
        log.debug("Checking code %d, message %r.", code, message)
        self.assertEqual(code, nagios.state.ok)
        self.assertEqual(message, messages['ok'])

        (code, message) = self.plugin.check_messages(ok = 'G H I')
        log.debug("Checking code %d, message %r.", code, message)
        self.assertEqual(code, nagios.state.ok)
        self.assertEqual(message, messages['ok'])

        # explicit join
        join = '+'
        (code, message) = self.plugin.check_messages(
                critical = arrays['critical'], warning = arrays['warning'],
                join = join)
        log.debug("Checking code %d, message %r.", code, message)
        self.assertEqual(message, join.join(arrays['critical']))

        join = ''
        (code, message) = self.plugin.check_messages(
                warning = arrays['warning'], join = join)
        log.debug("Checking code %d, message %r.", code, message)
        self.assertEqual(message, join.join(arrays['warning']))

        join = None
        (code, message) = self.plugin.check_messages(
                ok = arrays['ok'], join = join)
        log.debug("Checking code %d, message %r.", code, message)
        self.assertEqual(message, ' '.join(arrays['ok']))

        #join_all messages
        join_all = ' :: '
        msg_all_cwo = join_all.join([messages[x] for x in ('critical', 'warning', 'ok')])
        msg_all_cw = join_all.join([messages[x] for x in ('critical', 'warning')])
        msg_all_wo = join_all.join([messages[x] for x in ('warning', 'ok')])

        log.debug("Checking join_all critical, warning, ok.")
        (code, message) = self.plugin.check_messages(
                critical = arrays['critical'], warning = arrays['warning'],
                ok = arrays['ok'], join_all = join_all)
        log.debug("Checking code %d, message %r.", code, message)
        self.assertEqual(code, nagios.state.critical)
        self.assertEqual(message, msg_all_cwo)

        log.debug("Checking join_all critical, warning.")
        (code, message) = self.plugin.check_messages(
                critical = arrays['critical'], warning = arrays['warning'],
                join_all = join_all)
        log.debug("Checking code %d, message %r.", code, message)
        self.assertEqual(code, nagios.state.critical)
        self.assertEqual(message, msg_all_cw)

        log.debug("Checking join_all warning, ok.")
        (code, message) = self.plugin.check_messages(warning = arrays['warning'],
                ok = arrays['ok'], join_all = join_all)
        log.debug("Checking code %d, message %r.", code, message)
        self.assertEqual(code, nagios.state.warning)
        self.assertEqual(message, msg_all_wo)

        log.debug("Checking join_all warning.")
        (code, message) = self.plugin.check_messages(warning = arrays['warning'],
                join_all = join_all)
        log.debug("Checking code %d, message %r.", code, message)
        self.assertEqual(code, nagios.state.warning)
        self.assertEqual(message, messages['warning'])

    #--------------------------------------------------------------------------
    def test_add_message01(self):

        log.info("Testing add_message() 01 ...")

        self.plugin.add_message('critical', self.msgs['critical'])
        self.plugin.add_message('warning', self.msgs['warning'])
        (code, message) = self.plugin.check_messages()
        log.debug("Checking code %d, message %r.", code, message)
        self.assertEqual(code, nagios.state.critical)
        self.assertEqual(message, self.msgs['critical'])

    #--------------------------------------------------------------------------
    def test_add_message02(self):

        log.info("Testing add_message() 02 ...")

        self.plugin.add_message('critical', self.msgs['critical'])
        (code, message) = self.plugin.check_messages()
        log.debug("Checking code %d, message %r.", code, message)
        self.assertEqual(code, nagios.state.critical)
        self.assertEqual(message, self.msgs['critical'])

    #--------------------------------------------------------------------------
    def test_add_message03(self):

        log.info("Testing add_message() 03 ...")

        self.plugin.add_message('warning', self.msgs['warning'])
        (code, message) = self.plugin.check_messages()
        log.debug("Checking code %d, message %r.", code, message)
        self.assertEqual(code, nagios.state.warning)
        self.assertEqual(message, self.msgs['warning'])

    #--------------------------------------------------------------------------
    def test_add_message04(self):

        log.info("Testing add_message() 04 ...")

        self.plugin.add_message('warning', self.msgs['warning'])
        self.plugin.add_message('ok', self.msgs['ok'])
        (code, message) = self.plugin.check_messages()
        log.debug("Checking code %d, message %r.", code, message)
        self.assertEqual(code, nagios.state.warning)
        self.assertEqual(message, self.msgs['warning'])

    #--------------------------------------------------------------------------
    def test_add_message05(self):

        log.info("Testing add_message() 05 ...")

        self.plugin.add_message('ok', self.msgs['ok'])
        (code, message) = self.plugin.check_messages()
        log.debug("Checking code %d, message %r.", code, message)
        self.assertEqual(code, nagios.state.ok)
        self.assertEqual(message, self.msgs['ok'])

    #--------------------------------------------------------------------------
    def test_add_message06(self):

        log.info("Testing add_message() 06 ...")

        (code, message) = self.plugin.check_messages()
        log.debug("Checking code %d, message %r.", code, message)
        self.assertEqual(code, nagios.state.ok)
        self.assertEqual(message, '')

    #--------------------------------------------------------------------------
    def test_add_message_invalid(self):

        log.info("Testing add_message() with invalid codes ...")

        for key in ('foobar', 'OKAY', 'unknown', 'dependent'):
            log.debug("Trying to add a message with code %r ...", key)
            with self.assertRaises(NagiosPluginError) as cm:
                self.plugin.add_message(key, 'hi mum')
            log.debug("Got a NagiosPluginError: %s", str(cm.exception))

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
    suite.addTests(loader.loadTestsFromName(
            'test_plugin_03.TestNagiosPlugin3.test_messages'))
    suite.addTests(loader.loadTestsFromName(
            'test_plugin_03.TestNagiosPlugin3.test_add_message01'))
    suite.addTests(loader.loadTestsFromName(
            'test_plugin_03.TestNagiosPlugin3.test_add_message02'))
    suite.addTests(loader.loadTestsFromName(
            'test_plugin_03.TestNagiosPlugin3.test_add_message03'))
    suite.addTests(loader.loadTestsFromName(
            'test_plugin_03.TestNagiosPlugin3.test_add_message04'))
    suite.addTests(loader.loadTestsFromName(
            'test_plugin_03.TestNagiosPlugin3.test_add_message05'))
    suite.addTests(loader.loadTestsFromName(
            'test_plugin_03.TestNagiosPlugin3.test_add_message06'))
    suite.addTests(loader.loadTestsFromName(
            'test_plugin_03.TestNagiosPlugin3.test_add_message_invalid'))

    runner = unittest.TextTestRunner(verbosity = verbose)

    result = runner.run(suite)

#==============================================================================

# vim: tabstop=4 expandtab shiftwidth=4 softtabstop=4 nu
