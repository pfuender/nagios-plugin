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
import locale
import math

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

from nagios.plugins import ExtNagiosPluginError
from nagios.plugins import ExecutionTimeoutError
from nagios.plugins import CommandNotFoundError
from nagios.plugins import ExtNagiosPlugin

#---------------------------------------------
# Some module variables

__version__ = '0.1.0'

log = logging.getLogger(__name__)

VGS_CMD = os.sep + os.path.join('sbin', 'vgs')

vg_attribute = {
        'w': 'writeable',
        'r': 'readonly',
        'z': 'resizeable',
        'x': 'exported',
        'p': 'partial physical volumes',
        'c': 'contiguous allocation',
        'l': 'cling allocation',
        'n': 'normal allocation',
        'a': 'anywhere allocated',
        'i': 'inherited allocation',
        'C': 'clustered',
}

re_number_abs = re.compile(r'^\s*(\d+)\s*$')
re_number_percent = re.compile(r'^\s*(\d+)\s*%\s*$')

#==============================================================================
class VgNotExistsError(ExtNagiosPluginError):
    """Special exception indicating, that the volume group doesn't exists."""

    #--------------------------------------------------------------------------
    def __init__(self, vg):
        self.vg = vg

    #--------------------------------------------------------------------------
    def __str__(self):
        return "Volume group %r doesn't exists." % (self.vg)

