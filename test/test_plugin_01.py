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

libdir = os.path.abspath(os.path.join(os.path.dirname(sys.argv[0]), '..'))
sys.path.insert(0, libdir)

import general
from general import ColoredFormatter, pp, get_arg_verbose, init_root_logger
from general import NeedConfig, NeedTmpConfig

import nagios
from nagios import FakeExitError

from nagios.plugin import NagiosPluginError
from nagios.plugin import NagiosPlugin

from nagios.plugin.config import NoConfigfileFound

log = logging.getLogger(__name__)

#==============================================================================
class TestNagiosPlugin(NeedConfig):

    #--------------------------------------------------------------------------
    def test_plugin_object(self):

        log.info("Testing NagiosPlugin object.")
        plugin = NagiosPlugin(
                usage = '%(prog)s --hello',
                url = 'http://www.profitbricks.com',
                blurb = 'Senseless sample Nagios plugin.',
                licence = 'Licence: GNU Lesser General Public License (LGPL), Version 3',
                extra = 'Bla blub',
        )
        plugin.add_perfdata('bla', 10, 'MByte', warning = '20', critical = '30')
        plugin.set_thresholds(warning = '10:25', critical = "~:25")
        plugin.add_message(nagios.state.ok, 'bli', 'bla')
        plugin.add_message('warning', 'blub')
        log.debug("NagiosPluginArgparse object: %r", plugin)
        log.debug("NagiosPluginArgparse object: %s", str(plugin))

#    #--------------------------------------------------------------------------
#    def test_argparse_show_version(self):
#
#        log.info("Testing NagiosPluginArgparse showing version.")
#        na = NagiosPluginArgparse(
#                usage = '%(prog)s --version',
#                url = 'http://www.profitbricks.com',
#                blurb = 'Senseless sample Nagios plugin.',
#                extra = 'Bla blub',
#        )
#
#        try:
#            na.parse_args(['--version'])
#        except FakeExitError, e:
#            log.debug("NagiosPluginArgparse exited with exit value %d.", e.exit_value)
#            log.debug("Message on exit: >>>%s<<<", e.msg)
#
#    #--------------------------------------------------------------------------
#    def test_argparse_show_usage(self):
#
#        log.info("Testing NagiosPluginArgparse showing usage.")
#        na = NagiosPluginArgparse(
#                usage = '%(prog)s --version',
#                url = 'http://www.profitbricks.com',
#                blurb = 'Senseless sample Nagios plugin.',
#                extra = 'Bla blub',
#        )
#
#        try:
#            na.parse_args(['--usage'])
#        except FakeExitError, e:
#            log.debug("NagiosPluginArgparse exited with exit value %d.", e.exit_value)
#            log.debug("Message on exit: >>>%s<<<", e.msg)
#
#    #--------------------------------------------------------------------------
#    def test_argparse_parse_help(self):
#
#        log.info("Testing NagiosPluginArgparse generating help.")
#        na = NagiosPluginArgparse(
#                usage = '%(prog)s --help',
#                url = 'http://www.profitbricks.com',
#                blurb = 'Senseless sample Nagios plugin.',
#                extra = 'Bla blub\n\nblubber blub',
#                licence = 'Licence: GNU Lesser General Public License (LGPL), Version 3',
#        )
#
#        try:
#            na.parse_args(['-h'])
#        except FakeExitError, e:
#            log.debug("NagiosPluginArgparse exited with exit value %d.", e.exit_value)
#            log.debug("Message on exit: >>>%s<<<", e.msg)
#
#    #--------------------------------------------------------------------------
#    def test_argparse_wrong_argument(self):
#
#        log.info("Testing NagiosPluginArgparse for a wrong argument.")
#        na = NagiosPluginArgparse(
#                usage = '%(prog)s',
#                url = 'http://www.profitbricks.com',
#                blurb = 'Senseless sample Nagios plugin.',
#                licence = '',
#        )
#
#        try:
#            na.parse_args(['--bli-bla-blub'])
#        except FakeExitError, e:
#            log.debug("NagiosPluginArgparse exited with exit value %d.", e.exit_value)
#            log.debug("Message on exit: >>>%s<<<", e.msg)

#==============================================================================

if __name__ == '__main__':

    verbose = get_arg_verbose()
    init_root_logger(verbose)

    log.info("Starting tests ...")

    loader = unittest.TestLoader()
    suite = unittest.TestSuite()

    suite.addTests(loader.loadTestsFromName(
            'test_plugin_01.TestNagiosPlugin.test_plugin_object'))

    runner = unittest.TextTestRunner(verbosity = verbose)

    result = runner.run(suite)

#==============================================================================

# vim: tabstop=4 expandtab shiftwidth=4 softtabstop=4 nu
