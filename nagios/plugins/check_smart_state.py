#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
@author: Frank Brehm
@contact: frank.brehm@profitbricks.com
@copyright: © 2010 - 2013 by Frank Brehm, Berlin
@summary: Module for CheckSmartStatePlugin class
"""

# Standard modules
import os
import sys
import logging
import textwrap
import pwd
import re
import signal
import subprocess
import locale

from numbers import Number
from subprocess import CalledProcessError

# Third party modules

# Own modules

import nagios
from nagios import BaseNagiosError

from nagios.common import pp, caller_search_path

from nagios.plugin import NagiosPluginError

from nagios.plugin.range import NagiosRange

from nagios.plugin.threshold import NagiosThreshold

from nagios.plugin.argparser import default_timeout

from nagios.plugins import ExtNagiosPluginError
from nagios.plugins import ExecutionTimeoutError
from nagios.plugins import CommandNotFoundError
from nagios.plugins import ExtNagiosPlugin

#---------------------------------------------
# Some module variables

__version__ = '0.1.0'

log = logging.getLogger(__name__)

DEFAULT_MEGARAID_PATH = '/opt/MegaRAID/MegaCli'

#==============================================================================
class CheckSmartStatePlugin(ExtNagiosPlugin):
    """
    A special NagiosPlugin class for checking the SMART state of a physical
    hard drive.
    """

    #--------------------------------------------------------------------------
    def __init__(self):
        """
        Constructor of the CheckSmartStatePlugin class.
        """

        usage = """\
        %(prog)s [-v] [-m] -c <critical grown sectors> -w <warn grown sectors> <HD device>
        """
        usage = textwrap.dedent(usage).strip()
        usage += '\n       %(prog)s --usage'
        usage += '\n       %(prog)s --help'

        blurb = "Copyright (c) 2013 Frank Brehm, Berlin.\n\n"
        blurb += "Checks the SMART state of a physical hard drive."

        super(CheckSmartStatePlugin, self).__init__(
                usage = usage, blurb = blurb,
                append_searchpath = [DEFAULT_MEGARAID_PATH],
        )

        self._smartctl_cmd = self.get_command('smartctl')
        """
        @ivar: the underlaying 'smartctl' command
        @type: str
        """
        if not self.smartctl_cmd:
            msg = "Command %r not found." % ('smartctl')
            self.die(msg)

        self._megacli_cmd = None
        """
        @ivar: the 'MegaCLI' command for detecting Device Id from an enclosure:slot data
        @type: str
        """

        self._megaraid = False
        """
        @ivar: Is the given device a PhysicalDrive on a MegaRaid adapter
        @type: bool
        """

        self._timeout = default_timeout
        """
        @ivar: the timeout on execution of commands in seconds
        @type: int
        """

        self._init_megacli_cmd()

        self._add_args()

    #------------------------------------------------------------
    @property
    def smartctl_cmd(self):
        """The absolute path to the OS command 'smartctl'."""
        return self._smartctl_cmd

    #------------------------------------------------------------
    @property
    def megacli_cmd(self):
        """The absolute path to the OS command 'MegaCli'."""
        return self._megacli_cmd

    #------------------------------------------------------------
    @property
    def megaraid(self):
        """Is the given device a PhysicalDrive on a MegaRaid adapter."""
        return self._megaraid

    @megaraid.setter
    def megaraid(self, value):
        self._megaraid = bool(value)

    #------------------------------------------------------------
    @property
    def timeout(self):
        """The timeout on execution of commands in seconds."""
        return self._timeout

    #--------------------------------------------------------------------------
    def as_dict(self):
        """
        Typecasting into a dictionary.

        @return: structure as dict
        @rtype:  dict

        """

        d = super(CheckSmartStatePlugin, self).as_dict()

        d['smartctl_cmd'] = self.smartctl_cmd
        d['megacli_cmd'] = self.megacli_cmd
        d['megaraid'] = self.megaraid

        return d

    #--------------------------------------------------------------------------
    def _init_megacli_cmd(self):
        """
        Initializes self.megacli_cmd.
        """

        self._megacli_cmd = self._get_megacli_cmd()

    #--------------------------------------------------------------------------
    def _get_megacli_cmd(self, given_path = None):
        """
        Finding the executable 'MegaCli64', 'MegaCli' or 'megacli' under the
        search path or the given path.

        @param given_path: a possibly given path to MegaCli
        @type given_path: str

        @return: the found path to the megacli executable.
        @rtype: str or None

        """

        exe_names = ('MegaCli', 'megacli')
        arch = os.uname()[4]
        if arch == 'x86_64':
            exe_names = ('MegaCli64', 'MegaCli', 'megacli')

        if given_path:
            # Normalize the given path, if it exists.
            if os.path.isabs(given_path):
                if not is_exe(given_path):
                    return None
                return os.path.realpath(given_path)
            exe_names = (given_path,)

        for exe_name in exe_names:
            log.debug("Searching for %r ...", exe_name)
            exe_file = self.get_command(exe_name, quiet = True)
            if exe_file:
                return exe_file

        return None

    #--------------------------------------------------------------------------
    def _add_args(self):
        """
        Adding all necessary arguments to the commandline argument parser.
        """

        self.add_arg(
                '-m', '--megaraid',
                dest = 'megaraid',
                action = 'store_true',
                help = ('Is the given device a PhysicalDrive ' +
                        'on a MegaRaid adapter.'),
        )

    #--------------------------------------------------------------------------
    def __call__(self):
        """
        Method to call the plugin directly.
        """

        self.parse_args()
        self.init_root_logger()

        if self.verbose > 2:
            log.debug("Current object:\n%s", pp(self.as_dict()))

        state = nagios.state.ok
        out = "All seems to be ok."

        self.exit(state, out)

#==============================================================================

if __name__ == "__main__":

    pass

#==============================================================================

# vim: fileencoding=utf-8 filetype=python ts=4 expandtab shiftwidth=4 softtabstop=4
