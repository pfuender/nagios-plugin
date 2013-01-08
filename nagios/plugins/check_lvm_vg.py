#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
@author: Frank Brehm
@contact: frank.brehm@profitbricks.com
@copyright: © 2010 - 2013 by Frank Brehm, Berlin
@summary: Module for CheckLvmVgPlugin class
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

from numbers import Number

# Third party modules

# Own modules

import nagios
from nagios import BaseNagiosError

from nagios.common import pp, caller_search_path

from nagios.plugin import NagiosPluginError

from nagios.plugin.range import NagiosRange

from nagios.plugins import ExtNagiosPluginError
from nagios.plugins import ExecutionTimeoutError
from nagios.plugins import CommandNotFoundError
from nagios.plugins import ExtNagiosPlugin

#---------------------------------------------
# Some module variables

__version__ = '0.1.0'

log = logging.getLogger(__name__)

VGS_CMD = os.sep + os.path.join('sbin', 'vgs')


#==============================================================================
class CheckLvmVgPlugin(ExtNagiosPlugin):
    """
    A special NagiosPlugin class for checking a LVM volume group for its
    state and/or its free place.
    """

    #--------------------------------------------------------------------------
    def __init__(self, check_state = False):
        """
        Constructor of the CheckLvmVgPlugin class.

        @param check_state: if True, use this plugin to check the state,
                            if False, use it to check the free place of the VG
        @type check_state: bool

        """

        usage = ''
        if check_state:
            usage = """\
            %(prog)s [-v] [-t <timeout>] <volume_group>
            """
        else:
            usage = """\
            %(prog)s [-v] [-t <timeout>] -c <critical> -w <warning> <volume_group>
            """
        usage = textwrap.dedent(usage).strip()
        usage += '\n       %(prog)s --usage'
        usage += '\n       %(prog)s --help'

        blurb = "Copyright (c) 2013 Frank Brehm, Berlin.\n\n"
        if check_state:
            blurb += "Checks the state of the given volume group."
        else:
            blurb += "Checks the free space of the given volume group."

        super(CheckLvmVgPlugin, self).__init__(
                usage = usage, version = __version__, blurb = blurb,
        )

        self._check_state = bool(check_state)
        """
        @ivar: if True, use this plugin to check the state, if not, use it
               to check the free place of the VG
        @type: bool
        """

        self._vgs_cmd = VGS_CMD
        """
        @ivar: the underlaying 'ps' command
        @type: str
        """
        if not os.path.exists(self.vgs_cmd) or not os.access(
                self.vgs_cmd, os.X_OK):
            self._vgs_cmd = self.get_command('vgs')
        if not self.vgs_cmd:
            msg = "Command %r not found." % (VGS_CMD)
            self.die(msg)

        self._vg = None
        """
        @ivar: the volume group to check
        @type: str
        """

        self._add_args()

    #------------------------------------------------------------
    @property
    def vgs_cmd(self):
        """The absolute path to the OS command 'vgs'."""
        return self._vgs_cmd

    #------------------------------------------------------------
    @property
    def vg(self):
        """The volume group to check."""
        return self._vg

    #------------------------------------------------------------
    @property
    def check_state(self):
        """Use this plugin to check the state or to check the free place."""
        return self._check_state

    #--------------------------------------------------------------------------
    def as_dict(self):
        """
        Typecasting into a dictionary.

        @return: structure as dict
        @rtype:  dict

        """

        d = super(CheckLvmVgPlugin, self).as_dict()

        d['vgs_cmd'] = self.vgs_cmd
        d['vg'] = self.vg
        d['check_state'] = self.check_state

        return d

    #--------------------------------------------------------------------------
    def _add_args(self):
        """
        Adding all necessary arguments to the commandline argument parser.
        """

        if not self.check_state:
            self.add_arg(
                    '-w', '--warning',
                    metavar = 'FREE',
                    dest = 'warning',
                    required = True,
                    help = ('Generate warning state if the free space of the' +
                            'VG is below this value, maybe given absolute in ' +
                            'MiBytes or as percentage of the total size.'),
            )

            self.add_arg(
                    '-c', '--critical',
                    metavar = 'FREE',
                    dest = 'critical',
                    required = True,
                    help = ('Generate critical state if the free space of the' +
                            'VG is below this value, maybe given absolute in ' +
                            'MiBytes or as percentage of the total size.'),
            )

        vg_help = ''
        if self.check_state:
            vg_help = "The volume group, to check the state."
        else:
            vg_help = "The volume group to check the free place."

        self.add_arg(
                'vg',
                dest = 'vg',
                nargs = '?',
                help = vg_help,
        )

    #--------------------------------------------------------------------------
    def __call__(self):
        """
        Method to call the plugin directly.
        """

        self.parse_args()
        self.init_root_logger()

        if not self.argparser.args.vg:
            self.die("No volume group to check given.")

        if self.verbose > 2:
            log.debug("Current object:\n%s", pp(self.as_dict()))

        state = nagios.state.ok
        self.exit(state, "The stars are shining above us...")

        # vgs --unit m --noheadings --nosuffix --separator ';' --unbuffered \
        #   -o vg_fmt,vg_name,vg_attr,vg_size,vg_free,vg_extent_size,vg_extent_count,vg_free_count storage

#==============================================================================

if __name__ == "__main__":

    pass

#==============================================================================

# vim: fileencoding=utf-8 filetype=python ts=4
