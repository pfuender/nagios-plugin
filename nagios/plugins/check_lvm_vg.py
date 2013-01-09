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
    def __init__(self, vg, vgs_cmd = VGS_CMD, verbose = 0, **kwargs):
        """
        Constructor.

        @param vg: the name of the volume group
        @type vg: str
        @param vgs_cmd: the path to the vgs command
        @type vgs_cmd: str
        @param verbose: the verbosity level
        @type verbose: int

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
        if self.checked:
            fields.append("checked=%r" % (self.checked))
            fields.append("attr=%r" % (self.attr))
            fields.append("ext_size=%r" % (self.ext_size))
            fields.append("ext_count=%r" % (self.ext_count))
            fields.append("ext_free=%r" % (self.ext_free))

        out += ", ".join(fields) + ")>"
        return out

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

        state = nagios.state.ok
        self.exit(state, "The stars are shining above us...")

        # vgs --unit m --noheadings --nosuffix --separator ';' --unbuffered \
        #   -o vg_fmt,vg_name,vg_attr,vg_size,vg_free,vg_extent_size,vg_extent_count,vg_free_count storage

#==============================================================================

if __name__ == "__main__":

    pass

#==============================================================================

# vim: fileencoding=utf-8 filetype=python ts=4
