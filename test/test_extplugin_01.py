#!/usr/bin/env python
# -*- coding: utf-8 -*-
'''
@author: Frank Brehm
@contact: frank.brehm@profitbricks.com
@organization: Profitbricks GmbH
@copyright: © 2010-2013 by Profitbricks GmbH
@license: GPL3
@summary: test script (and module) for unit tests on ExtNagiosPlugin objects
'''

import unittest
import os
import sys
import logging
import tempfile

from collections import OrderedDict

libdir = os.path.abspath(os.path.join(os.path.dirname(sys.argv[0]), '..'))
sys.path.insert(0, libdir)

import general
from general import ColoredFormatter, get_arg_verbose, init_root_logger
from general import NeedConfig, NeedTmpConfig

import nagios
from nagios import FakeExitError

from nagios.plugin import NagiosPluginError

from nagios.plugins import ExtNagiosPluginError
from nagios.plugins import CommandNotFoundError
from nagios.plugins import ExecutionTimeoutError
from nagios.plugins import ExtNagiosPlugin

from nagios.plugin.threshold import NagiosThreshold

from nagios.plugin.config import NoConfigfileFound

log = logging.getLogger(__name__)

#==============================================================================
class TestExtNagiosPlugin(NeedConfig):

    #--------------------------------------------------------------------------
    def setUp(self):
        pass

    #--------------------------------------------------------------------------
    def test_plugin_object(self):

        log.info("Testing ExtNagiosPlugin object.")
        plugin = ExtNagiosPlugin(
                usage = '%(prog)s --hello',
                url = 'http://www.profitbricks.com',
                blurb = 'Senseless sample Nagios plugin.',
                licence = 'Licence: GNU Lesser General Public License (LGPL), Version 3',
                extra = 'Bla blub',
                verbose = self.verbose,
        )
        plugin.add_perfdata('bla', 10, 'MByte', warning = '20', critical = '30')
        plugin.set_thresholds(warning = '10:25', critical = "~:25")
        plugin.add_message(nagios.state.ok, 'bli', 'bla')
        plugin.add_message('warning', 'blub')
        log.debug("ExtNagiosPlugin object: %r", plugin)
        log.debug("ExtNagiosPlugin object: %s", str(plugin))

    #--------------------------------------------------------------------------
    def test_prepend_search_path(self):

        log.info("Testing Prepending a path to the search path.")

        tmpdir = tempfile.mkdtemp()

        try:

            tdir_real = os.path.realpath(tmpdir)
            tdir_rel = os.path.relpath(tmpdir)
            log.debug("Using %r for prepending to search path.", tdir_rel)

            plugin = ExtNagiosPlugin(
                    usage = '%(prog)s --hello',
                    url = 'http://www.profitbricks.com',
                    blurb = 'Senseless sample Nagios plugin.',
                    licence = 'Licence: GNU Lesser General Public License (LGPL), Version 3',
                    extra = 'Bla blub',
                    verbose = self.verbose,
                    prepend_searchpath = tdir_rel,
            )
            log.debug("ExtNagiosPlugin object: %r", plugin)
            log.debug("ExtNagiosPlugin object: %s", str(plugin))
            log.debug("Got as first search path: %r", plugin.search_path[0])
            self.assertEqual(tdir_real, plugin.search_path[0])

        finally:

            os.rmdir(tmpdir)

    #--------------------------------------------------------------------------
    def test_append_search_path(self):

        log.info("Testing appending a path to the search path.")

        tmpdir = tempfile.mkdtemp()

        try:

            tdir_real = os.path.realpath(tmpdir)
            tdir_rel = os.path.relpath(tmpdir)
            log.debug("Using %r for appending to search path.", tdir_rel)

            plugin = ExtNagiosPlugin(
                    usage = '%(prog)s --hello',
                    url = 'http://www.profitbricks.com',
                    blurb = 'Senseless sample Nagios plugin.',
                    licence = 'Licence: GNU Lesser General Public License (LGPL), Version 3',
                    extra = 'Bla blub',
                    verbose = self.verbose,
                    append_searchpath = tdir_rel,
            )
            log.debug("ExtNagiosPlugin object: %r", plugin)
            log.debug("ExtNagiosPlugin object: %s", str(plugin))
            log.debug("Got as last search path: %r", plugin.search_path[-1])
            self.assertEqual(tdir_real, plugin.search_path[-1])

        finally:

            os.rmdir(tmpdir)

#==============================================================================

if __name__ == '__main__':

    verbose = get_arg_verbose()
    if verbose is None:
        verbose = 0
    init_root_logger(verbose)

    log.info("Starting tests ...")

    loader = unittest.TestLoader()
    suite = unittest.TestSuite()

    suite.addTest(TestExtNagiosPlugin('test_plugin_object', verbose))
    suite.addTest(TestExtNagiosPlugin('test_prepend_search_path', verbose))
    suite.addTest(TestExtNagiosPlugin('test_append_search_path', verbose))

    runner = unittest.TextTestRunner(verbosity = verbose)

    result = runner.run(suite)

#==============================================================================

# vim: tabstop=4 expandtab shiftwidth=4 softtabstop=4 nu
