#!/usr/bin/env python
# -*- coding: utf-8 -*-
'''
@author: Frank Brehm
@contact: frank.brehm@profitbricks.com
@organization: Profitbricks GmbH
@copyright: © 2010-2013 by Profitbricks GmbH
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
from general import ColoredFormatter, get_arg_verbose, init_root_logger
from general import NeedConfig, NeedTmpConfig

import nagios
from nagios import FakeExitError

from nagios.plugin.config import NoConfigfileFound
from nagios.plugin.config import NagiosPluginConfig

from nagios.plugin.argparser import NagiosPluginArgparseError
from nagios.plugin.argparser import NagiosPluginArgparse

log = logging.getLogger(__name__)

#==============================================================================
class TestNagiosPluginArgparse2(NeedConfig):

    #--------------------------------------------------------------------------
    def test_argparse_add_simple_arg(self):

        log.info("Testing adding a simple argument to a NagiosPluginArgparse object.")
        na = NagiosPluginArgparse(
                usage = '%(prog)s [general_options] -w <warning_level> -c <critical_level>',
                url = 'http://www.profitbricks.com',
                blurb = 'Senseless sample Nagios plugin.',
                licence = '',
        )
        na.add_arg('-w', '--warning', type = int, required = True, metavar = 'LEVEL',
                dest = 'warn', help = "warning threshold")
        na.add_arg('-c', type = int, required = True, metavar = 'LEVEL',
                dest = 'crit', help = "critical threshold")
        na.add_arg('-D', '--device', required = True, metavar = 'DEVICE',
                default = 'sda', dest = 'device',
                help = "The device to check (default: %(default)r)")
        log.debug("NagiosPluginArgparse object: %r", na)
        log.debug("NagiosPluginArgparse object: %s", str(na))

        try:
            na.parse_args(['-h'])
        except FakeExitError as e:
            log.debug("NagiosPluginArgparse exited with exit value %d.", e.exit_value)
            log.debug("Message on exit: >>>%s<<<", e.msg)

    #--------------------------------------------------------------------------
    def test_argparse_perform_args(self):

        log.info("Testing performing arguments by a NagiosPluginArgparse object.")
        na = NagiosPluginArgparse(
                usage = '%(prog)s [options] -w <warning_level> -c <critical_level>',
                url = 'http://www.profitbricks.com',
                blurb = 'Senseless sample Nagios plugin.',
                licence = '',
        )
        na.add_arg('-w', '--warning', type = int, required = True, metavar = 'LEVEL',
                dest = 'warn', help = "warning threshold")
        na.add_arg('-c', '--critical', type = int, required = True, metavar = 'LEVEL',
                dest = 'crit', help = "critical threshold")
        na.add_arg('-D', '--device', required = True, metavar = 'DEVICE',
                default = 'sda', dest = 'device',
                help = "The device to check (default: %(default)r)")
        log.debug("NagiosPluginArgparse object: %r", na)
        log.debug("NagiosPluginArgparse object: %s", str(na))

        na.parse_args(['-w', '10', '-c', '50', '--device', 'sdc'])

        log.debug("Evaluated arguments: %r", na.args)

    #--------------------------------------------------------------------------
    def test_argparse_default_value(self):

        log.info("Testing performing arguments by a NagiosPluginArgparse object.")
        def_val = 'sda'
        na = NagiosPluginArgparse(
                usage = '%(prog)s [options] -D <device>',
                url = 'http://www.profitbricks.com',
                blurb = 'Senseless sample Nagios plugin.',
                licence = '',
        )
        na.add_arg('-D', '--device', required = True, metavar = 'DEVICE',
                default = def_val, dest = 'device',
                help = "The device to check (default: %(default)r)")
        log.debug("NagiosPluginArgparse object: %r", na)

        na.parse_args([])

        log.debug("Got value of argument 'device': %r", na.args.device)
        if na.args.device != def_val:
            self.fail("The value of argument 'device' should be %r, but it is %r." % (
                    def_val, na.args.device))

    #--------------------------------------------------------------------------
    def test_argparse_wo_name(self):

        log.info("Testing adding an argument to a NagiosPluginArgparse object without a name.")
        def_val = 'sda'
        na = NagiosPluginArgparse(
                usage = '%(prog)s [options] -D <device>',
                url = 'http://www.profitbricks.com',
                blurb = 'Senseless sample Nagios plugin.',
                licence = '',
        )
        try:
            na.add_arg(metavar = 'DEVICE', default = def_val, dest = 'device',
                    help = "The device to check (default: %(default)r)")
        except NagiosPluginArgparseError as e:
            log.debug("Correct raised exeption: %s", str(e))
        else:
            self.fail("This should raise a NagiosPluginArgparseError exception.")

    #--------------------------------------------------------------------------
    def test_argparse_wo_dest(self):

        log.info("Testing adding an argument to a NagiosPluginArgparse object without a dest.")
        def_val = 'sda'
        na = NagiosPluginArgparse(
                usage = '%(prog)s [options] -D <device>',
                url = 'http://www.profitbricks.com',
                blurb = 'Senseless sample Nagios plugin.',
                licence = '',
        )
        try:
            na.add_arg('-D', '--device', metavar = 'DEVICE', default = def_val,
                    help = "The device to check (default: %(default)r)")
        except NagiosPluginArgparseError as e:
            log.debug("Correct raised exeption: %s", str(e))
        else:
            self.fail("This should raise a NagiosPluginArgparseError exception.")

    #--------------------------------------------------------------------------
    def test_argparse_doubled_dest(self):

        log.info("Testing adding an argument to a NagiosPluginArgparse object with a doubled dest.")
        def_val = 'sda'
        na = NagiosPluginArgparse(
                usage = '%(prog)s [options] -D <device>',
                url = 'http://www.profitbricks.com',
                blurb = 'Senseless sample Nagios plugin.',
                licence = '',
        )
        try:
            na.add_arg('-D', '--device', metavar = 'DEVICE', default = def_val, dest = 'timeout',
                    help = "The device to check (default: %(default)r)")
        except NagiosPluginArgparseError as e:
            log.debug("Correct raised exeption: %s", str(e))
        else:
            self.fail("This should raise a NagiosPluginArgparseError exception.")

    #--------------------------------------------------------------------------
    def test_argparse_missing_argument(self):

        log.info("Testing missing argument by a NagiosPluginArgparse object.")
        na = NagiosPluginArgparse(
                usage = '%(prog)s [options] -w <warning_level> -c <critical_level> -D <device>',
                url = 'http://www.profitbricks.com',
                blurb = 'Senseless sample Nagios plugin.',
                licence = '',
        )
        na.add_arg('-w', type = int, required = True, metavar = 'LEVEL',
                dest = 'warn', help = "warning threshold")
        na.add_arg('-c', type = int, required = True, metavar = 'LEVEL',
                dest = 'crit', help = "critical threshold")
        na.add_arg('-a', action = 'store_true', dest = 'add',
                help = 'Some senseless additional stuff')
        na.add_arg('-D', '--device', required = True, metavar = 'DEVICE',
                dest = 'device', help = "The device to check")
        log.debug("NagiosPluginArgparse object: %r", na)
        log.debug("NagiosPluginArgparse object: %s", str(na))

        try:
            na.parse_args(['-w', '10', '-c', '50'])
        except FakeExitError as e:
            log.debug("NagiosPluginArgparse exited with exit value %d.", e.exit_value)
            log.debug("Message on exit: >>>%s<<<", e.msg)
            if e.exit_value != nagios.state.unknown:
                self.fail("The exit value is %d, but should be %d." %
                        (e.exit_value, nagios.state.unknown))
        else:
            self.fail("The plugin should be exit with an error message.")

        log.debug("Evaluated arguments: %r", na.args)

#==============================================================================

if __name__ == '__main__':

    verbose = get_arg_verbose()
    init_root_logger(verbose)

    log.info("Starting tests ...")

    loader = unittest.TestLoader()
    suite = unittest.TestSuite()

    suite.addTests(loader.loadTestsFromName(
            'test_argparse_02.TestNagiosPluginArgparse2.test_argparse_add_simple_arg'))
    suite.addTests(loader.loadTestsFromName(
            'test_argparse_02.TestNagiosPluginArgparse2.test_argparse_perform_args'))
    suite.addTests(loader.loadTestsFromName(
            'test_argparse_02.TestNagiosPluginArgparse2.test_argparse_default_value'))
    suite.addTests(loader.loadTestsFromName(
            'test_argparse_02.TestNagiosPluginArgparse2.test_argparse_wo_name'))
    suite.addTests(loader.loadTestsFromName(
            'test_argparse_02.TestNagiosPluginArgparse2.test_argparse_wo_dest'))
    suite.addTests(loader.loadTestsFromName(
            'test_argparse_02.TestNagiosPluginArgparse2.test_argparse_doubled_dest'))
    suite.addTests(loader.loadTestsFromName(
            'test_argparse_02.TestNagiosPluginArgparse2.test_argparse_missing_argument'))

    runner = unittest.TextTestRunner(verbosity = verbose)

    result = runner.run(suite)

#==============================================================================

# vim: tabstop=4 expandtab shiftwidth=4 softtabstop=4 nu
