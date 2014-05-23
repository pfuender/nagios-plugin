#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
@author: Frank Brehm
@contact: frank.brehm@profitbricks.com
@copyright: © 2010 - 2014 by Frank Brehm, Berlin
@summary: Module for CheckPbStorageExportsPlugin class for checking
          correctness of exported and/or not exported volumes
          on ProfitBricks storage servers
"""

# Standard modules
import os
import sys
import re
import logging
import socket
import textwrap
import time
import socket
import uuid
import math
import datetime


from numbers import Number

try:
    import configparser as cfgparser
except ImportError:
    import ConfigParser as cfgparser

# Third party modules

# Own modules

from pb_base.crc import crc64, crc64_digest

import nagios
from nagios import BaseNagiosError

from nagios.common import pp, caller_search_path

from nagios.plugin import NagiosPluginError

from nagios.plugin.range import NagiosRange

from nagios.plugin.threshold import NagiosThreshold

from nagios.plugin.extended import ExtNagiosPluginError
from nagios.plugin.extended import ExecutionTimeoutError
from nagios.plugin.extended import CommandNotFoundError

from nagios.plugin.config import NoConfigfileFound
from nagios.plugin.config import NagiosPluginConfig

from nagios.plugins.base_dcm_client_check import FunctionNotImplementedError
from nagios.plugins.base_dcm_client_check import DEFAULT_TIMEOUT
from nagios.plugins.base_dcm_client_check import STORAGE_CONFIG_DIR, DUMMY_LV
from nagios.plugins.base_dcm_client_check import BaseDcmClientPlugin

from dcmanagerclient.client import RestApiError

#---------------------------------------------
# Some module variables

__version__ = '0.1.0'
__copyright__ = 'Copyright (c) 2014 Frank Brehm, Berlin.'

DEFAULT_WARN_ERRORS = 0
DEFAULT_CRIT_ERRORS = 2

log = logging.getLogger(__name__)

#==============================================================================
class CheckPbStorageExportsPlugin(BaseDcmClientPlugin):
    """
    A special Nagios/Icinga plugin to check the correctness of exported
    and/or not exported volumes on ProfitBricks storage servers.
    The target volumes and mappings from database are get via REST API calls.
    """

    #--------------------------------------------------------------------------
    def __init__(self):
        """
        Constructor of the CheckPbStorageExportsPlugin class.
        """

        failed_commands = []

        usage = """\
                %(prog)s [options] [-H <server_name>] [-c <critical_errors>] [-w <warning_errors>]
                """
        usage = textwrap.dedent(usage).strip()
        usage += '\n       %(prog)s --usage'
        usage += '\n       %(prog)s --help'

        blurb = __copyright__ + "\n\n"
        blurb += ("Checks correctness of exported and/or not exported volumes " +
                    "on ProfitBricks storage servers.")

        self._hostname = socket.gethostname()
        """
        @ivar: the hostname of the current storage server
        @type: str
        """

        super(CheckPbStorageExportsPlugin, self).__init__(
                shortname = 'PB_STORAGE_EXPORTS',
                usage = usage, blurb = blurb,
                version = __version__, timeout = DEFAULT_TIMEOUT,
        )

        self._warning = NagiosRange(DEFAULT_WARN_ERRORS)
        """
        @ivar: the warning threshold of the test, max number of export errors,
               before a warning result is given
        @type: NagiosRange
        """

        self._critical = NagiosRange(DEFAULT_CRIT_ERRORS)
        """
        @ivar: the critical threshold of the test, max number of export errors,
               before a critical result is given
        @type: NagiosRange
        """

        self.all_api_exports = {}
        self.count = {}

        # Some commands are missing
        if failed_commands:
            raise CommandNotFoundError(failed_commands)

    #------------------------------------------------------------
    @property
    def hostname(self):
        """The hostname of the current storage server."""
        return self._hostname

    #------------------------------------------------------------
    @property
    def warning(self):
        """The warning threshold of the test."""
        return self._warning

    #------------------------------------------------------------
    @property
    def critical(self):
        """The critical threshold of the test."""
        return self._critical

    #--------------------------------------------------------------------------
    def as_dict(self):
        """
        Typecasting into a dictionary.

        @return: structure as dict
        @rtype:  dict

        """

        d = super(CheckPbStorageExportsPlugin, self).as_dict()

        d['hostname'] = self.hostname
        d['warning'] = self.warning
        d['critical'] = self.critical

        return d

    #--------------------------------------------------------------------------
    def add_args(self):
        """
        Adding all necessary arguments to the commandline argument parser.
        """

        msg_tpl = ("Generate %s state if the sum of false or wrong exported " +
                "volumes is higher (Default: %%(default)d).")

        msg = msg_tpl % ('warning')
        self.add_arg(
                '-w', '--warning',
                metavar = 'NUMBER',
                dest = 'warning',
                required = True,
                type = int,
                default = DEFAULT_WARN_ERRORS,
                help = msg,
        )

        msg = msg_tpl % ('critical')
        self.add_arg(
                '-c', '--critical',
                metavar = 'NUMBER',
                dest = 'critical',
                type = int,
                required = True,
                default = DEFAULT_CRIT_ERRORS,
                help = msg,
        )

        self.add_arg(
                '-H', '--hostname', '--host',
                metavar = 'NAME',
                dest = 'hostname',
                help = (("The hostname of the current storage server " +
                        "(Default: %r).") % (self.hostname)),
        )

        super(CheckPbStorageExportsPlugin, self).add_args()

    #--------------------------------------------------------------------------
    def parse_args_second(self):
        """
        Evaluates comand line parameters after evaluating the configuration.
        """

        # define Hostname
        hn = self.argparser.args.hostname
        if hn:
            hn = hn.strip()
        if hn:
            self._hostname = hn.lower()

        # define warning level
        if self.argparser.args.warning is not None:
            self._warning = NagiosRange(self.argparser.args.warning)

        # define critical level
        if self.argparser.args.critical is not None:
            self._critical = NagiosRange(self.argparser.args.critical)

        # set thresholds
        self.set_thresholds(
                warning = self.warning,
                critical = self.critical,
        )

    #--------------------------------------------------------------------------
    def read_config(self, cfg):
        """
        Read configuration from an already read in configuration file.

        @param cfg: the already read in nagion configuration
        @type cfg: NagiosPluginConfig

        """

        if cfg.has_section('general'):
            hostname = None
            if cfg.has_option('general', 'hostname'):
                hostname = cfg.get('general', 'hostname')
            if hostname:
                hostname = hostname.strip()
            if hostname:
                if self.verbose > 1:
                    log.debug("Got a hostname from config: %r", hostname)
                self._hostname = hostname

            vg = None
            if cfg.has_option('general', 'volumegroup'):
                vg = cfg.get('general', 'volumegroup')
            if vg:
                vg = vg.strip()
            if vg:
                if self.verbose > 1:
                    log.debug("Got a volume group from config: %r", vg)
                self._pb_vg = vg

    #--------------------------------------------------------------------------
    def run(self):
        """Main execution method."""

        state = nagios.state.ok
        out = "Storage exports on %r seems to be okay." % (
                self.hostname)

        self.all_api_exports = {}

        self.count = {
                'total': 0,
                'missing': 0,
                'alien': 0,
                'orphans': 0,
                'zombies': 0,
                'snapshots': 0,
                'ok': 0,
                'dummy': 0,
                'error': 0,
        }

        self.exit(state, out)

#==============================================================================

if __name__ == "__main__":

    pass

#==============================================================================

# vim: fileencoding=utf-8 filetype=python ts=4 et sw=4
