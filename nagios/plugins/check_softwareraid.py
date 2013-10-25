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
import glob
import errno

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

DEFAULT_TIMEOUT = 3
"""
Default timeout for all reading operations.
"""

#==============================================================================
class RaidState(object):
    """
    Encapsulation class for the state of an MD device.
    """

    #--------------------------------------------------------------------------
    def __init__(self, device):

        self.device = device

        self.array_state = None
        self.degraded = None
        self.nr_raid_disks = None
        self.raid_level = None
        self.suspended = None
        self.sync_action = None
        self.slaves = {}

    #--------------------------------------------------------------------------
    def as_dict(self):

        d = {}
        for key in self.__dict__:
            if key == 'slaves':
                continue
            val = self.__dict__[key]
            d[key] = val

        d['slaves'] = {}
        for sid in self.slaves:
            if not self.slaves[sid]:
                d['slaves'][sid] = None
            else:
                d['slaves'][sid] = self.slaves[sid].as_dict()

        return d

#==============================================================================
class SlaveState(object):
    """
    Encapsulation class for the state of a slave device of a RAID device.
    """

    #--------------------------------------------------------------------------
    def __init__(self, nr, path):

        self.nr = nr
        self.path = path
        self.block_device = None
        self.state = None

    #--------------------------------------------------------------------------
    def as_dict(self):

        d = {}
        for key in self.__dict__:
            val = self.__dict__[key]
            d[key] = val

        return d

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
                usage = usage, blurb = blurb, timeout = DEFAULT_TIMEOUT,
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
    def collect_devices(self):
        """
        Method to collect all MD devices and to store them in self.devices.
        """

        mddev_pattern = os.sep + os.path.join('sys', 'block', 'md*')
        log.debug("Collecting all MD devices with %r ...", mddev_pattern)

        dirs = glob.glob(mddev_pattern)
        if not dirs:
            return

        for md_dir in dirs:
            if not os.path.isdir(md_dir):
                if self.verbose:
                    log.warn("Strange - %r is not a directory.", md_dir)
                continue
            dev = os.path.basename(md_dir)
            self.devices.append(dev)

        return

    #--------------------------------------------------------------------------
    def check_mddev(self, dev):
        """
        Underlying method to check the state of a MD device.

        @raise NPReadTimeoutError: on timeout reading a particular file
                                   in sys filesystem
        @raise IOError: if a sysfilesystem file disappears sinc start of
                        this script

        @param dev: the name of the MD device to check (e.g. 'md0', 'md400')
        @type dev: str

        @return: a tuple of two values:
                    * the numeric (Nagios) state
                    * a textual description of the state
        @rtype: tuple of str and int

        """

        log.debug("Checking device %r ...", dev)

        base_dir = os.sep + os.path.join('sys', 'block', dev)
        base_mddir = os.path.join(base_dir, 'md')
        array_state_file = os.path.join(base_mddir, 'array_state')
        degraded_file = os.path.join(base_mddir, 'degraded')
        raid_disks_file = os.path.join(base_mddir, 'raid_disks')
        raid_level_file = os.path.join(base_mddir, 'level')
        degraded_file = os.path.join(base_mddir, 'degraded')
        suspended_file = os.path.join(base_mddir, 'suspended')
        sync_action_file = os.path.join(base_mddir, 'sync_action')
        sync_completed_file = os.path.join(base_mddir, 'sync_completed')

        for sys_dir in (base_dir, base_mddir):
            if not os.path.isdir(sys_dir):
                raise IOError(errno.ENOENT, "Directory doesn't exists.", sys_dir)

        state = RaidState(dev)

        state.array_state = self.read_file(array_state_file).strip()
        state.raid_level = self.read_file(raid_level_file).strip()
        if os.path.exists(degraded_file):
            state.degraded = bool(int(self.read_file(degraded_file)))
        state.nr_raid_disks = int(self.read_file(raid_disks_file))
        if os.path.exists(suspended_file):
            state.suspended = bool(int(self.read_file(suspended_file)))
        if os.path.exists(sync_action_file):
            state.sync_action = self.read_file(sync_action_file).strip()

        i = 0
        while i < state.nr_raid_disks:
            slave_link = os.path.join(base_mddir, 'rd%d' % (i))
            if not os.path.exists(slave_link):
                log.debug("Slave %d of raid %r doesn't exists.", i, dev)
                state.slaves[i] = None
                i += 1
                continue
            link_target = os.readlink(slave_link)
            slave_dir = os.path.normpath(os.path.join(
                    os.path.dirname(slave_link), link_target))

            slave_state_file = os.path.join(slave_dir, 'state')
            slave_block_file = os.path.join(slave_dir, 'block')
            slave_state = self.read_file(slave_state_file).strip()
            block_target = os.readlink(slave_block_file)
            slave_block_device = os.path.normpath(os.path.join(
                    os.path.dirname(slave_block_file), block_target))
            slave_block_device = os.sep + os.path.join('dev', os.path.basename(slave_block_device))

            slave = SlaveState(i, slave_dir)
            slave.block_device = slave_block_device
            slave.state = slave_state
            state.slaves[i] = slave

            i += 1

        if self.verbose > 2:
            log.debug("Status results for %r:\n%s", dev, pp(state.as_dict()))

        return None

    #--------------------------------------------------------------------------
    def __call__(self):
        """
        Method to call the plugin directly.
        """

        self.parse_args()
        if self.check_all:
            self.collect_devices()
            if not self.devices:
                self.exit(nagios.state.ok, "No MD devices to check found.")

        if self.verbose > 2:
            log.debug("Current object:\n%s", pp(self.as_dict()))
        log.debug("MD devices to check: %r", self.devices)

        state = nagios.state.ok
        out = "MD devices seems to be ok."

        for dev in sorted(self.devices,
                cmp = lambda x, y: cmp(int(x.replace('md', '')), int(y.replace('md', '')))):
            result = None
            try:
                result = self.check_mddev(dev)
            except NPReadTimeoutError:
                msg = "%s - timeout on getting information" % (dev)
                self.ugly_ones.append(msg)
            except IOError, e:
                msg = "MD device %r disappeared during this script: %s" % (
                        dev, e)
                log.debug(msg)
                continue
            except Exception, e:
                self.die("Unknown %r error on getting information about %r: %s" %
                        (e.__class__.__name__, dev, e))
            if result is None:
                continue

            self.checked_devices += 1
            (state, output) = result
            if state == nagios.state.ok:
                self.good_ones.append(output)
            elif state == nagios.state.warning:
                self.bad_ones.append(output)
            else:
                self.ugly_ones.append(output)


        self.exit(state, out)

#==============================================================================

if __name__ == "__main__":

    pass

#==============================================================================

# vim: fileencoding=utf-8 filetype=python ts=4 expandtab shiftwidth=4 softtabstop=4
