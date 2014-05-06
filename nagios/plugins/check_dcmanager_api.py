#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
@author: Frank Brehm
@contact: frank.brehm@profitbricks.com
@copyright: © 2010 - 2014 by Frank Brehm, Berlin
@summary: Module for CheckDcmanagerApiPlugin class for checking
          ability of the DcManager API
"""

# Standard modules
import os
import sys
import re
import logging
import textwrap
import time

from numbers import Number

# Third party modules

# Own modules

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
from nagios.plugins.base_dcm_client_check import BaseDcmClientPlugin

from dcmanagerclient.client import RestApiError

#---------------------------------------------
# Some module variables

__version__ = '0.2.0'
__copyright__ = 'Copyright (c) 2014 Frank Brehm, Berlin.'

DEFAULT_TIMEOUT = 60

DEFAULT_WARN_TIME = 10.0
DEFAULT_CRIT_TIME = 20.0

log = logging.getLogger(__name__)

#==============================================================================
class CheckDcmanagerApiPlugin(BaseDcmClientPlugin):
    """
    A special Nagios/Icinga plugin to check the ability of the
    DcManager API.
    """

    #--------------------------------------------------------------------------
    def __init__(self):
        """
        Constructor of the CheckDcmanagerApiPlugin class.
        """

        usage = """\
                %(prog)s [options] [--api-url <api_url>] [-c <critical_time>] [-w <warning_time>]
                """
        usage = textwrap.dedent(usage).strip()
        usage += '\n       %(prog)s --usage'
        usage += '\n       %(prog)s --help'

        blurb = __copyright__ + "\n\n"
        blurb += "Checks the ability of the DcManager API."

        super(CheckDcmanagerApiPlugin, self).__init__(
                shortname = 'PB_DCM_API',
                usage = usage, blurb = blurb,
                version = __version__, timeout = DEFAULT_TIMEOUT,
        )

        self._warning = NagiosRange(start = 0.0, end = DEFAULT_WARN_TIME)
        """
        @ivar: the warning threshold of the test, the maximum time for a reply
               before a warning result is given
        @type: NagiosRange
        """

        self._critical = NagiosRange(start = 0.0, end = DEFAULT_CRIT_TIME)
        """
        @ivar: the critical threshold of the test, the maximum time for a reply
               before a critical result is given
        @type: NagiosRange
        """

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

        d = super(CheckDcmanagerApiPlugin, self).as_dict()
        d['warning'] = self.warning
        d['critical'] = self.critical

        return d

    #--------------------------------------------------------------------------
    def add_args(self):
        """
        Adding all necessary arguments to the commandline argument parser.
        """

        msg_tpl = ("Generate %s state if the response time of the DcManager API " +
                "is higher (Default: %%(default)0.1f seconds).")

        msg = msg_tpl % ('warning')
        self.add_arg(
                '-w', '--warning',
                metavar = 'SECONDS',
                dest = 'warning',
                required = True,
                type = Number,
                default = DEFAULT_WARN_TIME,
                help = msg,
        )

        msg = msg_tpl % ('critical')
        self.add_arg(
                '-c', '--critical',
                metavar = 'SECONDS',
                dest = 'critical',
                type = Number,
                required = True,
                default = DEFAULT_CRIT_TIME,
                help = msg,
        )

        super(CheckDcmanagerApiPlugin, self).add_args()

    #--------------------------------------------------------------------------
    def parse_args_second(self):
        """
        Method to evaluate command line parameters after evaluating
        the configuration.
        """

        # define warning level
        if self.argparser.args.warning is not None:
            self._warning = NagiosRange(start = 0.0, end = self.argparser.args.warning)

        # define critical level
        if self.argparser.args.critical is not None:
            self._critical = NagiosRange(start = 0.0, end = self.argparser.args.critical)

        # set thresholds
        self.set_thresholds(
                warning = self.warning,
                critical = self.critical,
        )

    #--------------------------------------------------------------------------
    def run(self):
        """Main execution method."""

        state = nagios.state.ok
        out = "DcManager API %r seems to be okay." % (
                self.api.url)

        end_time = None
        start_time = time.time()
        try:
            clusters = self.api.clusters()
        except RestApiError as e:
            state = nagios.state.critical
            self.exit(state, str(e))

        end_time = time.time()
        duration = end_time - start_time

        nr_clusters = len(clusters)
        state = self.threshold.get_status(duration)
        self.add_perfdata(label = 'resp_time', uom = 's', value = duration,
                threshold = self.threshold)
        out = "Response time of DcManager API %r: %0.2f sec, found %d clusters." % (
                self.api.url, duration, nr_clusters)

        self.exit(state, out)

#==============================================================================

if __name__ == "__main__":

    pass

#==============================================================================

# vim: fileencoding=utf-8 filetype=python ts=4 et sw=4
