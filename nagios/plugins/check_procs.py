#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
@author: Frank Brehm
@contact: frank.brehm@profitbricks.com
@copyright: © 2010 - 2013 by Frank Brehm, Berlin
@summary: Module for CheckProcsPlugin class
"""

# Standard modules
import os
import sys
import logging
import textwrap

# Third party modules

# Own modules

import nagios
from nagios import BaseNagiosError

from nagios.common import pp, caller_search_path

from nagios.plugin import NagiosPluginError

from nagios.plugin.range import NagiosRange

from nagios.plugins import ExtNagiosPluginError
from nagios.plugins import CommandNotFoundError
from nagios.plugins import ExtNagiosPlugin

#---------------------------------------------
# Some module variables

__version__ = '0.2.0'

log = logging.getLogger(__name__)
PS_CMD = os.sep + os.path.join('bin', 'ps')

valid_metrics = ['PROCS', 'VSZ', 'RSS', 'CPU', 'ELAPSED']

#==============================================================================
class CheckProcsPlugin(ExtNagiosPlugin):
    """
    A special NagiosPlugin class for checking a running process.
    """

    #--------------------------------------------------------------------------
    def __init__(self):
        """
        Constructor of the CheckProcsPlugin class.
        """

        failed_commands = []

        usage = """\
        %(prog)s [-v] [-t <timeout>] [-c <critical_threshold>] [-w <warning_threshold>]
                   [-m <metric>] [-s <statusflags>] [--ps-cmd <command>]
                   [--ppid <parent_pid>] [--rss <value>] [--pcpu <value>] [--vsz <value>]
                   [--user <user_id>] [-a <args>] [-C <command>] [--init]
        %(prog)s --usage
        %(prog)s --help
        """
        usage = textwrap.dedent(usage).strip()

        blurb = """\
        Copyright (c) 2013 Frank Brehm, Berlin.

        Checks all processes and generates WARNING or CRITICAL states if the specified
        metric is outside the required threshold ranges. The metric defaults to number
        of processes.  Search filters can be applied to limit the processes to check.
        """
        blurb = textwrap.dedent(blurb).strip()

        super(CheckProcsPlugin, self).__init__(
                usage = usage, version = __version__, blurb = blurb,
        )


        self._ps_cmd = PS_CMD
        """
        @ivar: the underlaying 'ps' command
        @type: str
        """
        if not os.path.exists(self.ps_cmd) or not os.access(
                self.ps_cmd, os.X_OK):
            self._ps_cmd = self.get_command('ps')
        if not self.ps_cmd:
            failed_commands.append('ps')

        # Some commands are missing
        if failed_commands:
            raise CommandNotFoundError(failed_commands)

        self._add_args()

    #------------------------------------------------------------
    @property
    def ps_cmd(self):
        """The absolute path to the OS command 'ps'."""
        return self._ps_cmd

    #--------------------------------------------------------------------------
    def as_dict(self):
        """
        Typecasting into a dictionary.

        @return: structure as dict
        @rtype:  dict

        """

        d = super(CheckProcsPlugin, self).as_dict()

        d['ps_cmd'] = self.ps_cmd

        return d

    #--------------------------------------------------------------------------
    def _add_args(self):
        """
        Adding all necessary arguments zo the commandline argument parser.
        """

        self.add_arg(
                '-w', '--warning',
                type = NagiosRange,
                metavar = 'RANGE',
                dest = 'warning',
                required = True,
                help = 'Generate warning state if metric is outside this range',
        )

        self.add_arg(
                '-c', '--critical',
                type = NagiosRange,
                metavar = 'RANGE',
                dest = 'critical',
                required = True,
                help = 'Generate critical state if metric is outside this range',
        )

        self.add_arg(
                '-m', '--metric',
                choices = valid_metrics,
                dest = 'metric',
                required = True,
                default = 'PROCS',
                help = "Check thresholds against metric (default: %(default)s).",
        )

    #--------------------------------------------------------------------------
    def __call__(self):
        """
        Method to call the plugin directly.
        """

        self.parse_args()

#==============================================================================

if __name__ == "__main__":

    pass

#==============================================================================

# vim: fileencoding=utf-8 filetype=python ts=4