#==============================================================================
class LvmVgState(object):
    """
    A class for enapsulating and retrieving the state of an existing
    LVM volume group.
    """

    #--------------------------------------------------------------------------
    def __init__(self, vg, vgs_cmd = VGS_CMD, verbose = 0, timeout = 15, **kwargs):
        """
        Constructor.

        @param vg: the name of the volume group
        @type vg: str
        @param vgs_cmd: the path to the vgs command
        @type vgs_cmd: str
        @param verbose: the verbosity level
        @type verbose: int
        @param timeout: the timeout in execution the 'vgs' command
        @type timeout: int

        """

        self._vg = vg
        """
        @ivar: the name of the volume group
        @type: str
        """

        self._vgs_cmd = vgs_cmd
        """
        @ivar: the underlaying 'vgs' command
        @type: str
        """

        self._verbose = verbose
        """
        @ivar: the verbosity level
        @type: int
        """

        self._timeout = timeout
        """
        @ivar: the timeout in execution the 'vgs' command
        @type: int
        """

        self._checked = bool(kwargs.get('checked', False))
        """
        @ivar: flag, that the state of VG was even checked.
        @type: bool
        """

        self._format = kwargs.get('format', None)
        """
        @ivar: LVM format of the VG
        @type: str
        """

        self._attr = kwargs.get('attr', None)
        """
        @ivar: the attributes of the VG
        @type: set
        """

        self._ext_size = None
        """
        @ivar: the extent size of the VG in MiBytes
        @type: int
        """
        if 'ext_size' in kwargs:
            self._ext_size = int(kwargs.get('ext_size'))

        self._ext_count = None
        """
        @ivar: the total extent count of the VG
        @type: int
        """
        if 'ext_count' in kwargs:
            self._ext_count = int(kwargs.get('ext_count'))

        self._ext_free = None
        """
        @ivar: the count of free extents of the VG
        @type: int
        """
        if 'ext_free' in kwargs:
            self._ext_free = int(kwargs.get('ext_free'))

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
    def verbose(self):
        """The verbosity level."""
        return self._verbose

    #------------------------------------------------------------
    @property
    def timeout(self):
        """The timeout in execution the 'vgs' command."""
        return self._timeout

    #------------------------------------------------------------
    @property
    def checked(self):
        """A flag, that the state of VG was even checked."""
        return self._checked

    #------------------------------------------------------------
    @property
    def format(self):
        """The LVM format of the VG."""
        return self._format

    #------------------------------------------------------------
    @property
    def attr(self):
        """The attributes of the VG."""
        return self._attr

    #------------------------------------------------------------
    @property
    def attr_str(self):
        """A textual representation of the state of the vg."""

        if self._attr is None:
            return None

        if not self._attr:
            return 'unknown'

        descs = []
        # for the correct order:
        for char in ('w', 'r', 'z', 'x', 'p', 'c', 'l', 'n', 'a', 'i', 'C'):
            if char in self._attr:
                descs.append(vg_attribute[char])

        return ', '.join(descs)

    #------------------------------------------------------------
    @property
    def attr_vgs(self):
        """The attributes of the VG in a representation like in vgs."""

        if self._attr is None:
            return None

        chars = ['-', '-', '-', '-', '-', '-']

        if 'w' in self._attr:
            chars[0] = 'w'
        elif 'r' in self._attr:
            chars[0] = 'r'

        if 'z' in self._attr:
            chars[1] = 'z'

        if 'x' in self._attr:
            chars[2] = 'x'

        if 'p' in self._attr:
            chars[3] = 'p'

        for char in ('c', 'l', 'n', 'a', 'i'):
            if char in self._attr:
                chars[4] = char
                break

        if 'C' in self._attr:
            chars[5] = 'c'

        return ''.join(chars)

    #------------------------------------------------------------
    @property
    def ext_size(self):
        """The extent size of the VG in MiBytes."""
        return self._ext_size

    #------------------------------------------------------------
    @property
    def ext_count(self):
        """The total extent count of the VG."""
        return self._ext_count

    #------------------------------------------------------------
    @property
    def size(self):
        """The total size of the VG in Bytes."""

        if self.ext_size is None or self.ext_count is None:
            return None

        return long(self.ext_size) * long(self.ext_count) * 1024l * 1024l

    #------------------------------------------------------------
    @property
    def size_mb(self):
        """The total size of the VG in MiBytes."""

        if self.ext_size is None or self.ext_count is None:
            return None
        return self.ext_size * self.ext_count

    #------------------------------------------------------------
    @property
    def ext_free(self):
        """The count of free extents of the VG."""
        return self._ext_free

    #------------------------------------------------------------
    @property
    def free(self):
        """The free size of the VG in Bytes."""

        if self.ext_size is None or self.ext_free is None:
            return None

        return long(self.ext_size) * long(self.ext_free) * 1024l * 1024l

    #------------------------------------------------------------
    @property
    def free_mb(self):
        """The free size of the VG in MiBytes."""

        if self.ext_size is None or self.ext_free is None:
            return None

        return self.ext_size * self.ext_free

    #------------------------------------------------------------
    @property
    def percent_free(self):
        """The percentage of free space in the VG."""

        if (self.ext_count is None or self.ext_free is None or
                self.ext_count == 0):
            return None

        return (float(self.ext_free) / float(self.ext_count)) * 100.0

    #------------------------------------------------------------
    @property
    def ext_used(self):
        """The count of used extents of the VG."""

        if self.ext_count is None or self.ext_free is None:
            return None

        return self.ext_count - self.ext_free

    #------------------------------------------------------------
    @property
    def used(self):
        """The used size of the VG in Bytes."""

        if self.ext_size is None or self.ext_used is None:
            return None

        return long(self.ext_size) * long(self.ext_used) * 1024l * 1024l

    #------------------------------------------------------------
    @property
    def used_mb(self):
        """The used size of the VG in MiBytes."""

        if self.ext_size is None or self.ext_used is None:
            return None

        return self.ext_size * self.ext_used

    #------------------------------------------------------------
    @property
    def percent_used(self):
        """The percentage of used space in the VG."""

        if (self.ext_count is None or self.ext_used is None or
                self.ext_count == 0):
            return None

        return (float(self.ext_used) / float(self.ext_count)) * 100.0

    #--------------------------------------------------------------------------
    def as_dict(self):
        """
        Typecasting into a dictionary.

        @return: structure as dict
        @rtype:  dict

        """

        d = {}
        d['__class__'] = self.__class__.__name__
        d['vg'] = self.vg
        d['vgs_cmd'] = self.vgs_cmd
        d['verbose'] = self.verbose
        d['timeout'] = self.timeout
        d['checked'] = self.checked
        d['format'] = self.format
        d['attr'] = self.attr
        d['attr_str'] = self.attr_str
        d['attr_vgs'] = self.attr_vgs
        d['ext_size'] = self.ext_size
        d['ext_count'] = self.ext_count
        d['size'] = self.size
        d['size_mb'] = self.size_mb
        d['ext_free'] = self.ext_free
        d['free'] = self.free
        d['free_mb'] = self.free_mb
        d['percent_free'] = self.percent_free
        d['ext_used'] = self.ext_used
        d['used'] = self.used
        d['used_mb'] = self.used_mb
        d['percent_used'] = self.percent_used

        return d

    #--------------------------------------------------------------------------
    def __str__(self):
        """
        Typecasting function for translating object structure into a string.

        @return: structure as string
        @rtype:  str

        """

        return pp(self.as_dict())

    #--------------------------------------------------------------------------
    def __repr__(self):
        """Typecasting into a string for reproduction."""

        out = "<%s(" % (self.__class__.__name__)

        fields = []
        fields.append("vg=%r" % (self.vg))
        fields.append("vgs_cmd=%r" % (self.vgs_cmd))
        fields.append("verbose=%r" % (self.verbose))
        fields.append("timeout=%r" % (self.timeout))
        if self.checked:
            fields.append("checked=%r" % (self.checked))
            fields.append("attr=%r" % (self.attr))
            fields.append("ext_size=%r" % (self.ext_size))
            fields.append("ext_count=%r" % (self.ext_count))
            fields.append("ext_free=%r" % (self.ext_free))

        out += ", ".join(fields) + ")>"
        return out

    #--------------------------------------------------------------------------
    def get_data(self, force = False):
        """
        Main method to retrieve the data about the VG with the 'vgs' command.

        @param force: retrieve data, even if self.checked is True
        @type force: bool

        """

        if self.checked and not force:
            return

        # vgs --unit m --noheadings --nosuffix --separator ';' --unbuffered \
        #   -o vg_fmt,vg_name,vg_attr,vg_size,vg_free,vg_extent_size,vg_extent_count,vg_free_count storage

        fields = ('vg_fmt', 'vg_name', 'vg_attr', 'vg_extent_size',
                    'vg_extent_count', 'vg_free_count')

        cmd = [
                self.vgs_cmd,
                '--unit', 'm',
                '--noheadings', '--nosuffix',
                '--separator', ';',
                '--unbuffered',
                '-o', ','.join(fields),
                self.vg
        ]
        cmd_str = ' '.join(cmd)

        timeout = abs(int(self.timeout))

        output = ''
        def exec_alarm_caller(signum, sigframe):
            raise ExecutionTimeoutError(timeout, cmd_str)

        current_locale = os.environ.get('LC_NUMERIC')
        if self.verbose > 2:
            log.debug("Current locale is %r, setting to 'C'.", current_locale)
        os.environ['LC_NUMERIC'] = 'C'
        signal.signal(signal.SIGALRM, exec_alarm_caller)
        signal.alarm(timeout)

        try:
            output = subprocess.check_output(cmd, stderr = subprocess.STDOUT)
        finally:
            signal.alarm(0)
            if current_locale:
                os.environ['LC_NUMERIC'] = current_locale
            else:
                del os.environ['LC_NUMERIC']

        if self.verbose > 2:
            log.debug("Got output:\n%s", output)

        fields = output.strip().split(';')
        if self.verbose > 2:
            log.debug("Got fields:\n%s", pp(fields))


        self._format = fields[0]
        self._ext_size = int(float(fields[3]))
        self._ext_count = int(fields[4])
        self._ext_free = int(fields[5])

        attr_str = fields[2]
        attr = set([])
        for i in (0, 1, 2, 3, 4):
            if attr_str[i] != '-':
                attr.add(attr_str[i])
        if attr_str[5] == 'c':
            attr.add('C')
        self._attr = attr

        self._checked = True

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
        @ivar: the underlaying 'vgs' command
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
        self._vg = self.argparser.args.vg

        if self.verbose > 2:
            log.debug("Current object:\n%s", pp(self.as_dict()))

        #-----------------------------------------------------------
        # Parameters for check_free
        crit = 0
        crit_is_abs = True
        warn = 0
        warn_is_abs = True

        if not self.check_state:

            match_pc = re_number_percent.search(self.argparser.args.critical)
            match_abs = re_number_abs.search(self.argparser.args.critical)

            if match_pc:
                crit = int(match_pc.group(1))
                crit_is_abs = False
            elif match_abs:
                crit = int(match_abs.group(1))
            else:
                self.die("Invalid critical value %r." % (self.argparser.args.critical))
                return

            match_pc = re_number_percent.search(self.argparser.args.warning)
            match_abs = re_number_abs.search(self.argparser.args.warning)

            if match_pc:
                warn = int(match_pc.group(1))
                warn_is_abs = False
            elif match_abs:
                warn = int(match_abs.group(1))
            else:
                self.die("Invalid warning value %r." % (self.argparser.args.warning))
                return

        #-----------------------------------------------------------
        # Getting current state of VG
        vg_state = LvmVgState(
                vg = self.vg, vgs_cmd = self.vgs_cmd,
                verbose = self.verbose, timeout = self.argparser.args.timeout)

        try:
            vg_state.get_data()
        except (ExecutionTimeoutError, VgNotExistsError),  e:
            self.die(str(e))
        except CalledProcessError, e:
            msg = "The %r command returned %d with the message: %s" % (
                    self.vgs_cmd, e.returncode, e.output)
            self.die(msg)

        if self.verbose > 1:
            log.debug("Got a state of the volume group %r:\n%s",
                    self.vg, vg_state)

        #-----------------------------------------------
        if self.check_state:

            self.add_message(nagios.state.ok,
                    ("Volume group %r seems to be OK." % (self.vg)))

            if 'r' in vg_state.attr:
                self.add_message(nagios.state.warning,
                        ("Volume group %r is in a read-only state." % (self.vg)))

            if not 'z' in vg_state.attr:
                self.add_message(nagios.state.warning,
                        ("Volume group %r is not resizeable." % (self.vg)))

            if 'p' in vg_state.attr:
                self.add_message(nagios.state.critical,
                        (("One or more physical volumes belonging to the " +
                        "volume group %r are missing from the system.") % (
                        self.vg)))

            (state, msg) = self.check_messages()
            self.exit(state, msg)

            #Only for the blinds:
            return

        #-----------------------------------------------
        # And now check free space (or whatever)

        if not vg_state.size_mb:
            self.die("Cannot detect absolute size of volume group %r." % (
                    self.vg))

        c_free_abs = 0
        c_free_pc = 0
        c_used_abs = 0
        c_used_pc = 0
        if crit_is_abs:
            c_free_abs = crit
            c_used_abs = vg_state.size_mb - crit
            c_free_pc = float(crit) / float(vg_state.size_mb) * 100
            c_used_pc = float(c_used_abs) / float(vg_state.size_mb) * 100
        else:
            c_free_pc = float(crit)
            c_used_pc = 100.0 - c_free_pc
            c_free_abs = int(math.ceil(c_free_pc * float(vg_state.size_mb) / 100))
            c_used_abs = vg_state.size_mb - c_free_abs

        w_free_abs = 0
        w_free_pc = 0
        w_used_abs = 0
        w_used_pc = 0
        if warn_is_abs:
            w_free_abs = warn
            w_used_abs = vg_state.size_mb - warn
            w_free_pc = float(warn) / float(vg_state.size_mb) * 100
            w_used_pc = float(w_used_abs) / float(vg_state.size_mb) * 100
        else:
            w_free_pc = float(warn)
            w_used_pc = 100.0 - w_free_pc
            w_free_abs = int(math.ceil(w_free_pc * float(vg_state.size_mb) / 100))
            w_used_abs = vg_state.size_mb - w_free_abs

        if c_free_abs > w_free_abs:
            self.die(("The warning threshold must be greater than the " +
                    "critical threshold."))

        th_free_abs = NagiosThreshold(
                warning = "@%d" % (w_free_abs), critical = "@%d" % (c_free_abs))
        th_used_abs = NagiosThreshold(
                warning = "%d" % (w_used_abs), critical = "%d" % (c_used_abs))
        th_free_pc = NagiosThreshold(
                warning = "@%d" % (w_free_pc), critical = "@%d" % (c_free_pc))
        th_used_pc = NagiosThreshold(
                warning = "%f" % (w_used_pc), critical = "%f" % (c_used_pc))

        if self.verbose > 2:
            log.debug("Thresholds free MBytes:\n%s", pp(th_free_abs.as_dict()))
            log.debug("Thresholds free percent:\n%s", pp(th_free_pc.as_dict()))
            log.debug("Thresholds used MBytes:\n%s", pp(th_used_abs.as_dict()))
            log.debug("Thresholds used percent:\n%s", pp(th_used_pc.as_dict()))

        self.add_perfdata(label = 'total_size', value = vg_state.size_mb,
                uom = 'MiB')
        self.add_perfdata(label = 'free_size', value = vg_state.free_mb,
                uom = 'MiB', threshold = th_free_abs)
        self.add_perfdata(label = 'free_percent',
                value = float("%0.2f" % (vg_state.percent_free)), uom = '%',
                threshold = th_free_pc)
        self.add_perfdata(label = 'alloc_size', value = vg_state.used_mb,
                uom = 'MiB', threshold = th_used_abs)
        self.add_perfdata(label = 'alloc_percent',
                value = float("%0.2f" % (vg_state.percent_used)), uom = '%',
                threshold = th_used_pc)

        state = th_free_abs.get_status(vg_state.free_mb)

        out = "%d MiB total, %d MiB free (%0.1f%%), %d MiB allocated (%0.1f%%)" % (
                vg_state.size_mb, vg_state.free_mb, vg_state.percent_free,
                vg_state.used_mb, vg_state.percent_used)

        self.exit(state, out)

#==============================================================================

if __name__ == "__main__":

    pass

#==============================================================================

# vim: fileencoding=utf-8 filetype=python ts=4
