#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
@author: Frank Brehm
@contact: frank.brehm@profitbricks.com
@copyright: © 2010 - 2013 by Frank Brehm, Berlin
@summary: Module for CheckIbStatusPlugin class
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

from nagios.plugin.range import NagiosRange

from nagios.plugin.threshold import NagiosThreshold

from nagios.plugins import ExtNagiosPluginError
from nagios.plugins import ExecutionTimeoutError
from nagios.plugins import CommandNotFoundError
from nagios.plugins import ExtNagiosPlugin

#---------------------------------------------
# Some module variables

__version__ = '0.3.0'

log = logging.getLogger(__name__)

DEFAULT_RATE = 40
DEFAULT_TIMEOUT = 2
IB_BASE_DIR = os.sep + os.path.join('sys', 'class', 'infiniband')

# Some conststants from /usr/include/infiniband/iba/ib_types.h:
IB_LINK_NO_CHANGE = 0
IB_LINK_DOWN      = 1
IB_LINK_INIT      = 2
IB_LINK_ARMED     = 3
IB_LINK_ACTIVE    = 4
IB_LINK_ACT_DEFER = 5

IB_PORT_PHYS_STATE_NO_CHANGE      = 0
IB_PORT_PHYS_STATE_SLEEP          = 1
IB_PORT_PHYS_STATE_POLLING        = 2
IB_PORT_PHYS_STATE_DISABLED       = 3
IB_PORT_PHYS_STATE_SHIFT          = 4
IB_PORT_PHYS_STATE_LINKUP         = 5
IB_PORT_PHYS_STATE_LINKERRRECOVER = 6
IB_PORT_PHYS_STATE_PHYTEST        = 7

re_state = re.compile(r'^(\d+):\s+(\S.*)')
re_rate = re.compile(r'^(\d+)')

