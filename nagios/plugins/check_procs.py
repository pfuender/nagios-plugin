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
import pwd
import re
import locale

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

__version__ = '0.5.0'

log = logging.getLogger(__name__)

PS_CMD = os.sep + os.path.join('bin', 'ps')

PID_MAX_FILE = os.sep + os.path.join('proc', 'sys', 'kernel', 'pid_max')

valid_metrics = {
        'PROCS':   {'uom': '',       'label': 'procs'},
        'VSZ':     {'uom': 'KiByte', 'label': 'vsz'},
        'RSS':     {'uom': 'KiByte', 'label': 'rss'},
        'CPU':     {'uom': '%',      'label': 'cpu'},
        'ELAPSED': {'uom': 'sec',    'label': 'elapsed_time'},
}

# Valid process state codes, taken from the ps-manpage
process_state = {
        'D':    'uninterruptible sleep',
        'R':    'running or runnable',
        'S':    'interruptible sleep',
        'T':    'stopped or being traced',
        'W':    'paging',
        'X':    'dead',
        'Z':    'defunct ("zombie") process',
        '<':    'high-priority',
        'N':    'low-priority',
        'L':    'has pages locked into memory',
        's':    'is a session leader',
        'l':    'is multi-threaded',
        '+':    'is in the foreground process group',
}

re_integer = re.compile(r'^\s*(\d+)\s*$')

# Contstructing the regex for parsing the output of ps command
match_ps_line = r'^\s*(?P<user>\S+)'
match_ps_line += r'\s+(?P<pid>\d+)'
match_ps_line += r'\s+(?P<ppid>\d+)'
match_ps_line += r'\s+(?P<state>\S+)'
match_ps_line += r'\s+(?P<pcpu>-|\d+(?:\.\d*)?)'
match_ps_line += r'\s+(?P<vsz>\d+)'
match_ps_line += r'\s+(?P<rss>\d+)'
match_ps_line += r'\s+(?P<time>(?:(?:\d+-)?\d+:)?\d+:\d+)'
match_ps_line += r'\s+(?P<comm>\S+)'
match_ps_line += r'\s+(?P<args>.*)'
match_ps_line += r'\s*$'

re_ps_line = re.compile(match_ps_line)

# Parsing time description
pattern_time = r'\s*(?:(?:(?P<days>\d+)-)?(?P<hours>\d+):)?'
pattern_time += r'(?P<mins>\d+):(?P<secs>\d+)'
if __name__ == '__main__':
    print("Search pattern for a time description: %r" % (pattern_time))
re_time = re.compile(pattern_time)

re_percent = re.compile(r'^\s*(\d+(?:\.\d*)?)\s*%\s*$')

