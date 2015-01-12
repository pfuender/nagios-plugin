#!/usr/bin/env python
# -*- coding: utf-8 -*-
'''
@author: Frank Brehm
@contact: frank.brehm@profitbricks.com
@organization: Profitbricks GmbH
@copyright: © 2010 - 2015 by Profitbricks GmbH
@license: GPL3
@summary: test script (and module) for unit tests on NagiosPlugin objects
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
from nagios.plugin import NagiosPlugin

from nagios.plugin.threshold import NagiosThreshold

from nagios.plugin.config import NoConfigfileFound

log = logging.getLogger(__name__)

TEST_CONTENT = "Hello world!\n"

#==============================================================================
class TestNagiosPlugin(NeedConfig):

    #--------------------------------------------------------------------------
    def setUp(self):

        if self.verbose > 2:
            log.debug("Setting up a TestNagiosPlugin object ...")
        super(TestNagiosPlugin, self).setUp()

        if self.verbose > 1:
            log.debug("Creating a temporary file for reading ...")
        (fd, self.tmp_file, ) = tempfile.mkstemp(
                prefix = "temp-", suffix =  '.txt')
        if self.verbose > 2:
            log.debug("Writing temporary file %r ...", self.tmp_file)

        f = os.fdopen(fd, 'w')
        f.write(TEST_CONTENT)
        f.close()

        pass

    #--------------------------------------------------------------------------
    def tearDown(self):

        if self.verbose > 2:
            log.debug("Tearing down the TestNagiosPlugin object ...")
        super(TestNagiosPlugin, self).tearDown()

        if os.path.exists(self.tmp_file):
            if self.verbose > 2:
                log.debug("Removing temporary file %r ...", self.tmp_file)
            os.remove(self.tmp_file)

        pass

    #--------------------------------------------------------------------------
    def test_read_file(self):

        log.info("Testing reading a file by a Nagios plugin.")
        plugin = NagiosPlugin(
                usage = '%(prog)s --hello',
                url = 'http://www.profitbricks.com',
                blurb = 'Sample Nagios plugin for reading a file.',
                licence = 'Licence: GNU Lesser General Public License (LGPL), Version 3',
                extra = 'Bla blub',
        )
        if self.verbose > 3:
            log.debug("NagiosPluginArgparse object: %s", str(plugin))
        log.debug("Reading file %r ...", self.tmp_file)
        content = plugin.read_file(self.tmp_file)
        self.assertEqual(content, TEST_CONTENT)

    #--------------------------------------------------------------------------
    @unittest.skipIf(os.geteuid() == 0, "No sense to perform this as root.")
    def test_no_permissions(self):

        log.info("Testing trying to read a file without permissions.")
        plugin = NagiosPlugin(
                usage = '%(prog)s --hello',
                url = 'http://www.profitbricks.com',
                blurb = 'Sample Nagios plugin for reading a file.',
                licence = 'Licence: GNU Lesser General Public License (LGPL), Version 3',
                extra = 'Bla blub',
        )
        if self.verbose > 3:
            log.debug("NagiosPluginArgparse object: %s", str(plugin))
        log.debug("Chmod 000 to %r ...", self.tmp_file)
        os.chmod(self.tmp_file, 0)
        log.debug("Reading file %r ...", self.tmp_file)
        with self.assertRaises(IOError) as cm:
            content = plugin.read_file(self.tmp_file)
        e = cm.exception
        log.debug("%s raised on read_file() with a file without permissions: %s",
                e.__class__.__name__, e)

    #--------------------------------------------------------------------------
    def test_read_non_existing(self):

        log.info("Testing trying to read a non existing file.")
        plugin = NagiosPlugin(
                usage = '%(prog)s --hello',
                url = 'http://www.profitbricks.com',
                blurb = 'Sample Nagios plugin for reading a file.',
                licence = 'Licence: GNU Lesser General Public License (LGPL), Version 3',
                extra = 'Bla blub',
        )
        if self.verbose > 3:
            log.debug("NagiosPluginArgparse object: %s", str(plugin))
        log.debug("Removing %r ...", self.tmp_file)
        os.remove(self.tmp_file)
        log.debug("Reading file %r ...", self.tmp_file)
        with self.assertRaises(IOError) as cm:
            content = plugin.read_file(self.tmp_file)
        e = cm.exception
        log.debug("%s raised on read_file() with a non existing file: %s",
                e.__class__.__name__, e)

#==============================================================================

if __name__ == '__main__':

    verbose = get_arg_verbose()
    if verbose is None:
        verbose = 0
    init_root_logger(verbose)

    log.info("Starting tests ...")

    suite = unittest.TestSuite()

    suite.addTest(TestNagiosPlugin('test_read_file', verbose))
    suite.addTest(TestNagiosPlugin('test_no_permissions', verbose))
    suite.addTest(TestNagiosPlugin('test_read_non_existing', verbose))

    runner = unittest.TextTestRunner(verbosity = verbose)

    result = runner.run(suite)

#==============================================================================

# vim: tabstop=4 expandtab shiftwidth=4 softtabstop=4
