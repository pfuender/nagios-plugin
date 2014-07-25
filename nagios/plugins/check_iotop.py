#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
@author: Frank Brehm
@contact: frank.brehm@profitbricks.com
@copyright: © 2010 - 2014 by Frank Brehm, Berlin
@summary: Module for CheckIotopPlugin class for checking
          I/O utilization of processes
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
from iotop.data import find_uids, TaskStatsNetlink, ProcessList, Stats
from iotop.data import ThreadInfo

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

from nagios.plugin.config import NoConfigfileFound
from nagios.plugin.config import NagiosPluginConfig

#---------------------------------------------
# Some module variables

__version__ = '0.2.0'
__copyright__ = 'Copyright (c) 2014 Frank Brehm, Berlin.'

DEFAULT_TIMEOUT = 60

log = logging.getLogger(__name__)

###############################################################################
class IotopOptions(object):

    def __init__(self,
            only = False,
            batch = None,
            iterations = None,
            delay_seconds = 1,
            pids = None,
            users = None,
            processes = False,
            accumulated = False,
            kilobytes = False,
            time = None,
            quiet = 0,
            profile = False):

        self.only = bool(only)

        self.batch = None
        if batch is not None:
            self.batch = bool(batch)
        if time or quiet:
            self.batch = True

        self.iterations = None
        if iterations is not None:
            self.iterations = int(iterations)

        self.delay_seconds = int(delay_seconds)

        self.pids = []
        if pids:
            for pid in pids:
                self.pids.append(int(pid))

        self.users = []
        if users:
            for user in users:
                self.users.append(user)

        self.uids = []

        self.processes = bool(processes)

        self.accumulated = bool(accumulated)

        self.kilobytes = bool(kilobytes)

        self.time = None
        if time is not None:
            self.time = bool(time)

        self.quiet = int(quiet)

        self.profile = bool(profile)

