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
        log.debug("NagiosPluginArgparse object: %r", plugin)
        log.debug("NagiosPluginArgparse object: %s", str(plugin))

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

    runner = unittest.TextTestRunner(verbosity = verbose)

    result = runner.run(suite)

#==============================================================================

# vim: tabstop=4 expandtab shiftwidth=4 softtabstop=4 nu
