#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
@author: Frank Brehm
@contact: frank.brehm@profitbricks.com
@copyright: © 2010 - 2013 by Frank Brehm, Berlin
@summary: Module for a class for a nagios/icinga plugin to check the number
          of hotspare drives on a LSI MegaRaid adapter
"""

# Standard modules
import os
import sys
import re
import logging
import textwrap

from numbers import Number

# Third party modules

# Own modules

import nagios
from nagios import BaseNagiosError

from nagios.common import pp, caller_search_path

from nagios.plugin import NagiosPluginError

from nagios.plugin.functions import max_state

from nagios.plugin.range import NagiosRange

from nagios.plugin.threshold import NagiosThreshold

from nagios.plugin.extended import ExtNagiosPluginError
from nagios.plugin.extended import ExecutionTimeoutError
from nagios.plugin.extended import CommandNotFoundError
from nagios.plugin.extended import ExtNagiosPlugin

import nagios.plugins.check_megaraid
from nagios.plugins.check_megaraid import CheckMegaRaidPlugin

#---------------------------------------------
# Some module variables

__version__ = '0.3.0'

log = logging.getLogger(__name__)

#==============================================================================
class CheckMegaRaidHotsparePlugin(CheckMegaRaidPlugin):
    """
    A special NagiosPlugin class for checking the number of hotspare drives on
    a LSI MegaRaid adapter.
    """

    #--------------------------------------------------------------------------
    def __init__(self):
        """
        Constructor of the CheckMegaRaidHotsparePlugin class.
        """

        usage = """\
                %(prog)s [-v] [-a <adapter_nr>] -c <critical_hotspares>: -w <warning_hotspares>:
                """
        usage = textwrap.dedent(usage).strip()
        usage += '\n       %(prog)s --usage'
        usage += '\n       %(prog)s --help'

        blurb = "Copyright (c) 2013 Frank Brehm, Berlin.\n\n"
        blurb += "Checks the number of hotspare drives on a LSI MegaRaid adapter."

        super(CheckMegaRaidHotsparePlugin, self).__init__(
                shortname = 'MEGARAID_HOTSPARE',
                usage = usage, blurb = blurb,
                version = __version__,
        )

        self._critical_number = NagiosRange('1:')

        self._warning_number = NagiosRange('2:')

        self._add_args()

    #------------------------------------------------------------
    @property
    def critical_number(self):
        """The number of hotspare drives, where it becomes critical, if
        the number of existing hotspares is below."""
        return self._critical_number

    #------------------------------------------------------------
    @property
    def warning_number(self):
        """The number of hotspare drives, where it becomes a warning, if
        the number of existing hotspares is below."""
        return self._warning_number

    #--------------------------------------------------------------------------
    def as_dict(self):
        """
        Typecasting into a dictionary.

        @return: structure as dict
        @rtype:  dict

        """

        d = super(CheckMegaRaidHotsparePlugin, self).as_dict()

        d['critical_number'] = self.critical_number.as_dict()
        d['warning_number'] = self.warning_number.as_dict()

        return d

    #--------------------------------------------------------------------------
    def _add_args(self):
        """
        Adding all necessary arguments to the commandline argument parser.
        """

        help_c = """\
                The number of hotspare drives, where it becomes critical,
                if the number of existing hotspares is below (mandantory,
                default: '%(default)s').
                """
        help_c = textwrap.dedent(help_c).replace('\n', ' ').strip()
        self.add_arg(
                '-c', '--critical',
                metavar = 'DRIVES:',
                dest = 'critical',
                required = True,
                type = NagiosRange,
                default = self.critical_number,
                help = help_c,
        )

        help_w = """\
                The number of hotspare drives, where it becomes a warning,
                if the number of existing hotspares is below (mandantory,
                default: '%(default)s').
                """
        help_w = textwrap.dedent(help_w).replace('\n', ' ').strip()
        self.add_arg(
                '-w', '--warning',
                metavar = 'DRIVES:',
                dest = 'warning',
                required = True,
                type = NagiosRange,
                default = self.warning_number,
                help = help_w,
        )

        super(CheckMegaRaidHotsparePlugin, self)._add_args()

    #--------------------------------------------------------------------------
    def parse_args(self, args = None):
        """
        Executes self.argparser.parse_args().

        If overridden by successors, it should be called via super().

        @param args: the argument strings to parse. If not given, they are
                     taken from sys.argv.
        @type args: list of str or None

        """

        super(CheckMegaRaidHotsparePlugin, self).parse_args(args)

        crit = self.argparser.args.critical
        if not crit.end is None:
            msg = ("The critical hot spare number must be given with an " +
                    "ending colon, e.g. '1:' (given %s).") % (crit)
            self.die(msg)
        self._critical_number = crit

        warn = self.argparser.args.warning
        if not warn.end is None:
            msg = ("The warning hot spare number must be given with an " +
                    "ending colon, e.g. '2:' (given %s).") % (warn)
            self.die(msg)
        self._warning_number = warn

        if crit.start > warn.start:
            msg = ("The warning number must be greater than or equal to " +
                    "the critical number (given warning: '%s', critical " +
                    "'%s').") % (warn, crit)
            self.die(msg)

        self.set_thresholds(
                warning = warn,
                critical = crit,
        )

    #--------------------------------------------------------------------------
    def call(self):
        """
        Method to call the plugin directly.
        """

        state = nagios.state.ok
        out = "Number of existing hotspares of MegaRaid adapter %d seems to be okay." % (
                self.adapter_nr)

        # Slot Number: 23
        re_slot = re.compile(r'^\s*Slot\s+Number\s*:\s*\d+', re.IGNORECASE)

        #
        re_fw = re.compile(r'^\s*Firmware\s+state\s*:\s*(\w+),?', re.IGNORECASE)

        found_hotspares = 0
        drives_total = 0
        args = ('-PdList',)
        (stdoutdata, stderrdata, ret, exit_code) = self.megacli(args)
        if self.verbose > 3:
            log.debug("Output on StdOut:\n%s", stdoutdata)

        for line in stdoutdata.splitlines():

            line = line.strip()

            if re_slot.search(line):
                drives_total += 1
                continue

            match = re_fw.search(line)
            if match and match.group(1).lower() == 'hotspare':
                found_hotspares += 1

        log.debug("Found %d drives, %d hotspares.", drives_total, found_hotspares)

        state = self.threshold.get_status(found_hotspares)
        out = "found %d hotspare(s) " % (found_hotspares)
        out += "(warning: <%d, critical: <%d)." %  (self.threshold.warning.start,
                self.threshold.critical.start)

        self.add_perfdata(
                label = 'hotspares',
                value = found_hotspares,
                uom = '',
                threshold = self.threshold,
        )

        self.add_perfdata(
                label = 'drives_total',
                value = drives_total,
                uom = '',
        )

        self.exit(state, out)

#==============================================================================

if __name__ == "__main__":

    pass

#==============================================================================

# vim: fileencoding=utf-8 filetype=python ts=4 et