#==============================================================================
class CheckIotopPlugin(ExtNagiosPlugin):
    """
    A special NagiosPlugin class for checking I/O utilization of processes
    with iotop
    """

    #--------------------------------------------------------------------------
    def __init__(self):
        """
        Constructor of the CheckIotopPlugin class.
        """

        usage = """\
        %(prog)s [-v] [-c <critical_thresholds>] [-w <warning_thresholds>]
                 [-d DURATION] [-i ITERATIONS]
        %(prog)s --usage
        %(prog)s --help
        """
        usage = textwrap.dedent(usage).strip()

        blurb = """\
        Copyright (c) 2014 Frank Brehm, Berlin.

        Checks the I/O utilization of all processes and generates WARNING or
        CRITICAL states if the block I/O delay breaks given thresholds.
        The I/O utilization will caught in ITERATIONS loops of
        an interval of DURATION seconds.
        This plugin must be executed as root.
        """
        blurb = textwrap.dedent(blurb).strip()

        super(CheckIotopPlugin, self).__init__(
                usage = usage, blurb = blurb,
        )

        self.warning = (0, 3, 5)
        self.critical = (1, 5, 10)
        self.delay = 1.0
        self.iterations = 5

        self.iotop_opts = None
        self.connection = None
        self.process_list = None
        self.processes = []
        self.process_count = {
                '90': 0,
                '50': 0,
                '10': 0,
                '0': 0,
                'total': 0,
        }

        self._add_args()

    #--------------------------------------------------------------------------
    def _add_args(self):
        """
        Adding all necessary arguments to the commandline argument parser.
        """

        msg_tpl = "Generate a %s state if the number of processes with an "
        msg_tpl += "I/O-delay of 90/50/10 %%%% is higher as the appropriate "
        msg_tpl += "threshold (default: %%(default)s)."

        self.add_arg(
                '-w', '--warning',
                metavar = 'IO_DELAY_90,IO_DELAY_50,IO_DELAY_10',
                dest = 'warning',
                required = True,
                default = ','.join(map(lambda x: ("%d" % (x)), self.warning)),
                help = msg_tpl % ('warning'),
        )

        self.add_arg(
                '-c', '--critical',
                metavar = 'IO_DELAY_90,IO_DELAY_50,IO_DELAY_10',
                dest = 'critical',
                required = True,
                default = ','.join(map(lambda x: ("%d" % (x)), self.critical)),
                help = msg_tpl % ('critical'),
        )

        self.add_arg(
                '-d', '--delay',
                metavar = 'SEC',
                type = float,
                dest = 'delay',
                default = self.delay,
                required = True,
                help = ("Delay between iterations in seconds of refreshing " +
                        "the process list (default: %(default).1f sec)."),
        )

        self.add_arg(
                '-i', '--iterations',
                metavar = 'NUM',
                type = int,
                dest = 'iterations',
                default = self.iterations,
                required = True,
                help = ("Set the number of iterations before calculating "
                        "the reult of this check (default: %(default)s)."),
        )

    #--------------------------------------------------------------------------
    def __call__(self):
        """
        Method to call the plugin directly.
        """

        self.parse_args()
        self.init_root_logger()

        if self.argparser.args.delay < 0.2:
            msg = "The delay must be in minimum 0.2 seconds."
            self.die(msg)
        self.delay = self.argparser.args.delay

        if self.argparser.args.iterations < 1:
            msg = "There must be in minimum one iteration."
            self.die(msg)
        self.iterations = self.argparser.args.iterations

        msg_tpl = ("The %s thresholds must be given in the form " +
                "'IO_DELAY_90,IO_DELAY_50,IO_DELAY_10', where the " +
                "values are integer values.")
        re_limits = re.compile(r'^\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*$')

        match = re_limits.search(self.argparser.args.warning)
        if not match:
            self.die(msg_tpl % ('warning'))
        self.warning = (int(match.group(1)), int(match.group(2)),
                int(match.group(3)))

        match = re_limits.search(self.argparser.args.critical)
        if not match:
            self.die(msg_tpl % ('critical'))
        self.critical = (int(match.group(1)), int(match.group(2)),
                int(match.group(3)))

        if self.verbose > 1:
            log.debug("Got thresholds: warning: %r, critical: %r.",
                    self.warning, self.critical)
            log.debug("Number of iterations: %d, delay between: %.1f seconds.",
                    self.iterations, self.delay)
            log.debug("Initialisation complete.")

        if os.geteuid():
            self.die("This plugin must be executed as root.")

        self.get_proc_stats()
        self.evaluate_proc_stats()

        state = nagios.state.ok

        if (self.process_count['90'] >= self.critical[0] or
                self.process_count['50'] >= self.critical[1] or
                self.process_count['10'] >= self.critical[2]):
            state = nagios.state.critical
        elif (self.process_count['90'] >= self.warning[0] or
                self.process_count['50'] >= self.warning[1] or
                self.process_count['10'] >= self.warning[2]):
            state = nagios.state.warning

        msg = "Total %(total)d procs, %(90)d procs with i/o delay >= 90%%, "
        msg += "%(50)d procs with i/o delay >= 50%% and %(10)d procs with "
        msg += "i/o delay >= 10%%."
        out = msg % self.process_count

        self.exit(state, out)

    #--------------------------------------------------------------------------
    def get_proc_stats(self):

        if self.verbose > 2:
            log.debug("Init of iotop objects  ...")

        self.iotop_opts = IotopOptions(only = True, batch = True,
                processes = True, iterations = self.iterations, accumulated = True)

        self.connection = TaskStatsNetlink(self.iotop_opts)
        self.process_list = ProcessList(self.connection, self.iotop_opts)

        for j in range(self.iterations):
            time.sleep(self.delay)
            if self.verbose > 1:
                log.debug("Refreshing processlist %d ...", j)
            total, actual = self.process_list.refresh_processes()

    #--------------------------------------------------------------------------
    def evaluate_proc_stats(self):

        for proc in self.process_list.processes.values():
            self.processes.append(proc)

        i = 0
        duration = self.process_list.duration
        for proc in self.processes:
            i += 1
            blkio_delay = 0
            proc_duration = duration
            blkio_delay = proc.stats_accum.blkio_delay_total
            proc_duration = time.time() - proc.stats_accum_timestamp
            blkio_delay_percent = float(blkio_delay) / (proc_duration * 10000000.0)

            self.process_count['total'] += 1
            if blkio_delay_percent >= 90:
                self.process_count['90'] += 1
            elif blkio_delay_percent >= 50:
                self.process_count['50'] += 1
            elif blkio_delay_percent >= 10:
                self.process_count['10'] += 1

        self.process_count['0'] = (self.process_count['total'] -
                self.process_count['90'] - self.process_count['50'] -
                self.process_count['10'])

        if self.verbose > 1:
            log.debug("Got the following results:\n%s", pp(self.process_count))

#==============================================================================

if __name__ == "__main__":

    pass

#==============================================================================

# vim: fileencoding=utf-8 filetype=python ts=4 et sw=4
