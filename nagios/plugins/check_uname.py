#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
@author: Frank Brehm
@contact: frank.brehm@profitbricks.com
@copyright: © 2010 - 2015 by Frank Brehm, Berlin
@summary: Module for CheckUnamePlugin class
"""

# Standard modules
import os
import sys
import logging
import textwrap

# Third party modules

from pkg_resources import parse_version

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
from nagios.plugin.extended import ExtNagiosPlugin

#---------------------------------------------
# Some module variables

__version__ = '0.1.0'

log = logging.getLogger(__name__)

#==============================================================================
class CheckUnamePlugin(ExtNagiosPlugin):
    """
    A special NagiosPlugin class for checking a uname parameters, espcially
    the version of the current running kernel.
    """

    #--------------------------------------------------------------------------
    def __init__(self):
        """
        Constructor of the CheckUnamePlugin class.
        """

        usage = """\
        %(prog)s [-v] [--warning] [--arch <architecture>] [--os <operating system>]
                   [--min-version <version>]
        %(prog)s --usage
        %(prog)s --help
        """
        usage = textwrap.dedent(usage).strip()

        blurb = """\
        Copyright (c) 2015 Frank Brehm, Berlin.

        Checks differnt uname parameters, e.g. the kernel version, the
        architecture and the operating system  against the given parameters.
        """
        blurb = textwrap.dedent(blurb).strip()

        super(CheckUnamePlugin, self).__init__(
                usage = usage, blurb = blurb,
        )

        self._warning = False
        """
        @ivar: Return a warning instead of critical error, if the current
               kernel version is below the given kernel version.
               On failures on architecture and operating system always a
               critical error is thrown.
        @type: bool
        """

        self._arch = None
        """
        @ivar: the architecture to check for, e.g. 'x86_64'
        @type: str
        """

        self._os = None
        """
        @ivar: the operating system to check for, e.g. 'Linux'
        @type: str
        """

        self._min_version = None
        """
        @ivar: the minimum version number of the current running kernel
        @type: str or None
        """

        self._add_args()

    #------------------------------------------------------------
    @property
    def warning(self):
        """
        Return a warning instead of critical error, if the current
        kernel version is below the given kernel version.
        """
        return self._warning

    @warning.setter
    def warning(self, value):
        self._warning = bool(value)

    #------------------------------------------------------------
    @property
    def min_version(self):
        """The minimum version number of the current running kernel."""
        return self._min_version

    #------------------------------------------------------------
    @property
    def arch(self):
        """The architecture to check for, e.g. 'x86_64'."""
        return self._arch

    #------------------------------------------------------------
    @property
    def os(self):
        """The operating system to check for, e.g. 'Linux'."""
        return self._os

    #--------------------------------------------------------------------------
    def as_dict(self):
        """
        Typecasting into a dictionary.

        @return: structure as dict
        @rtype:  dict

        """

        d = super(CheckUnamePlugin, self).as_dict()

        d['min_version'] = self.min_version
        d['arch'] = self.arch
        d['os'] = self.os
        d['warning'] = self.warning

        return d

    #--------------------------------------------------------------------------
    def _add_args(self):
        """
        Adding all necessary arguments to the commandline argument parser.
        """

        self.add_arg(
                '-w', '--warning',
                action = 'store_true',
                dest = 'warning',
                help = ('Return a warning instead of critical error, if the ' +
                        'current kernel version is below the given kernel version.'),
        )

        self.add_arg(
                '-a', '--arch',
                metavar = 'ARCHITECTURE',
                dest = 'arch',
                help = "The architecture to check for, e.g. 'x86_64'.",
        )

        self.add_arg(
                '-o', '--os',
                metavar = 'OS',
                dest = 'os',
                help = "The operating system to check for, e.g. 'Linux'.",
        )

        self.add_arg(
                '-m', '--min-version',
                metavar = 'VERSION',
                dest = 'min_version',
                help = "The minimum version number of the current running kernel.",
        )

    #--------------------------------------------------------------------------
    def parse_args(self, args = None):
        """
        Executes self.argparser.parse_args().

        @param args: the argument strings to parse. If not given, they are
                     taken from sys.argv.
        @type args: list of str or None

        """

        super(CheckUnamePlugin, self).parse_args(args)

        if self.argparser.args.warning:
            self.warning = self.argparser.args.warning
        if self.argparser.args.min_version is not None:
            self._min_version = self.argparser.args.min_version

        if self.argparser.args.arch is not None:
            log.debug("Setting architecture to %r ...", self.argparser.args.arch)
            self._arch = self.argparser.args.arch
        if self.argparser.args.os is not None:
            self._os = self.argparser.args.os

        if self.min_version is None and self.arch is None and self.os is None:
            msg = ("In minimum one of the arguments '--arch', '--os' or " +
                    "'--min-version' must be given.")
            self.die(msg)

    #--------------------------------------------------------------------------
    def __call__(self):
        """
        Method to call the plugin directly.
        """

        self.parse_args()
        self.init_root_logger()

        if self.verbose > 2:
            log.debug("Current object:\n%s", pp(self.as_dict()))

        un = os.uname()

        state = nagios.state.ok
        out = "%s kernel for %s with version %r." % (un[0], un[4], un[2])

        if self.arch is not None:
            if self.arch.lower() != un[4].lower():
                state = self.max_state(state, nagios.state.critical)
                out += " Architecture is not %r." % (self.arch)

        if self.os is not None:
            if self.os.lower() != un[0].lower():
                state = self.max_state(state, nagios.state.critical)
                out += " Operating system is not %r." % (self.os)

        if self.min_version is not None:
            cur_version = un[2]

            parsed_version_expected = parse_version(self.min_version)
            if self.verbose > 1:
                log.debug("Expecting parsed version %r.", parsed_version_expected)

            parsed_version_got = parse_version(cur_version)
            if self.verbose > 1:
                log.debug("Got parsed version %r.", parsed_version_got)

            if parsed_version_got < parsed_version_expected:
                if self.warning:
                    state = self.max_state(state, nagios.state.warning)
                else:
                    state = self.max_state(state, nagios.state.critical)
                out += " Expected min. kernel version: %r." % (self.min_version)
        
        self.exit(state, out)

#==============================================================================

if __name__ == "__main__":

    pass

#==============================================================================

# vim: fileencoding=utf-8 filetype=python ts=4 et
