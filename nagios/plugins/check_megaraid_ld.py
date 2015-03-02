#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
@author: Frank Brehm
@contact: frank.brehm@profitbricks.com
@copyright: © 2010 - 2015 by Frank Brehm, Berlin
@summary: Module for a class for a nagios/icinga plugin to check a particular
          logical drive on a LSI MegaRaid adapter
"""

# Standard modules
import re
import logging
import textwrap

# Third party modules

# Own modules

import nagios

from nagios.plugin.functions import max_state


import nagios.plugins.check_megaraid
from nagios.plugins.check_megaraid import CheckMegaRaidPlugin

# --------------------------------------------
# Some module variables

__version__ = '0.2.2'

log = logging.getLogger(__name__)

# Example output
"""
0 storage208:~ # megacli -LdInfo -L 0 -a0


Adapter 0 -- Virtual Drive Information:
Virtual Drive: 0 (Target Id: 0)
Name                :
RAID Level          : Primary-1, Secondary-0, RAID Level Qualifier-0
Size                : 55.375 GB
Sector Size         : 512
Is VD emulated      : No
Mirror Data         : 55.375 GB
State               : Optimal
Strip Size          : 256 KB
Number Of Drives    : 2
Span Depth          : 1
Default Cache Policy: WriteBack, ReadAdaptive, Direct, No Write Cache if Bad BBU
Current Cache Policy: WriteBack, ReadAdaptive, Direct, No Write Cache if Bad BBU
Default Access Policy: Read/Write
Current Access Policy: Read/Write
Disk Cache Policy   : Enabled
Encryption Type     : None
PI type: No PI

Is VD Cached: No



Exit Code: 0x00
0 storage208:~ # megacli -LdInfo -L 3 -a0


Adapter 0 -- Virtual Drive Information:
Virtual Drive: 3 (Target Id: 3)
Name                :
RAID Level          : Primary-1, Secondary-0, RAID Level Qualifier-0
Size                : 2.728 TB
Sector Size         : 512
Is VD emulated      : No
Mirror Data         : 2.728 TB
State               : Optimal
Strip Size          : 256 KB
Number Of Drives    : 2
Span Depth          : 1
Default Cache Policy: WriteBack, ReadAdaptive, Direct, No Write Cache if Bad BBU
Current Cache Policy: WriteBack, ReadAdaptive, Direct, No Write Cache if Bad BBU
Default Access Policy: Read/Write
Current Access Policy: Read/Write
Disk Cache Policy   : Enabled
Encryption Type     : None
PI type: No PI

Is VD Cached: Yes
Cache Cade Type : Read Only



