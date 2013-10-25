#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
@author: Frank Brehm
@contact: frank.brehm@profitbricks.com
@copyright: © 2010 - 2013 by Frank Brehm, Berlin
@summary: Module for CheckSoftwareRaidPlugin class
"""

# Standard modules
import os
import sys
import logging
import textwrap
import pwd
import re
import locale
import stat

from numbers import Number

# Third party modules

# Own modules

import nagios
from nagios import BaseNagiosError

from nagios.common import pp, caller_search_path

from nagios.plugin import NagiosPluginError
from nagios.plugin import NPReadTimeoutError

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

#==============================================================================
class CheckSoftwareRaidPlugin(ExtNagiosPlugin):
    """
    A special NagiosPlugin class for checking the state of one or all  Linux
    software RAID devices (MD devices).
    """

    #--------------------------------------------------------------------------
    def __init__(self):
        """
        Constructor of the CheckSoftwareRaidPlugin class.
        """

        usage = """\
        %(prog)s [-v] [<MD device>]
        """
        usage = textwrap.dedent(usage).strip()
        usage += '\n       %(prog)s --usage'
        usage += '\n       %(prog)s --help'

        blurb = "Copyright (c) 2013 Frank Brehm, Berlin.\n\n"
        blurb += "Checks the state of one or all  Linux software RAID devices."

        super(CheckSoftwareRaidPlugin, self).__init__(
                usage = usage, blurb = blurb,
        )

        self.devices = []
        """
        @ivar: all MD devices to check
        @type: list of str
        """

        self.check_all = False
        """
        @ivar: flag to check all available MD devices
        @type: bool
        """

        self.good_ones = []
        """
        @ivar: all messages after checking with OK state
        @type: list of str
        """

        self.bad_ones = []
        """
        @ivar: all messages after checking with WARNING state
        @type: list of str
        """

        self.ugly_ones = []
        """
        @ivar: all messages after checking with CRITICAL state
        @type: list of str
        """

        self.checked_devices = 0
        """
        @ivar: the total number of checked devices
        @type: int
        """

        self._add_args()

    #--------------------------------------------------------------------------
    def as_dict(self):
        """
        Typecasting into a dictionary.

        @return: structure as dict
        @rtype:  dict

        """

        d = super(CheckSoftwareRaidPlugin, self).as_dict()

        d['devices'] = self.devices
        d['check_all'] = self.check_all
        d['good_ones'] = self.good_ones
        d['bad_ones'] = self.bad_ones
        d['ugly_ones'] = self.ugly_ones
        d['checked_devices'] = self.checked_devices

        return d

    #--------------------------------------------------------------------------
    def _add_args(self):
        """
        Adding all necessary arguments to the commandline argument parser.
        """

        self.add_arg(
                'device',
                dest = 'device',
                nargs = '?',
                help = ("The device to check (given as 'mdX' or '/dev/mdX' " +
                        "or /sys/block/mdX, must exists)."),
        )

    #--------------------------------------------------------------------------
    def parse_args(self, args = None):
        """
        Executes self.argparser.parse_args().

        @param args: the argument strings to parse. If not given, they are
                     taken from sys.argv.
        @type args: list of str or None

        """

        super(CheckSoftwareRaidPlugin, self).parse_args(args)

        self.init_root_logger()

        re_dev = re.compile(r'^(?:/dev/|/sys/block/)?(md\d+)$')

        if self.argparser.args.device:
            if self.argparser.args.device.lower() == 'all':
                self.check_all = True
            else:
                match = re_dev.search(self.argparser.args.device)
                if not match:
                    self.die("Device %r is not a valid MD device." % (
                            self.argparser.args.device))
                self.devices.append(match.group(1))
        else:
            self.check_all = True

        if self.check_all:
            return

        dev = self.devices[0]
        dev_dev = os.sep + os.path.join('dev', dev)
        sys_dev = os.sep + os.path.join('sys', 'block', dev)

        if not os.path.isdir(sys_dev):
            self.die("Device %r is not a block device." % (dev))

        if not os.path.exists(dev_dev):
            self.die("Device %r doesn't exists." % (dev_dev))

        dev_stat = os.stat(dev_dev)
        dev_mode = dev_stat.st_mode
        if not stat.S_ISBLK(dev_mode):
            self.die("%r is not a block device." % (dev_dev))

    #--------------------------------------------------------------------------
    def __call__(self):
        """
        Method to call the plugin directly.
        """

        self.parse_args()

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
