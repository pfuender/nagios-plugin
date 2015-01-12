#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@author: Frank Brehm
@contact: frank.brehm@profitbricks.com
@organization: Profitbricks GmbH
@copyright: © 2010 - 2015 by Profitbricks GmbH
@license: GPL3
@summary: test script (and module) for unit tests on NagiosPluginArgparse
          and NagiosPluginConfig objects
"""

import unittest
import os
import sys
import logging

libdir = os.path.abspath(os.path.join(os.path.dirname(sys.argv[0]), '..'))
sys.path.insert(0, libdir)

import general
from general import ColoredFormatter, get_arg_verbose, init_root_logger
from general import NeedConfig, NeedTmpConfig

log = logging.getLogger(__name__)

#==============================================================================
class TestNagiosPluginArgparse(NeedConfig):

    #--------------------------------------------------------------------------
    def test_import_modules(self):

        log.info("Test importing all appropriate modules ...")

        log.debug("Importing module %r ...", "nagios")
        import nagios

        log.debug("Importing %r from %r ...", 'FakeExitError', 'nagios')
        from nagios import FakeExitError

        log.debug("Importing %r from %r ...", 'NoConfigfileFound', 'nagios.plugin.config')
        from nagios.plugin.config import NoConfigfileFound

        log.debug("Importing %r from %r ...", 'NagiosPluginConfig', 'nagios.plugin.config')
        from nagios.plugin.config import NagiosPluginConfig

        log.debug("Importing %r from %r ...", 'NagiosPluginArgparse', 'nagios.plugin.argparser')
        from nagios.plugin.argparser import NagiosPluginArgparse

    #--------------------------------------------------------------------------
    def test_argparse_object(self):

        log.info("Testing NagiosPluginArgparse object.")

        import nagios
        from nagios.plugin.argparser import NagiosPluginArgparse

        na = NagiosPluginArgparse(
                usage = '%(prog)s --hello',
                url = 'http://www.profitbricks.com',
                blurb = 'Senseless sample Nagios plugin.',
                extra = 'Bla blub',
        )
        log.debug("NagiosPluginArgparse object: %r", na)
        log.debug("NagiosPluginArgparse object: %s", str(na))

    #--------------------------------------------------------------------------
    def test_argparse_show_version(self):

        log.info("Testing NagiosPluginArgparse showing version.")

        import nagios
        from nagios import FakeExitError
        from nagios.plugin.argparser import NagiosPluginArgparse

        na = NagiosPluginArgparse(
                usage = '%(prog)s --version',
                url = 'http://www.profitbricks.com',
                blurb = 'Senseless sample Nagios plugin.',
                extra = 'Bla blub',
        )

        try:
            na.parse_args(['--version'])
        except FakeExitError as e:
            log.debug("NagiosPluginArgparse exited with exit value %d.", e.exit_value)
            log.debug("Message on exit: >>>%s<<<", e.msg)

    #--------------------------------------------------------------------------
    def test_argparse_show_usage(self):

        log.info("Testing NagiosPluginArgparse showing usage.")

        import nagios
        from nagios import FakeExitError
        from nagios.plugin.argparser import NagiosPluginArgparse

        na = NagiosPluginArgparse(
                usage = '%(prog)s --version',
                url = 'http://www.profitbricks.com',
                blurb = 'Senseless sample Nagios plugin.',
                extra = 'Bla blub',
        )

        try:
            na.parse_args(['--usage'])
        except FakeExitError as e:
            log.debug("NagiosPluginArgparse exited with exit value %d.", e.exit_value)
            log.debug("Message on exit: >>>%s<<<", e.msg)

    #--------------------------------------------------------------------------
    def test_argparse_parse_help(self):

        log.info("Testing NagiosPluginArgparse generating help.")

        import nagios
        from nagios import FakeExitError
        from nagios.plugin.argparser import NagiosPluginArgparse

        na = NagiosPluginArgparse(
                usage = '%(prog)s --help',
                url = 'http://www.profitbricks.com',
                blurb = 'Senseless sample Nagios plugin.',
                extra = 'Bla blub\n\nblubber blub',
                licence = 'Licence: GNU Lesser General Public License (LGPL), Version 3',
        )

        try:
            na.parse_args(['-h'])
        except FakeExitError as e:
            log.debug("NagiosPluginArgparse exited with exit value %d.", e.exit_value)
            log.debug("Message on exit: >>>%s<<<", e.msg)

    #--------------------------------------------------------------------------
    def test_argparse_wrong_argument(self):

        log.info("Testing NagiosPluginArgparse for a wrong argument.")

        import nagios
        from nagios import FakeExitError
        from nagios.plugin.argparser import NagiosPluginArgparse

        na = NagiosPluginArgparse(
                usage = '%(prog)s',
                url = 'http://www.profitbricks.com',
                blurb = 'Senseless sample Nagios plugin.',
                licence = '',
        )

        try:
            na.parse_args(['--bli-bla-blub'])
        except FakeExitError as e:
            log.debug("NagiosPluginArgparse exited with exit value %d.", e.exit_value)
            log.debug("Message on exit: >>>%s<<<", e.msg)

#==============================================================================

if __name__ == '__main__':

    verbose = get_arg_verbose()
    if verbose is None:
        verbose = 0
    init_root_logger(verbose)

    log.info("Starting tests ...")

    suite = unittest.TestSuite()

    suite.addTest(TestNagiosPluginArgparse('test_import_modules', verbose))
    suite.addTest(TestNagiosPluginArgparse('test_argparse_object', verbose))
    suite.addTest(TestNagiosPluginArgparse('test_argparse_show_version', verbose))
    suite.addTest(TestNagiosPluginArgparse('test_argparse_show_usage', verbose))
    suite.addTest(TestNagiosPluginArgparse('test_argparse_parse_help', verbose))
    suite.addTest(TestNagiosPluginArgparse('test_argparse_wrong_argument', verbose))

    runner = unittest.TextTestRunner(verbosity = verbose)

    result = runner.run(suite)

#==============================================================================

# vim: tabstop=4 expandtab shiftwidth=4 softtabstop=4