Exit Code: 0x00
"""


# =============================================================================
class CheckMegaRaidLdPlugin(CheckMegaRaidPlugin):
    """
    A special NagiosPlugin class for checking the state of a Logical Drive of a
    LSI MegaRaid adapter.
    """

    # -------------------------------------------------------------------------
    def __init__(self):
        """
        Constructor of the CheckMegaRaidLdPlugin class.
        """

        usage = """\
                %(prog)s [-v] [-a <adapter_nr>] -l <drive_nr> [--cached]
                """
        usage = textwrap.dedent(usage).strip()
        usage += '\n       %(prog)s --usage'
        usage += '\n       %(prog)s --help'

        blurb = "Copyright (c) 2015 Frank Brehm, Berlin.\n\n"
        blurb += "Checks the state of a Logical Drive of a LSI MegaRaid adapter."

        super(CheckMegaRaidLdPlugin, self).__init__(
            shortname='MEGARAID_LD',
            usage=usage, blurb=blurb,
            version=__version__,
        )

        self._ld_number = None
        """
        @ivar: the number of the Logical Drive to check
        @type: int
        """

        self._cached = False
        """
        @ivar: checking, whether the LD is cached by CacheCade
        @type: bool
        """

        self._warn_on_consistency_check = False
        """
        @ivar: Emit a warning, if there is currently a consitency check
               on this logical drive
        @type: bool
        """

        self._add_args()

    # -----------------------------------------------------------
    @property
    def ld_number(self):
        """The number of the Logical Drive to check."""
        return self._ld_number

    # -----------------------------------------------------------
    @property
    def cached(self):
        """Checking, whether the LD is cached by CacheCade."""
        return self._cached

    # -----------------------------------------------------------
    @property
    def warn_on_consistency_check(self):
        """
        Emit a warning, if there is currently a consitency check
        on this logical drive.
        """
        return self._warn_on_consistency_check

    # -------------------------------------------------------------------------
    def as_dict(self):
        """
        Typecasting into a dictionary.

        @return: structure as dict
        @rtype:  dict

        """

        d = super(CheckMegaRaidLdPlugin, self).as_dict()

        d['ld_number'] = self.ld_number
        d['cached'] = self.cached
        d['warn_on_consistency_check'] = self.warn_on_consistency_check

        return d

    # -------------------------------------------------------------------------
    def _add_args(self):
        """
        Adding all necessary arguments to the commandline argument parser.
        """

        self.add_arg(
            '-l', '--ld-nr',
            metavar='NR',
            dest='ld_nr',
            required=True,
            type=int,
            help="The number of the Logical Drive to check (mandantory).",
        )

        self.add_arg(
            '--cached',
            action='store_true',
            dest='cached',
            help="Checking, whether the LD is cached by CacheCade.",
        )

        self.add_arg(
            '-W', '--warn_on_consistency_check',
            action='store_true',
            dest='wocc',
            help=(
                'Emit a warning, if there is currently a '
                'consitency check on this logical drive.'),
        )

        super(CheckMegaRaidLdPlugin, self)._add_args()

    # -------------------------------------------------------------------------
    def parse_args(self, args=None):
        """
        Executes self.argparser.parse_args().

        If overridden by successors, it should be called via super().

        @param args: the argument strings to parse. If not given, they are
                     taken from sys.argv.
        @type args: list of str or None

        """

        super(CheckMegaRaidLdPlugin, self).parse_args(args)

        self._ld_number = self.argparser.args.ld_nr
        if self.argparser.args.cached:
            self._cached = True

        if self.argparser.args.wocc:
            self._warn_on_consistency_check = True

    # -------------------------------------------------------------------------
    def call(self):
        """
        Method to call the plugin directly.
        """

        state = nagios.state.ok
        out = "LD %d of MegaRaid adapter %d seems to be okay." % (
            self.ld_number, self.adapter_nr)

        # Adapter 0: Virtual Drive 55 Does not Exist.
        re_not_exists = re.compile(
            r'^.*Virtual\s+Drive\s+\d+\s+Does\s+not\s+Exist\.', re.IGNORECASE)
        # RAID Level          : Primary-1, Secondary-0, RAID Level Qualifier-0
        re_raid_level = re.compile(
            r'^\s*RAID\s+Level\s*:\s+Primary-(\d+)', re.IGNORECASE)
        # Size                : 2.728 TB
        re_size = re.compile(
            r'^\s*Size\s*:\s+(\d+(?:\.\d*)?)\s*(\S+)?', re.IGNORECASE)
        # State               : Optimal
        re_state = re.compile(r'^\s*State\s*:\s+(\S+)', re.IGNORECASE)
        # Number Of Drives    : 2
        re_number = re.compile(
            r'^\s*Number\s+Of\s+Drives\s*:\s+(\d+)', re.IGNORECASE)
        # Span Depth          : 1
        re_span = re.compile(r'^\s*Span\s+Depth\s*:\s+(\d+)', re.IGNORECASE)
        # Is VD Cached: Yes
        # Is VD Cached: No
        re_cached = re.compile(
            r'^\s*Is\s+VD\s+Cached\s*:\s+(\S+)', re.IGNORECASE)
        # Check Consistency: Completed 95%, Taken 8 min
        re_consist = re.compile(
            r'Check\s+Consistency\s*:\s+Completed\s+(\d+)%,\s+Taken\s+(\d+)\s*min',
            re.IGNORECASE)

        raid_level = None
        size_val = None
        size_unit = None
        ld_state = None
        pd_number = None
        span_depth = None
        ld_cached = None
        consist_percent = None
        consist_min = None

        args = ('-LdInfo', '-L', ("%d" % (self.ld_number)))
        (stdoutdata, stderrdata, ret, exit_code) = self.megacli(args)
        if self.verbose > 2:
            log.debug("Output on StdOut:\n%s", stdoutdata)

        for line in stdoutdata.splitlines():

            line = line.strip()

            # Logical Drive not exists
            if re_not_exists.search(line):
                self.die(line)

            match = re_raid_level.search(line)
            if match:
                raid_level = int(match.group(1))
                continue

            match = re_size.search(line)
            if match:
                size_val = float(match.group(1))
                size_unit = match.group(2)
                continue

            match = re_state.search(line)
            if match:
                ld_state = match.group(1)
                continue

            match = re_number.search(line)
            if match:
                pd_number = int(match.group(1))
                continue

            match = re_span.search(line)
            if match:
                span_depth = int(match.group(1))
                continue

            match = re_cached.search(line)
            if match:
                ld_cached = match.group(1)

            match = re_consist.search(line)
            if match:
                consist_percent = int(match.group(1))
                consist_min = int(match.group(2))

        if exit_code:
            state = nagios.state.critical
        elif not ld_state:
            state = nagios.state.critical
            ld_state = 'unknown'
        elif ld_state.lower() != 'optimal':
            state = nagios.state.critical

        consistency_out = ''
        if consist_percent is not None:
            if self.warn_on_consistency_check:
                state = max_state(state, nagios.state.warning)
            consistency_out = ", consistency check completed: %d%%, taken %d min." % (
                consist_percent, consist_min)

        cached_out = ', cached: No'
        if ld_cached:
            cached_out = ', cached: %s' % (ld_cached)
        if self.cached:
            if not ld_cached or ld_cached.lower() != 'yes':
                state = max_state(state, nagios.state.warning)

        pd_count = 9999
        if pd_number:
            pd_count = pd_number
            if span_depth and span_depth > 1:
                pd_count = pd_number * span_depth
                if raid_level < 10:
                    raid_level *= 10

        size_out = ''
        if size_val:
            if size_unit:
                size_out = ', %s %s' % (str(size_val), size_unit)
            else:
                size_out = ', %s' % (str(size_val))

        out = "State of LD %d of MegaRaid adapter %d (RAID-%d, %d drives%s%s%s): %s." % (
            self.ld_number, self.adapter_nr, raid_level, pd_count,
            size_out, cached_out, consistency_out, ld_state)

        self.exit(state, out)

# =============================================================================

if __name__ == "__main__":

    pass

# =============================================================================

# vim: fileencoding=utf-8 filetype=python ts=4 et
