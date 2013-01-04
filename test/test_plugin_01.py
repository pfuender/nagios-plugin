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

    #--------------------------------------------------------------------------
    def test_plugin_object_props(self):

        log.info("Testing NagiosPlugin object properties.")

        plugin = NagiosPlugin()

        if not isinstance(plugin, NagiosPlugin):
            self.fail("Not a NagiosPlugin object: %r" % (plugin))

        log.debug("Setting shortname explicitly to 'PAGESIZE'.")
        plugin.shortname = "PAGESIZE"
        self.assertEqual(plugin.shortname, "PAGESIZE")

        log.debug("Resetting plugin to default.")
        plugin = NagiosPlugin()
        self.assertEqual(plugin.shortname, "TEST_PLUGIN_01")

        log.debug("Creating plugin with a shortname 'SIZE' on init.")
        plugin = NagiosPlugin(shortname = 'SIZE')
        self.assertEqual(plugin.shortname, "SIZE")

        log.debug("Creating plugin with a plugin name 'check_stuff'")
        plugin = NagiosPlugin(plugin = 'check_stuff')
        self.assertEqual(plugin.shortname, "STUFF")

        log.debug("Creating plugin with a shortname 'SIZE' and a plugin " +
                "name 'check_stuff' on init.")
        plugin = NagiosPlugin(shortname = 'SIZE', plugin = 'check_stuff')
        self.assertEqual(plugin.shortname, "SIZE")

        log.debug("Setting thresholds to warn if < 10, critical if > 25.")
        t = plugin.set_thresholds(warning = "10:25", critical = "~:25")
        if not isinstance(t, NagiosThreshold):
            self.fail("Not a NagiosThreshold object: %r" % (t))

        log.debug("Adding performance data size ...")
        plugin.add_perfdata(
                label = "size", value = 1, uom = "kB", threshold = t
        )
        pdata = plugin.all_perfoutput()
        log.debug("Got performance data: %r", pdata)
        self.assertEqual(pdata, 'size=1kB;10:25;~:25')

        log.debug("Adding performance data time ...")
        plugin.add_perfdata(label = "time", value = 3.52, threshold = t)
        pdata = plugin.all_perfoutput()
        log.debug("Got performance data: %r", pdata)
        self.assertEqual(pdata, 'size=1kB;10:25;~:25 time=3.52;10:25;~:25')

    #--------------------------------------------------------------------------
    def test_plugin_threshold_checks(self):

        log.info("Testing plugin threshold checks ...")

        plugin = NagiosPlugin(shortname = 'SIZE', plugin = 'check_stuff')
        log.debug("Setting thresholds to warn if < 10, critical if > 25.")
        t = plugin.set_thresholds(warning = "10:25", critical = "~:25")

        expected_results = OrderedDict()
        expected_results[-1] = nagios.state.warning
        expected_results[1] = nagios.state.warning
        expected_results[20] = nagios.state.ok
        expected_results[25] = nagios.state.ok
        expected_results[26] = nagios.state.critical
        expected_results[30] = nagios.state.critical

        for value in expected_results.keys():
            ecpected_result = expected_results[value]
            got_result = t.get_status(value)
            log.debug("Checking value %d, expect result %d, got result %d.",
                    value, ecpected_result, got_result)
            self.assertEqual(got_result, ecpected_result)

#==============================================================================

if __name__ == '__main__':

    verbose = get_arg_verbose()
    init_root_logger(verbose)

    log.info("Starting tests ...")

    loader = unittest.TestLoader()
    suite = unittest.TestSuite()

    suite.addTests(loader.loadTestsFromName(
            'test_plugin_01.TestNagiosPlugin.test_plugin_object'))
    suite.addTests(loader.loadTestsFromName(
            'test_plugin_01.TestNagiosPlugin.test_plugin_object_props'))
    suite.addTests(loader.loadTestsFromName(
            'test_plugin_01.TestNagiosPlugin.test_plugin_threshold_checks'))

    runner = unittest.TextTestRunner(verbosity = verbose)

    result = runner.run(suite)

#==============================================================================

# vim: tabstop=4 expandtab shiftwidth=4 softtabstop=4 nu
