#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@author: Frank Brehm
@contact: frank.brehm@profitbricks.com
@organization: Profitbricks GmbH
@copyright: © 2010 - 2015 by Profitbricks GmbH
@license: GPL3
@summary: general used functions an objects used for unit tests on nagios
          plugin framework
"""

import unittest
import os
import sys
import logging
import tempfile
import argparse

import nagios
import nagios.plugin.functions

from nagios import FakeExitError

from nagios.color_syslog import ColoredFormatter

#==============================================================================

log = logging.getLogger(__name__)

#==============================================================================
def get_arg_verbose():

    arg_parser = argparse.ArgumentParser()

    arg_parser = argparse.ArgumentParser()
    arg_parser.add_argument("-v", "--verbose", action = "count",
            dest = 'verbose', help = 'Increase the verbosity level')
    args = arg_parser.parse_args()

    return args.verbose

#==============================================================================
def init_root_logger(verbose = 0):

    root_log = logging.getLogger()
    root_log.setLevel(logging.WARNING)
    if verbose:
        if verbose > 1:
            root_log.setLevel(logging.DEBUG)
        else:
            root_log.setLevel(logging.INFO)

    appname = os.path.basename(sys.argv[0])
    format_str = appname + ': '
    if verbose:
        if verbose > 1:
            format_str += '%(name)s(%(lineno)d) %(funcName)s() '
        else:
            format_str += '%(name)s '
    format_str += '%(levelname)s - %(message)s'
    formatter = None
    formatter = ColoredFormatter(format_str)

    # create log handler for console output
    lh_console = logging.StreamHandler(sys.stderr)
    if verbose:
        lh_console.setLevel(logging.DEBUG)
    else:
        lh_console.setLevel(logging.INFO)
    lh_console.setFormatter(formatter)

    root_log.addHandler(lh_console)

#==============================================================================
class NagiosPluginTestcase(unittest.TestCase):

    #--------------------------------------------------------------------------
    def __init__(self, methodName = 'runTest', verbose = 0):

        self._verbose = int(verbose)

        super(NagiosPluginTestcase, self).__init__(methodName)

    #--------------------------------------------------------------------------
    @property
    def verbose(self):
        """The verbosity level."""
        return getattr(self, '_verbose', 0)

    #--------------------------------------------------------------------------
    def setUp(self):
        pass

    #--------------------------------------------------------------------------
    def tearDown(self):
        pass

#==============================================================================
class NeedConfig(NagiosPluginTestcase):

    #--------------------------------------------------------------------------
    @property
    def verbose(self):
        """The verbosity level."""
        return getattr(self, '_verbose', 0)

    #--------------------------------------------------------------------------
    def setUp(self):

        nagios.plugin.functions._fake_exit = True

        bdir = os.path.realpath(os.path.dirname(sys.argv[0]))
        self.test_dir = os.path.join(bdir, 'npg03')
        if not os.path.isdir(self.test_dir):
            raise RuntimeError("Directory %r doesn't exists." % (self.test_dir))
        self.ini_file = os.path.join(self.test_dir, 'plugins.ini')
        if not os.path.isfile(self.ini_file):
            raise RuntimeError("File %r doesn't exists." % (self.ini_file))

        bogus = os.sep + os.path.join('random', 'bogus', 'path')
        os.environ['NAGIOS_CONFIG_PATH'] = bogus + ':' + self.test_dir

    #--------------------------------------------------------------------------
    def tearDown(self):
        pass

#==============================================================================
class NeedTmpConfig(NeedConfig):

    #--------------------------------------------------------------------------
    def setUp(self):

        super(NeedTmpConfig, self).setUp()

        if self.verbose > 1:
            log.debug("Creating a temporary config file ...")
        (fd, self.tmp_cfg, ) = tempfile.mkstemp(
                prefix = "temp-plugins-", suffix =  '.ini')

        if self.verbose > 2:
            log.debug("Creating temp configfile %r ...", self.tmp_cfg)
        f = os.fdopen(fd, 'w')
        f.write("[silly_options]\n")
        f.write("uhu1 = banane 1\n")
        f.write("uhu2 = \" Banane 2\"\n")
        f.write("\n")
        f.close()

    #--------------------------------------------------------------------------
    def tearDown(self):

        if self.verbose > 2:
            log.debug("Removing temporary configfile %r ...", self.tmp_cfg)
        os.remove(self.tmp_cfg)

#==============================================================================

if __name__ == '__main__':

    pass

#==============================================================================

# vim: tabstop=4 expandtab shiftwidth=4 softtabstop=4