#==============================================================================
class ProcessInfo(object):
    """
    A class capsulating process informations.
    """

    #--------------------------------------------------------------------------
    def __init__(self,
            user, pid, ppid, state, pcpu, vsz, rss, time, comm, args):
        """
        Constructor.

        @param user: effective user name
        @type user: str
        @param pid: process ID number of the process
        @type pid: str or int
        @param ppid: parent process ID
        @type ppid: str or int
        @param state: state of the process as a multicharacter identifier
        @type state: str
        @param pcpu: cpu utilization of the process
        @type pcpu: str or float
        @param vsz: virtual memory size of the process in KiB
        @type vsz: str or int
        @param rss: resident set size in kiloBytes
        @type rss: str or int
        @param time: cumulative CPU time in "[DD-]HH:MM:SS" format.
        @type time: str
        @param comm: command name (only the executable name)
        @type comm: str
        @param args: command with all its arguments
        @type args: str

        """

        self._user = None
        self._uid = None
        self.user = user

        self._pid = None
        self.pid = pid

        self._ppid = None
        self.ppid = ppid

        self._state = set([])
        self.state = state

        self._pcpu = 0.0
        self.pcpu = pcpu

        self._vsz = 0
        self.vsz = vsz

        self._rss = 0
        self.rss = rss

        self._time = 0
        self.time = time

        self._comm = str(comm)
        self._args = str(args)

    #------------------------------------------------------------
    @property
    def user(self):
        """The effective user name."""
        return self._user

    @user.setter
    def user(self, value):
        match = re_integer.search(value)
        if match:
            self._user = match.group(1)
            self._uid = int(self._user)
        else:
            usr = value.strip()
            uid = -1
            try:
                uid = pwd.getpwnam(usr).pw_uid
            except KeyError as e:
                log.debug("Invalid user name %r in process list.", usr)
                uid = -1
            self._user = usr
            self._uid = uid

    #------------------------------------------------------------
    @property
    def uid(self):
        """The UID of the effective user."""
        return self._uid

    #------------------------------------------------------------
    @property
    def pid(self):
        """The process ID number of the process."""
        return self._pid

    @pid.setter
    def pid(self, value):
        self._pid = int(value)

    #------------------------------------------------------------
    @property
    def ppid(self):
        """The parent process ID number."""
        return self._ppid

    @ppid.setter
    def ppid(self, value):
        self._ppid = int(value)

    #------------------------------------------------------------
    @property
    def state(self):
        """The state of the process."""
        return self._state

    @state.setter
    def state(self, value):
        self._state = set([])
        for char in value[:]:
            self._state.add(char)

    #------------------------------------------------------------
    @property
    def state_desc(self):
        """Textual description of the process states."""

        desc_list = []
        for char in sorted(self._state):
            desc = "Unknown state %r" % (char)
            if char in process_state:
                desc = process_state[char]
            desc_list.append(desc)

        return ', '.join(desc_list)

    #------------------------------------------------------------
    @property
    def pcpu(self):
        """The cpu utilization of the process in percent."""
        return self._pcpu

    @pcpu.setter
    def pcpu(self, value):

        self._pcpu = 0.0
        if isinstance(value, Number):
            self._pcpu = float(value)
            return

        if value and value != '-':
            self._pcpu = float(value.strip())

    #------------------------------------------------------------
    @property
    def vsz(self):
        """The virtual memory size of the process in KiB."""
        return self._vsz

    @vsz.setter
    def vsz(self, value):
        self._vsz = 0
        if isinstance(value, Number):
            self._vsz = int(value)
            return
        self._vsz = int(value.strip())

    #------------------------------------------------------------
    @property
    def rss(self):
        """The resident set size of the process in KiB."""
        return self._rss

    @rss.setter
    def rss(self, value):
        self._rss = 0
        if isinstance(value, Number):
            self._rss = int(value)
            return
        self._rss = int(value.strip())

    #------------------------------------------------------------
    @property
    def time(self):
        """The cumulative CPU time in seconds."""
        return self._time

    @time.setter
    def time(self, value):
        self._time = 0
        if isinstance(value, Number):
            self._time = int(value)
            return

        match = re_time.search(value)
        if match:
            self._time = 60 * int(match.group('mins'))
            self._time += int(match.group('secs'))
            if match.group('hours'):
                self._time += 60 * 60 * int(match.group('hours'))
            if match.group('days'):
                self._time += 24 * 60 * 60 * int(match.group('days'))
        else:
            log.warn("Could not parse time description %r.", value)

    #------------------------------------------------------------
    @property
    def time_desc(self):
        """Textual description of the cumulative CPU time."""

        t = self._time

        secs = t % 60
        t = (t - secs) / 60

        mins = t % 60
        t = (t - mins) / 60

        hours = t % 24
        days = (t - hours) / 24

        out = "%02d:%02d:%02d" % (hours, mins, secs)
        if days:
            out = ("%d-" % (days)) + out

        return out

    #------------------------------------------------------------
    @property
    def comm(self):
        """The command name (only the executable name)."""
        return self._comm

    #------------------------------------------------------------
    @property
    def args(self):
        """The command with all its arguments."""
        return self._args

    #--------------------------------------------------------------------------
    def as_dict(self):
        """Transforms the elements of the object into a dict."""

        d = {}
        d['__class_name__'] = self.__class__.__name__
        d['user'] = self.user
        d['uid'] = self.uid
        d['pid'] = self.pid
        d['ppid'] = self.ppid
        d['state'] = self.state
        d['state_desc'] = self.state_desc
        d['pcpu'] = self.pcpu
        d['vsz'] = self.vsz
        d['rss'] = self.rss
        d['time'] = self.time
        d['time_desc'] = self.time_desc
        d['comm'] = self.comm
        d['args'] = self.args

        return d

    #--------------------------------------------------------------------------
    def __str__(self):
        """
        Typecasting function for translating object structure into a string.
        """

        return pp(self.as_dict())

    #--------------------------------------------------------------------------
    def __repr__(self):
        """Typecasting into a string for reproduction."""

        out = "<%s(" % (self.__class__.__name__)

        fields = []
        fields.append("user=%r" % (self.user))
        fields.append("pid=%r" % (self.pid))
        fields.append("ppid=%r" % (self.ppid))
        fields.append("state=%r" % (''.join(self.state)))
        fields.append("pcpu=%r" % (self.pcpu))
        fields.append("vsz=%r" % (self.vsz))
        fields.append("rss=%r" % (self.rss))
        fields.append("time=%r" % (self.time))
        fields.append("comm=%r" % (self.comm))
        fields.append("args=%r" % (self.args))

        out += ", ".join(fields) + ")>"

        return out


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
                usage = usage, blurb = blurb,
        )

        self._ps_cmd = PS_CMD
        """
        @ivar: the underlaying 'ps' command
        @type: str
        """
        if not os.path.exists(self.ps_cmd) or not os.access(
                self.ps_cmd, os.X_OK):
            self._ps_cmd = self.get_command('ps')

        self._user = None
        """
        @ivar: Only scan for processes with user name or ID indicated.
        @type: str
        """

        self._pid_max = 2 ** 15
        """
        @ivar: The maximum number of processes in the system,
               defaults to 32768
        @type: int
        """

        self._warning = NagiosRange(self.pid_max * 70 / 100)
        """
        @ivar: the warning threshold of the test, defaults to
               70 % of the maximum number of processes in the system
        @type: NagiosRange
        """

        self._critical = NagiosRange(self.pid_max * 90 / 100)
        """
        @ivar: the critical threshold of the test, defaults to
               90 % of the maximum number of processes in the system
        @type: NagiosRange
        """

        self._add_args()

    #------------------------------------------------------------
    @property
    def pid_max(self):
        """The maximum number of processes in the system, defaults to 32768."""
        return self._pid_max

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

    #------------------------------------------------------------
    @property
    def ps_cmd(self):
        """The absolute path to the OS command 'ps'."""
        return self._ps_cmd

    #------------------------------------------------------------
    @property
    def user(self):
        """Only scan for processes with user name or ID indicated."""
        return self._user

    @user.setter
    def user(self, value):

        uid = None
        user = None
        if isinstance(value, Number):
            uid = int(value)
        else:
            match = re_integer.search(value)
            if match:
                uid = int(match.group(1))
            else:
                user = str(value).strip()

        if uid is not None:
            try:
                user = pwd.getpwuid(uid).pw_name
            except KeyError as e:
                log.warn("Invalid UID %d.", uid)
                return
        else:
            try:
                uid = pwd.getpwnam(user).pw_uid
            except KeyError as e:
                log.warn("Invalid user name %r.", user)
                return

        self._user = user

    #--------------------------------------------------------------------------
    def as_dict(self):
        """
        Typecasting into a dictionary.

        @return: structure as dict
        @rtype:  dict

        """

        d = super(CheckProcsPlugin, self).as_dict()

        d['ps_cmd'] = self.ps_cmd
        d['user'] = self.user
        d['pid_max'] = self.pid_max
        d['warning'] = self.warning
        d['critical'] = self.critical

        return d

    #--------------------------------------------------------------------------
    def _add_args(self):
        """
        Adding all necessary arguments to the commandline argument parser.
        """

        msg_p  = "If given as a percentage, the range will taken as percent of "
        msg_p += "the maximum number of processes of the system (taken from "
        msg_p += "/proc/sys/kernel/pid_max)."

        msg = "Generate warning state if metric is outside this range. " + msg_p

        self.add_arg(
                '-w', '--warning',
                metavar = 'RANGE',
                dest = 'warning',
                required = True,
                help = msg,
        )

        msg = "Generate critical state if metric is outside this range. " + msg_p

        self.add_arg(
                '-c', '--critical',
                metavar = 'RANGE',
                dest = 'critical',
                required = True,
                help = msg,
        )

        self.add_arg(
                '-m', '--metric',
                choices = sorted(valid_metrics.keys()),
                dest = 'metric',
                required = True,
                default = 'PROCS',
                help = "Check thresholds against metric (default: %(default)s).",
        )

        default_ps = PS_CMD
        if self.ps_cmd:
            default_ps = self.ps_cmd
        self.add_arg(
                '--ps-cmd',
                dest = 'ps_cmd',
                required = True,
                default = default_ps,
                help = "The ps-command (default: %(default)r).",
        )

        state_help = """\
        Only scan for processes that have, in the output of 'ps', one or
        more of the status flags you specify (for example R, Z, S, RS,
        RSZDT, plus others based on the output of your 'ps' command).
        """
        state_help = textwrap.dedent(state_help).strip()

        self.add_arg(
                '-s', '--state',
                metavar = 'STATE',
                dest = 'state',
                help = state_help
        )

        self.add_arg(
                '-p', '--ppid',
                type = int,
                metavar = 'PID',
                dest = 'ppid',
                help = 'Only scan for children of the parent process ID indicated.',
        )

        self.add_arg(
                '-z', '--vsz',
                type = int,
                dest = 'vsz',
                help = 'Only scan for processes with virtual size higher than indicated.',
        )

        self.add_arg(
                '-r', '--rss',
                type = int,
                dest = 'rss',
                help = 'Only scan for processes with rss higher than indicated.',
        )

        self.add_arg(
                '-P', '--pcpu',
                type = int,
                dest = 'pcpu',
                help = 'Only scan for processes with pcpu higher than indicated.',
        )

        self.add_arg(
                '-u', '--user',
                dest = 'user',
                help = 'Only scan for processes with user name or UID indicated.',
        )

        self.add_arg(
                '-a', '--args',
                metavar = 'STRING',
                dest = 'args',
                help = 'Only scan for processes with args that contain STRING.',
        )

        #--ereg-argument-array=
        self.add_arg(
                '--preg-argument-array', '--ereg-argument-array', '--regex',
                metavar = 'STRING',
                dest = 'regex',
                help = ('Only scan for processes with args that contain ' +
                        'the Perl regeular expression STRING.'),
        )

        self.add_arg(
                '-C', '--command',
                metavar = 'STRING',
                dest = 'command',
                help = 'Only scan for exact matches of STRING (without path).',
        )

        self.add_arg(
                '-i', '--init',
                action = 'store_true',
                dest = 'init',
                help = 'Only scan for processes, they are direct childs of init.',
        )

    #--------------------------------------------------------------------------
    def __call__(self):
        """
        Method to call the plugin directly.
        """

        self.parse_args()
        self.init_root_logger()

        ps_cmd = PS_CMD
        if self.argparser.args.ps_cmd:
            self._ps_cmd = self.get_command(self.argparser.args.ps_cmd)
            ps_cmd = self.argparser.args.ps_cmd
        if not self.ps_cmd:
            msg = "Command %r not found." % (ps_cmd)
            self.die(msg)

        if os.path.exists(PID_MAX_FILE):
            log.debug("Reading %r ...", PID_MAX_FILE)
            self._pid_max = int(self.read_file(PID_MAX_FILE, quiet = True))
            log.debug("Got a pid_max value of %d processes.", self._pid_max)
            self._warning = NagiosRange(self.pid_max * 70 / 100)
            self._critical = NagiosRange(self.pid_max * 90 / 100)

        if self.argparser.args.user:
            self.user = self.argparser.args.user
            if self.user is None:
                msg = "Invalid user name or UID %r given." % (
                        self.argparser.args.user)
                self.die(msg)

        match = re_percent.search(self.argparser.args.warning)
        if match:
            percent = float(match.group(1))
            warning = int(self.pid_max * percent / 100)
            self._warning = NagiosRange(warning)
        else:
            self._warning = NagiosRange(self.argparser.args.warning)

        match = re_percent.search(self.argparser.args.critical)
        if match:
            percent = float(match.group(1))
            critical = int(self.pid_max * percent / 100)
            self._critical = NagiosRange(critical)
        else:
            self._critical = NagiosRange(self.argparser.args.critical)

        if self.verbose > 1:
            log.debug("Got thresholds: warning: %s, critical: %s.",
                    self.warning, self.critical)

        self.set_thresholds(
                warning = self.warning,
                critical = self.critical,
        )

        if self.verbose > 2:
            log.debug("Current object:\n%s", pp(self.as_dict()))

        uom = self.get_uom()
        label = self.get_label()

        found_processes = self.collect_processes()
        value_total = self.get_total_value(found_processes)
        count = len(found_processes)

        log.debug("Got a total value (by %s) of %d%s.",
                self.argparser.args.metric, value_total, uom)

        state = self.threshold.get_status(value_total)
        self.add_perfdata(
                label = label,
                value = value_total,
                uom = uom,
                threshold = self.threshold,
        )

        plural = ''
        if count != 1:
            plural = 'es'
        out = "%d process%s" % (count, plural)
        fdescription = self.get_filter_description()
        if fdescription:
            out += ' with ' + fdescription

        self.exit(state, out)

    #--------------------------------------------------------------------------
    def get_filter_description(self):
        """Retrieves a description for the current filter of processes."""

        decriptions = []

        if self.argparser.args.init:
            decriptions.append("init child")
        if self.argparser.args.state:
            decriptions.append("state %r" % (self.argparser.args.state))
        if self.argparser.args.ppid is not None:
            decriptions.append("PPID %d" % (self.argparser.args.ppid))
        if self.user:
            decriptions.append("user %r" % (self.user))
        if self.argparser.args.command:
            decriptions.append("command %r" % (self.argparser.args.command))
        if self.argparser.args.args:
            decriptions.append("args %r" % (self.argparser.args.args))
        if self.argparser.args.regex:
            decriptions.append("regex %r" % (self.argparser.args.regex))
        if self.argparser.args.vsz:
            decriptions.append("vsz >%dKiByte" % (self.argparser.args.vsz))
        if self.argparser.args.rss:
            decriptions.append("rss >%dKiByte" % (self.argparser.args.rss))
        if self.argparser.args.pcpu:
            decriptions.append("pcpu >%d%%" % (self.argparser.args.pcpu))

        return ', '.join(decriptions)

    #--------------------------------------------------------------------------
    def get_total_value(self, found_processes):
        """Computing the total value of the metric to check."""

        value_total = 0

        metric = self.argparser.args.metric

        for pinfo in found_processes:

            value = 1
            if metric == 'VSZ':
                value = pinfo.vsz
            elif metric == 'RSS':
                value = pinfo.rss
            elif metric == 'CPU':
                value = pinfo.pcpu
            elif metric == 'ELAPSED':
                value = pinfo.time

            value_total += value

        return value_total

    #--------------------------------------------------------------------------
    def get_uom(self):
        """Returns the unit of measuring dependend of the metric to retrieve."""

        metric = self.argparser.args.metric
        return valid_metrics[metric]['uom']

    #--------------------------------------------------------------------------
    def get_label(self):
        """Returns the label for the performance data dependend
        of the metric to retrieve."""

        metric = self.argparser.args.metric
        return valid_metrics[metric]['label']

    #--------------------------------------------------------------------------
    def collect_processes(self):
        """The main routine of this plugin."""

        args_pattern = None
        re_args = None
        if self.argparser.args.args:
            args_pattern = re.escape(self.argparser.args.args)
            try:
                re_args = re.compile(args_pattern)
            except Exception as e:
                msg = "Invalid search pattern %r for arguments: %s" % (
                        self.argparser.args.args, str(e))
                self.die(msg)
            log.debug("Searching for processes with pattern %r ...",
                    args_pattern)

        re_pattern = None
        re_regex = None
        if self.argparser.args.regex:
            re_pattern = self.argparser.args.regex
            try:
                re_regex = re.compile(re_pattern)
            except Exception as e:
                msg = "Invalid regular expression %r for arguments: %s" % (
                        re_pattern, str(e))
                self.die(msg)
            log.debug("Searching for processes with regular expression %r ...",
                    re_pattern)

        fields = ('user', 'pid', 'ppid', 'stat', 'pcpu', 'vsz', 'rss', 'time',
                'comm', 'args')

        cmd = [self.ps_cmd, '-e', '-o', ','.join(fields)]
        stdoutdata = ''
        stderrdata = ''

        current_locale = os.environ.get('LC_NUMERIC')
        if self.verbose > 2:
            log.debug("Current locale is %r, setting to 'C'.", current_locale)
        os.environ['LC_NUMERIC'] = 'C'

        try:
            (ret, stdoutdata, stderrdata) = self.exec_cmd(cmd)
        finally:
            if current_locale:
                os.environ['LC_NUMERIC'] = current_locale
            else:
                del os.environ['LC_NUMERIC']

        if self.verbose > 3:
            log.debug("Got from STDOUT:\n%s", stdoutdata)
            log.debug("Got from STDERR:\n%s", stderrdata)

        lines = stdoutdata.splitlines()

        found_processes = []

        for line in lines[1:]:

            pinfo = self._parse_process_line(line)
            if not pinfo:
                log.warn("Could not parse output line of ps: %r", line)
                continue

            if pinfo.pid == os.getpid():
                # Ignore myself
                if self.verbose > 2:
                    log.debug("Ignoring myself.")
                continue

            if pinfo.ppid == os.getpid():
                # Ignore the process of the ps-command initiated by myself
                if self.verbose > 2:
                    log.debug("Ignoring self initiated process.")
                continue

            if self.argparser.args.init and pinfo.ppid != 1:
                continue

            if self.argparser.args.ppid is not None:
                if pinfo.ppid != self.argparser.args.ppid:
                    continue

            if self.argparser.args.state:
                found = False
                state = self.argparser.args.state
                for char in state:
                    if char in pinfo.state:
                        found = True
                        break
                if found:
                    if self.verbose > 2:
                        log.debug("State %r found in %r (%d).", state,
                                pinfo.state, pinfo.pid)
                else:
                    if self.verbose > 3:
                        log.debug("State %r not found in %r (%d).", state,
                                pinfo.state, pinfo.pid)
                    continue

            if self.user:
                if pinfo.user != self.user:
                    if self.verbose > 2:
                        log.debug("Ignoring process %d of user %r.",
                            pinfo.pid, pinfo.user)
                    continue

            if self.argparser.args.command:
                if pinfo.comm != self.argparser.args.command:
                    continue

            if re_regex:
                if not re_regex.search(pinfo.args):
                    continue

            if re_args:
                if not re_args.search(pinfo.args):
                    continue

            if self.argparser.args.vsz:
                if pinfo.vsz < self.argparser.args.vsz:
                    continue

            if self.argparser.args.rss:
                if pinfo.rss < self.argparser.args.rss:
                    continue

            if self.argparser.args.pcpu:
                if pinfo.pcpu < float(self.argparser.args.pcpu):
                    continue

            found_processes.append(pinfo)

        # What did we found:
        if self.verbose > 2:
            if found_processes:
                r = []
                for pinfo in found_processes:
                    r.append(repr(pinfo))
                procs = ',\n'.join(r)
                log.debug("Processes to regard:\n%s", procs)
            else:
                log.debug("No processes to regard.")

        return found_processes

    #--------------------------------------------------------------------------
    def _parse_process_line(self, line):
        """Parsing a line how given back from the ps command."""

        match = re_ps_line.search(line)
        if not match:
            return None

        kwords = match.groupdict()

        pinfo = ProcessInfo(**kwords)
        if self.verbose > 3:
            log.debug("Got process info: %s", pinfo)

        return pinfo

#==============================================================================

if __name__ == "__main__":

    pass

#==============================================================================

# vim: fileencoding=utf-8 filetype=python ts=4 et