#==============================================================================
class CheckIbStatusPlugin(ExtNagiosPlugin):
    """
    A special NagiosPlugin class for checking the state of a particular
    infiniband HCA and port.
    """

    #--------------------------------------------------------------------------
    def __init__(self):
        """
        Constructor of the CheckIbStatusPlugin class.
        """

        usage = """\
                %(prog)s [-v] [-t <timeout>] -H <HCA_name> -P <HCA_port> [--rate <RATE>]
                """
        usage = textwrap.dedent(usage).strip()
        usage += '\n       %(prog)s --usage'
        usage += '\n       %(prog)s --help'

        blurb = "Copyright (c) 2013 Frank Brehm, Berlin.\n\n"
        blurb += "Checks the state of the given Infiniband HCA port."

        super(CheckIbStatusPlugin, self).__init__(
                shortname = 'IB_PORT',
                usage = usage, blurb = blurb,
                version = __version__, timeout = DEFAULT_TIMEOUT,
        )

        self._hca_name = None
        """
        @ivar: the name of the HCA to check (e.g. 'mlx4_0')
        @type: str
        """

        self._hca_port = None
        """
        @ivar: the port number of the HCA to check (e.g. 1)
        @type: int
        """

        self._rate = 40
        """
        @ivar: the expected transfer rate of the HCA port in Gb/sec
        @type: int
        """

        self._add_args()

    #------------------------------------------------------------
    @property
    def hca_name(self):
        """The name of the HCA to check (e.g. 'mlx4_0')."""
        return self._hca_name

    #------------------------------------------------------------
    @property
    def hca_port(self):
        """The port number of the HCA to check (e.g. 1)."""
        return self._hca_port

    #------------------------------------------------------------
    @property
    def rate(self):
        """The expected transfer rate of the HCA port in Gb/sec."""
        return self._rate

    #--------------------------------------------------------------------------
    def as_dict(self):
        """
        Typecasting into a dictionary.

        @return: structure as dict
        @rtype:  dict

        """

        d = super(CheckIbStatusPlugin, self).as_dict()

        d['hca_name'] = self.hca_name
        d['hca_port'] = self.hca_port
        d['rate'] = self.rate

        return d

    #--------------------------------------------------------------------------
    def _add_args(self):
        """
        Adding all necessary arguments to the commandline argument parser.
        """

        self.add_arg(
                '-H', '--hca-name',
                metavar = 'HCA',
                dest = 'hca_name',
                required = True,
                help = "The name of the HCA to check (e.g. 'mlx4_0').",
        )

        self.add_arg(
                '-P', '--hca-port',
                metavar = 'PORT',
                dest = 'hca_port',
                type = int,
                required = True,
                help = "The port number of the HCA to check (e.g. 1).",
        )

        self.add_arg(
                '--rate',
                metavar = 'RATE',
                dest = 'rate',
                type = int,
                default = DEFAULT_RATE,
                help = ("The expected transfer rate of the HCA port " +
                        "in Gb/sec (Default: %(default)d)."),
        )

    #--------------------------------------------------------------------------
    def parse_args(self, args = None):
        """
        Executes self.argparser.parse_args().

        @param args: the argument strings to parse. If not given, they are
                     taken from sys.argv.
        @type args: list of str or None

        """

        super(CheckIbStatusPlugin, self).parse_args(args)

        self._hca_name = self.argparser.args.hca_name
        self._hca_port = self.argparser.args.hca_port
        self._rate = self.argparser.args.rate

    #--------------------------------------------------------------------------
    def __call__(self):
        """
        Method to call the plugin directly.
        """

        self.parse_args()
        self.init_root_logger()

        state = nagios.state.ok
        out = "Infiniband port %s:%d seems to be okay." % (
                self.hca_name, self.hca_port)

        if self.verbose > 2:
            log.debug("Current object:\n%s", pp(self.as_dict()))

        # Checking directories in sysfs ...
        hca_dir = os.path.join(IB_BASE_DIR, self.hca_name)
        ports_dir = os.path.join(hca_dir, 'ports')
        port_dir = os.path.join(ports_dir, str(self.hca_port))

        for sysfsdir in (IB_BASE_DIR, hca_dir, ports_dir, port_dir):
            if self.verbose > 1:
                log.debug("Checking directory %r ...", sysfsdir)
            if not os.path.exists(sysfsdir):
                msg = "Directory %r doesn't exists." % (sysfsdir)
                self.exit(nagios.state.critical, msg)
            if not os.path.isdir(sysfsdir):
                msg = "%r is not a directory." % (sysfsdir)
                self.exit(nagios.state.critical, msg)

        # Checking state files
        state_file = os.path.join(port_dir, 'state')
        phys_state_file = os.path.join(port_dir, 'phys_state')
        rate_file = os.path.join(port_dir, 'rate')

        for sfile in (state_file, phys_state_file, rate_file):
            if self.verbose > 1:
                log.debug("Checking file %r ...", sfile)
            if not os.path.exists(sfile):
                msg = "File %r doesn't exists." % (sfile)
                self.exit(nagios.state.critical, msg)
            if not os.path.isfile(sfile):
                msg = "%r is not a regular file." % (sfile)
                self.exit(nagios.state.critical, msg)

        # getting state (e.g.: '4: ACTIVE', '1: DOWN')
        cur_state = self.read_file(state_file).strip()
        state_num = None
        state_str = None
        match = re_state.search(cur_state)
        if not match:
            msg = "Could not evaluate IB port state %r from %r." % (
                    cur_state, state_file)
            self.die(msg)
        state_num = int(match.group(1))
        state_str = match.group(2)
        log.debug("Got a state %r (%d) for infiniband port %s:%d.", state_str,
                state_num, self.hca_name, self.hca_port)

        # getting physical state (e.g.: '5: LinkUp', '2: Polling')
        cur_phys_state = self.read_file(phys_state_file).strip()
        phys_state_num = None
        phys_state_str = None
        match = re_state.search(cur_phys_state)
        if not match:
            msg = "Could not evaluate IB port physical state %r from %r." % (
                    cur_phys_state, phys_state_file)
            self.die(msg)
        phys_state_num = int(match.group(1))
        phys_state_str = match.group(2)
        log.debug("Got a physical state %r (%d) for infiniband port %s:%d.",
                phys_state_str, phys_state_num, self.hca_name, self.hca_port)

        # getting the current port rate (e.g. '40 Gb/sec (4X QDR)')
        cur_rate = self.read_file(rate_file).strip()
        rate_val = None
        match = re_rate.search(cur_rate)
        if not match:
            msg = "Could not evaluate IB port rate %r from %r." % (
                    cur_rate, rate_file)
            self.die(msg)
        rate_val = int(match.group(1))
        log.debug("Got a data rate of %d GiB/sec [%s] for infiniband port %s:%d.",
                rate_val, cur_rate, self.hca_name, self.hca_port)

        if rate_val != self.rate:
            state = nagios.state.warning

        if state_num != IB_LINK_ACTIVE:
            state = nagios.state.critical

        if phys_state_num != IB_PORT_PHYS_STATE_LINKUP:
            state = nagios.state.critical

        out = "Infiniband port %s:%d is %s (%s) - current rate %s." % (
                self.hca_name, self.hca_port, state_str, phys_state_str,
                cur_rate)

        self.exit(state, out)

#==============================================================================

if __name__ == "__main__":

    pass

#==============================================================================

# vim: fileencoding=utf-8 filetype=python ts=4 et
