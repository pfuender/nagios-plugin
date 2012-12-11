#!/usr/bin/env python
# -*- coding: utf-8 -*-
'''
@author: Frank Brehm
@contact: frank.brehm@profitbricks.com
@organization: Profitbricks GmbH
@copyright: (c) 2010-2012 by Profitbricks GmbH
@license: GPL3
@summary: test script (and module) for unit tests on NagiosGetopt
          and NagiosPluginConfig objects
'''

import unittest
import os
import sys
import logging
import tempfile

libdir = os.path.abspath(os.path.join(os.path.dirname(sys.argv[0]), '..'))
sys.path.insert(0, libdir)

import general

from general import ColoredFormatter, pp, get_arg_verbose, init_root_logger

import nagios
from nagios.plugin.config import NoConfigfileFound
from nagios.plugin.config import NagiosPluginConfig

log = logging.getLogger(__name__)

#==============================================================================
class NeedConfig(unittest.TestCase):

    #--------------------------------------------------------------------------
    def setUp(self):
        bdir = os.path.realpath(os.path.dirname(sys.argv[0]))
        self.test_dir = os.path.join(bdir, 'npg03')
        if not os.path.isdir(self.test_dir):
            raise RuntimeError("Directory %r doesn't exists." % (self.test_dir))
        self.ini_file = os.path.join(self.test_dir, 'plugins.ini')
        if not os.path.isfile(self.ini_file):
            raise RuntimeError("File %r doesn't exists." % (self.ini_file))

        bogus = os.sep + os.path.join('random', 'bogus', 'path')
        os.environ['NAGIOS_CONFIG_PATH'] = bogus + ':' + self.test_dir

#==============================================================================
class NeedTmpConfig(NeedConfig):

    #--------------------------------------------------------------------------
    def setUp(self):

        super(NeedTmpConfig, self).setUp()

        (fd, self.tmp_cfg, ) = tempfile.mkstemp(
                prefix = "temp-plugins-", suffix =  '.ini')

        log.debug("Creating temp configfile %r ...", self.tmp_cfg)
        f = os.fdopen(fd, 'w')
        f.write("[silly_options]\n")
        f.write("uhu1 = banane 1\n")
        f.write("uhu2 = \" Banane 2\"\n")
        f.write("\n")
        f.close()

    #--------------------------------------------------------------------------
    def tearDown(self):

        log.debug("Removing temp configfile %r ...", self.tmp_cfg)
        os.remove(self.tmp_cfg)

#==============================================================================
class TestNagiosPluginConfig(NeedConfig):

    #--------------------------------------------------------------------------
    def test_config_object(self):

        log.info("Testing NagiosPluginConfig object.")
        try:
            cfg = NagiosPluginConfig()
            log.debug("NagiosPluginConfig object: %r", cfg)
        except Exception, e:
            self.fail("Could not instatiate NagiosPluginConfig by a %s: %s" % (
                    e.__class__.__name__, str(e)))

    #--------------------------------------------------------------------------
    def test_read_default_paths(self):

        log.info("Testing read default config paths.")
        try:
            cfg = NagiosPluginConfig()
            configs = cfg.read()
            log.debug("Read configuration files:\n%s", pp(configs))
            c = {}
            for section in cfg.sections():
                if not section in c:
                    c[section] = {}
                for option in cfg.options(section):
                    val = cfg.get(section, option)
                    c[section][option] = val
            log.debug("Found options in config:\n%s", pp(c))
        except NoConfigfileFound, e:
            self.fail("Could not read NagiosPluginConfig by a %s: %s" % (
                    e.__class__.__name__, str(e)))

#==============================================================================
class TesttNagiosPluginConfigFile(NeedTmpConfig):

    #--------------------------------------------------------------------------
    def test_read_cfgfile(self):

        log.info("Testing read temp configfile %r.", self.tmp_cfg)
        try:
            cfg = NagiosPluginConfig()
            configs = cfg.read(self.tmp_cfg)
            log.debug("Read configuration files:\n%s", pp(configs))
            c = {}
            for section in cfg.sections():
                if not section in c:
                    c[section] = {}
                for option in cfg.options(section):
                    val = cfg.get(section, option)
                    c[section][option] = val
            log.debug("Found options in config:\n%s", pp(c))
        except NoConfigfileFound, e:
            self.fail("Could not read NagiosPluginConfig by a %s: %s" % (
                    e.__class__.__name__, str(e)))

#==============================================================================

if __name__ == '__main__':


    verbose = get_arg_verbose()
    init_root_logger(verbose)

    log.info("Starting tests ...")

    loader = unittest.TestLoader()
    suite = unittest.TestSuite()

    suite.addTests(loader.loadTestsFromName(
            'test_getopt_03.TestNagiosPluginConfig.test_config_object'))
    suite.addTests(loader.loadTestsFromName(
            'test_getopt_03.TestNagiosPluginConfig.test_read_default_paths'))
    suite.addTests(loader.loadTestsFromName(
            'test_getopt_03.TesttNagiosPluginConfigFile.test_read_cfgfile'))

    runner = unittest.TextTestRunner(verbosity = verbose)

    result = runner.run(suite)

#==============================================================================

# vim: tabstop=4 expandtab shiftwidth=4 softtabstop=4 nu
