#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
@author: Frank Brehm
@contact: frank.brehm@profitbricks.com
@copyright: © 2010 - 2013 by Frank Brehm, Berlin
@summary: Module for CheckSmartStatePlugin class
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

from nagios.plugin.range import NagiosRange

from nagios.plugin.threshold import NagiosThreshold

from nagios.plugin.argparser import default_timeout

from nagios.plugin.extended import ExtNagiosPluginError
from nagios.plugin.extended import ExecutionTimeoutError
from nagios.plugin.extended import CommandNotFoundError
from nagios.plugin.extended import ExtNagiosPlugin

#---------------------------------------------
# Some module variables

__version__ = '0.3.1'

log = logging.getLogger(__name__)

DEFAULT_MEGARAID_PATH = '/opt/MegaRAID/MegaCli'
DEFAULT_WARN_SECTORS = 4
DEFAULT_CRIT_SECTORS = 10

#==============================================================================
class MegaCliExecTimeoutError(ExtNagiosPluginError, IOError):
    """
    Special error class indicating a timout error on
    executing MegaCli.
    """

    #--------------------------------------------------------------------------
    def __init__(self, timeout, cmdline):
        """
        Constructor.

        @param timeout: the timout in seconds leading to the error
        @type timeout: float
        @param cmdline: the commandline leading to the error
        @type cmdline: str

        """

        t_o = None
        try:
            t_o = float(timeout)
        except ValueError:
            pass
        self.timeout = t_o

        self.cmdline = cmdline

    #--------------------------------------------------------------------------
    def __str__(self):

        msg = "Error executing: %s (timeout after %0.1f secs)" % (
                self.cmdline, self.timeout)

        return msg

#==============================================================================
class CheckSmartStatePlugin(ExtNagiosPlugin):
    """
    A special NagiosPlugin class for checking the SMART state of a physical
    hard drive.
    """

    #--------------------------------------------------------------------------
    def __init__(self):
        """
        Constructor of the CheckSmartStatePlugin class.
        """

        usage = """\
        %(prog)s [-v] [-m] -c <critical grown sectors> -w <warn grown sectors> <HD device>
        """
        usage = textwrap.dedent(usage).strip()
        usage += '\n       %(prog)s --usage'
        usage += '\n       %(prog)s --help'

        blurb = "Copyright (c) 2013 Frank Brehm, Berlin.\n\n"
        blurb += "Checks the SMART state of a physical hard drive."

        super(CheckSmartStatePlugin, self).__init__(
                usage = usage, blurb = blurb,
                append_searchpath = [DEFAULT_MEGARAID_PATH],
        )

        self._smartctl_cmd = self.get_command('smartctl')
        """
        @ivar: the underlaying 'smartctl' command
        @type: str
        """
        if not self.smartctl_cmd:
            msg = "Command %r not found." % ('smartctl')
            self.die(msg)

        self._megacli_cmd = None
        """
        @ivar: the 'MegaCLI' command for detecting Device Id from an enclosure:slot data
        @type: str
        """

        self._megaraid = False
        """
        @ivar: Is the given device a PhysicalDrive on a MegaRaid adapter
        @type: bool
        """

        self._warn_sectors = NagiosRange(start = 0, end = DEFAULT_WARN_SECTORS)
        """
        @ivar: number of grown defect sectors leading to a warning
        @type: NagiosRange
        """

        self._crit_sectors = NagiosRange(start = 0, end = DEFAULT_CRIT_SECTORS)
        """
        @ivar: number of grown defect sectors leading to a critical message
        @type: NagiosRange
        """

        self._device = None
        """
        @ivar: the device to check
        @type: str
        """

        self._device_id = None
        """
        @ivar: the MegaRaid Device Id of the PD on the MegaRAID controller.
        @type: int
        """

        self._megaraid_slot = None
        """
        @ivar: the MegaRaid enclusure-Id/slot-Id pair to check
        @type: tuple of two int
        """

        self._adapter_nr = 0
        """
        @ivar: the number of the MegaRaid adapter (e.g. 0)
        @type: str
        """

        self._init_megacli_cmd()

        self._add_args()

    #------------------------------------------------------------
    @property
    def smartctl_cmd(self):
        """The absolute path to the OS command 'smartctl'."""
        return self._smartctl_cmd

    #------------------------------------------------------------
    @property
    def megacli_cmd(self):
        """The absolute path to the OS command 'MegaCli'."""
        return self._megacli_cmd

    #------------------------------------------------------------
    @property
    def megaraid(self):
        """Is the given device a PhysicalDrive on a MegaRaid adapter."""
        return self._megaraid

    @megaraid.setter
    def megaraid(self, value):
        self._megaraid = bool(value)

    #------------------------------------------------------------
    @property
    def warn_sectors(self):
        """The number of grown defect sectors leading to a warning."""
        return self._warn_sectors

    #------------------------------------------------------------
    @property
    def crit_sectors(self):
        """The number of grown defect sectors leading to a critical message."""
        return self._crit_sectors

    #------------------------------------------------------------
    @property
    def device(self):
        """The device to check."""
        return self._device

    #------------------------------------------------------------
    @property
    def device_id(self):
        """The MegaRaid Device Id of the PD on the MegaRAID controller."""
        return self._device_id

    #------------------------------------------------------------
    @property
    def megaraid_slot(self):
        """The MegaRaid enclusure-Id/slot-Id pair to check."""
        return self._megaraid_slot

    #------------------------------------------------------------
    @property
    def adapter_nr(self):
        """The number of the MegaRaid adapter (e.g. 0)."""
        return self._adapter_nr

    #--------------------------------------------------------------------------
    def as_dict(self):
        """
        Typecasting into a dictionary.

        @return: structure as dict
        @rtype:  dict

        """

        d = super(CheckSmartStatePlugin, self).as_dict()

        d['adapter_nr'] = self.adapter_nr
        d['smartctl_cmd'] = self.smartctl_cmd
        d['megacli_cmd'] = self.megacli_cmd
        d['megaraid'] = self.megaraid
        d['warn_sectors'] = self.warn_sectors
        d['crit_sectors'] = self.crit_sectors
        d['device'] = self.device
        d['device_id'] = self.device_id
        d['megaraid_slot'] = self.megaraid_slot

        return d

    #--------------------------------------------------------------------------
    def _init_megacli_cmd(self):
        """
        Initializes self.megacli_cmd.
        """

        self._megacli_cmd = self._get_megacli_cmd()

    #--------------------------------------------------------------------------
    def _get_megacli_cmd(self, given_path = None):
        """
        Finding the executable 'MegaCli64', 'MegaCli' or 'megacli' under the
        search path or the given path.

        @param given_path: a possibly given path to MegaCli
        @type given_path: str

        @return: the found path to the megacli executable.
        @rtype: str or None

        """

        exe_names = ('MegaCli', 'megacli')
        arch = os.uname()[4]
        if arch == 'x86_64':
            exe_names = ('MegaCli64', 'MegaCli', 'megacli')

        if given_path:
            # Normalize the given path, if it exists.
            if os.path.isabs(given_path):
                if not is_exe(given_path):
                    return None
                return os.path.realpath(given_path)
            exe_names = (given_path,)

        for exe_name in exe_names:
            log.debug("Searching for %r ...", exe_name)
            exe_file = self.get_command(exe_name, quiet = True)
            if exe_file:
                return exe_file

        return None

    #--------------------------------------------------------------------------
    def _add_args(self):
        """
        Adding all necessary arguments to the commandline argument parser.
        """

        arg_help = ('The number of grown defect sectors leading to a ' +
                    'warning (Default: %d).') % (DEFAULT_WARN_SECTORS)
        self.add_arg(
                '-w', '--warning',
                metavar = 'SECTORS',
                dest = 'warning',
                required = True,
                type = int,
                default = DEFAULT_WARN_SECTORS,
                help = arg_help,
        )

        arg_help = ('The number of grown defect sectors leading to a ' +
                    'critical message (Default: %d).') % (DEFAULT_CRIT_SECTORS)
        self.add_arg(
                '-c', '--critical',
                metavar = 'SECTORS',
                dest = 'critical',
                required = True,
                type = int,
                default = DEFAULT_CRIT_SECTORS,
                help = arg_help,
        )

        self.add_arg(
                '-m', '--megaraid',
                metavar = 'DEVICE_ID',
                dest = 'megaraid',
                help = ('If given, check the device DEVICE_ID on a MegaRAID ' +
                        'controller. The DEVICE_ID might be given as a single ' +
                        'Device Id (integer) or as an <enclosure-id:slot-id> ' +
                        'pair of the MegaRaid adapter.'),
        )

        self.add_arg(
                'device',
                dest = 'device',
                nargs = '?',
                help = ("The device to check (given as 'sdX' or '/dev/sdX', " +
                        "must exists)."),
        )

    #--------------------------------------------------------------------------
    def parse_args(self, args = None):
        """
        Executes self.argparser.parse_args().

        @param args: the argument strings to parse. If not given, they are
                     taken from sys.argv.
        @type args: list of str or None

        """

        super(CheckSmartStatePlugin, self).parse_args(args)

        self.init_root_logger()

        self._warn_sectors = NagiosRange(start = 0, end = self.argparser.args.warning)
        self._crit_sectors = NagiosRange(start = 0, end = self.argparser.args.critical)

        self.set_thresholds(
                warning = self.warn_sectors,
                critical = self.crit_sectors,
        )

        if not self.argparser.args.device:
            self.die("No device to check given.")

        dev = os.path.basename(self.argparser.args.device)
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

        self._device = dev_dev

        if self.argparser.args.megaraid:
            self._init_megacli_dev(self.argparser.args.megaraid)


    #--------------------------------------------------------------------------
    def _init_megacli_dev(self, dev):
        """
        Initializes self.device_id and self.megaraid_slot in case of checking
        smartctl on a device on a MagaRaid adpter.
        """

        self._device_id = None
        self._megaraid_slot = None

        re_device_id = re.compile(r'^\s*(\d+)\s*$')
        re_slot = re.compile(r'^\s*(?:\[(\d+:\d+)\]|(\d+:\d+))\s*$')
        re_enc_slot = re.compile(r'^(\d+):(\d+)$')

        self._megaraid = True

        # A single Device Id was given
        match = re_device_id.search(dev)
        if match:
            self._device_id = int(match.group(1))
            return

        # A pair of Enclosure-Id : Sot-Id was given
        match = re_slot.search(dev)
        if not match:
            self.die("Invalid MegaRaid descriptor %r given." % (dev))

        pair = match.group(1)
        if pair is None:
            pair = match.group(2)

        match = re_enc_slot.search(pair)
        if not match:
            self.die("Ooops, pair %r didn't match pattern %r???" % (
                    pair, re_enc_slot.pattern))

        self._megaraid_slot = (int(match.group(1)), int(match.group(2)))

        return self._init_megaraid_device_id()

    #--------------------------------------------------------------------------
    def _init_megaraid_device_id(self):
        """
        Evaluates the Magaraid Device Id from the given Enclosure Id and
        Slot Id.
        """

        stdoutdata = self.get_megaraid_pd_state()

        # Device Id: 38
        re_dev_id = re.compile(r'^\s*Device\s+Id\s*:\s*(\d+)', re.IGNORECASE)
        dev_id = None

        for line in stdoutdata.splitlines():
            match = re_dev_id.search(line)
            if match:
                dev_id = int(match.group(1))
                break

        if dev_id is None:
            self.die("No device Id found for PhysDrv [%d:%d] on the megaraid adapter." % 
                self._megaraid_slot)

        self._device_id = dev_id
        log.debug("Got a Device Id of %d." % (dev_id))
        return

    #--------------------------------------------------------------------------
    def get_megaraid_pd_state(self):
        """
        Retrieves the state of the appropriate MegaRaid Physical Device, if
        the given device is a MegarRaid disk.

        It dies, if the state could not retrieved.

        @return: the output of 'megacli -pdinfo -physdrv[E:S] -a0'
        @rtype: str

        """

        if not self._megaraid_slot:
            self.die("Ooops, need Enclosure Id and Slot Id to retrieve " +
                    "the state of the Magaraid Physical Device.")

        if not self.megacli_cmd:
            self.die("Didn't found to MegaCli command to retrieve the " +
                    "state of the Magaraid Physical Device.")

        pd = '-PhysDrv[%d:%d]' % self._megaraid_slot

        cmd_list = [
                self.megacli_cmd,
                '-pdInfo',
                ('-PhysDrv[%d:%d]' % self._megaraid_slot),
                '-a', '0',
                '-NoLog',
        ]

        (ret, stdoutdata, stderrdata) = self.exec_cmd(cmd_list)

        re_no_adapter = re.compile(r'^\s*User\s+specified\s+controller\s+is\s+not\s+present',
                re.IGNORECASE)
        re_exit_code = re.compile(r'^\s*Exit\s*Code\s*:\s+0x([0-9a-f]+)', re.IGNORECASE)
        # Adapter 0: Device at Enclosure - 1, Slot - 22 is not found.
        re_not_found = re.compile(r'Device\s+at.*not\s+found\.', re.IGNORECASE)

        exit_code = ret
        no_adapter_found = False
        if stdoutdata:
            for line in stdoutdata.splitlines():

                if re_no_adapter.search(line):
                    self.die('The specified controller %d is not present.' % (
                            self.adapter_nr))

                if re_not_found.search(line):
                        self.die(line.strip())

                match = re_exit_code.search(line)
                if match:
                    exit_code = int(match.group(1), 16)
                    continue

        log.debug("Exitcode of '%s -pdInfo -PhysDrv[%d:%d] -a 0': %d.",
                self.megacli_cmd, self._megaraid_slot[0],
                self._megaraid_slot[1], exit_code)

        if not stdoutdata:
            self.die('No ouput from: %s' % (cmd_str))

        return stdoutdata

    #--------------------------------------------------------------------------
    def get_megaraid_pd_spin_state(self):
        """
        Retrieves the spin state of a Magaraid Physical Drive.

        @return: the spin state as one of 'up', 'down' or None
        @rtype: str or None

        """

        stdoutdata = self.get_megaraid_pd_state()

        # The line of interest:
        #Firmware state: Unconfigured(good), Spun down

        re_fw_state = re.compile(r'^\s*Firmware\s+state:\s*(\S.*)',
                re.IGNORECASE)
        re_spin_state = re.compile(r'Spun\s+(Down|Up)', re.IGNORECASE)
        fw_state = None

        for line in stdoutdata.splitlines():
            match = re_fw_state.search(line)
            if match:
                fw_state = match.group(1).strip()
                break

        if fw_state is None:
            log.debug(("Could not retrieve firmware state of Magaraid " +
                    "Physical Device [%d:%d]."), self._megaraid_slot[0],
                    self._megaraid_slot[1])
            return None

        log.debug("Got a firmware state of Magaraid Physical Device [%d:%d]: %s",
                self._megaraid_slot[0], self._megaraid_slot[1], fw_state)

        match = re_spin_state.search(fw_state)
        if not match:
            log.debug(("Could not retrieve spin state of Magaraid " +
                    "Physical Device [%d:%d] from %r."), self._megaraid_slot[0],
                    self._megaraid_slot[1], fw_state)
            return None

        return match.group(1).lower()

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

        re_is_sas = re.compile(r'^\s*Transport\s+protocol\s*:\s*SAS\s*$',
                (re.IGNORECASE | re.MULTILINE))

        no_smart_patterns = (
            r'Device\s+does\s+not\s+support\s+SMART',
            # SMART support is:     Unavailable - device lacks SMART capability.
            r'SMART\s+support\s+is:\s+Unavailable\s+-\s+.*',
        )
        pattern = r'(' + r'|'.join(no_smart_patterns) + r')'
        re_no_smart = re.compile(pattern, (re.IGNORECASE | re.MULTILINE))
        if self.verbose > 2:
            log.debug("No SMART pattern: %r", re_no_smart.pattern)

        smart_output = self._exec_smartctl()

        is_sas = False
        if re_is_sas.search(smart_output):
            is_sas = True

        match = re_no_smart.search(smart_output)
        if match:

            msg = ''
            if is_sas:
                msg = "SAS "
            else:
                msg = "SATA "
            dev = self.device
            if self.megaraid:
                dev = "[%d:%d]" % self.megaraid_slot

            reason = match.group(1).strip()
            reason = re.sub(r'\s+', ' ', reason)
            log.debug("No SMART of HDD %s: %s", dev, reason)

            if self.megaraid:

                # Exit with OK, if the disk is spun down
                spin_state = self.get_megaraid_pd_spin_state()
                if spin_state and spin_state == 'down':

                    msg += "HDD %s: Spun Down" % (dev)
                    self.exit(nagios.state.ok, msg)

            msg += "HDD %s: %s" % (dev, reason)
            self.die(msg)

        self.disk_data = {
                'model': None,
                'serial': None,
                'health_state': None,
                'nr_grown_defects': 0,
                'temperature': None,
                'hours_on': None,
        }

        if is_sas:
            log.debug("Disk is a SAS disk.")
            self._eval_sas_disk(smart_output)
        else:
            log.debug("Disk is a SATA disk.")
            self._eval_sata_disk(smart_output)

        log.debug("Evaluated disk data:\n%s", pp(self.disk_data))

        err_msgs = []

        if self.disk_data['health_state'] is None:
            msg = "Could not detect SMART Health Status of "
            if is_sas:
                msg += "SAS "
            else:
                msg += "SATA "
            dev = self.device
            if self.megaraid:
                dev = "[%d:%d]" % self.megaraid_slot
            msg += "HDD %s." % (dev)
            self.die(msg)

        if is_sas:
            if self.disk_data['health_state'].lower() != 'ok':
                state = self.max_state(state, nagios.state.critical)
                err_msgs.append("SMART Health Status is %r." % (
                        self.disk_data['health_state']))
        else:
            if self.disk_data['health_state'].lower() != 'passed':
                state = self.max_state(state, nagios.state.critical)
                err_msgs.append("SMART overall-health self-assessment test result is %r." % (
                        self.disk_data['health_state']))

        gd_count = self.disk_data['nr_grown_defects']
        if self.threshold:
            gd_state = self.threshold.get_status(gd_count)
            if gd_state != nagios.state.ok:
                state = self.max_state(state, gd_state)
                err_msgs.append("%d elements in list of grown defects." % (
                        gd_count))
            self.add_perfdata(
                    label = 'gd_list',
                    value = gd_count,
                    threshold = self.threshold,
            )
        else:
            self.add_perfdata(
                    label = 'gd_list',
                    value = gd_count,
            )

        if self.disk_data['temperature'] is not None:
            self.add_perfdata(
                    label = 'temperature',
                    value = self.disk_data['temperature'],
                    uom = "C",
            )

        out = ""
        if is_sas:
            out = "SAS "
        else:
            out = "SATA "
        dev = self.device
        if self.megaraid:
            dev = "[%d:%d]" % self.megaraid_slot
        out += "HDD %s " % (dev)

        if err_msgs:
            out += ", ".join(err_msgs)
        else:
            out += "SMART Health Status seems to be okay."

        if (self.disk_data['hours_on'] is not None and
                isinstance(self.disk_data['hours_on'], Number)):
            days = self.disk_data['hours_on'] / 24
            hours = self.disk_data['hours_on'] % 24
            out += " Power on: %d days, %d hours." % (days, hours)

        self.exit(state, out)

    #--------------------------------------------------------------------------
    def _eval_sata_disk(self, smart_output):

        re_health_state = re.compile(r'^SMART\s+overall-health\s+self-assessment\s+test\s+result\s*:\s*(\S.*)',
                re.IGNORECASE)
        re_model = re.compile(r'^Device\s+Model\s*:\s*(\S.*)', re.IGNORECASE)
        #   5 Reallocated_Sector_Ct   -O--CK   100   100   000    -    0
        re_realloc = re.compile(r'^\d+\s+Reallocated_Sector_Ct\s+\S+\s+\S+\s+\S+\s+\S+\s+\S+\s+(\d+)',
                re.IGNORECASE)
        # 187 Reported_Uncorrect      -O--CK   100   100   000    -    0
        re_rep_uncorr = re.compile(r'^\d+\s+Reported_Uncorrect\s+(\S+)\s+\S+\s+\S+\s+\S+\s+\S+\s+(\d+)',
                re.IGNORECASE)
        # 197 Current_Pending_Sector  -O--CK   100   100   000    -    0
        re_cur_pend_sect = re.compile(r'^\d+\s+Current_Pending_Sector\s+\S+\s+\S+\s+\S+\s+\S+\s+\S+\s+(\d+)',
                re.IGNORECASE)
        # yxz Offline_Uncorrectable   -O--CK   100   100   000    -    0
        re_offl_uncor = re.compile(r'^\d+\s+Offline_Uncorrectable\s+\S+\s+\S+\s+\S+\s+\S+\s+\S+\s+(\d+)',
                re.IGNORECASE)
        # xyz Reallocated_Event_Count -O--CK   100   100   000    -    0
        re_realloc_evt = re.compile(r'^\d+\s+Reallocated_Event_Count\s+\S+\s+\S+\s+\S+\s+\S+\s+\S+\s+(\d+)',
                re.IGNORECASE)
        # zyx Erase_Fail_Count        -O--CK   100   100   000    -    0
        re_erase_fail_count = re.compile(r'^\d+\s+Erase_Fail_Count\s+\S+\s+\S+\s+\S+\s+\S+\s+\S+\s+(\d+)',
                re.IGNORECASE)
        # 194 Temperature_Celsius     -O---K   100   100   000    -    25
        re_temp = re.compile(r'^\d+\s+Temperature_Celsius\s+\S+\s+\S+\s+\S+\s+\S+\s+\S+\s+(\d+)',
                re.IGNORECASE)
        #   9 Power_On_Hours          -O--CK   100   100   000    -    2139
        re_hours = re.compile(r'^\d+\s+Power_On_Hours\s+\S+\s+\S+\s+\S+\s+\S+\s+\S+\s+(\d+(?:\.\d*)?)',
                re.IGNORECASE)

        use_uncorrect = True

        for line in smart_output.splitlines():
            line = line.strip()
            if line == '':
                continue

            match = re_health_state.search(line)
            if match:
                self.disk_data['health_state'] = match.group(1)
                continue

            match = re_model.search(line)
            if match:
                self.disk_data['model'] = match.group(1)
                continue

            match = re_realloc.search(line)
            if match:
                self.disk_data['realloc_sectors'] = int(match.group(1))
                continue

            match = re_rep_uncorr.search(line)
            if match:
                uncorrect_tags = match.group(1).lower()
                if uncorrect_tags[0] == 'p':
                    use_uncorrect = False
                self.disk_data['reported_uncorrect'] = int(match.group(2))
                continue

            match = re_cur_pend_sect.search(line)
            if match:
                self.disk_data['current_pending_sector'] = int(match.group(1))
                continue

            match = re_offl_uncor.search(line)
            if match:
                self.disk_data['offline_uncorretable'] = int(match.group(1))
                continue

            match = re_realloc_evt.search(line)
            if match:
                self.disk_data['realloc_event_count'] = int(match.group(1))
                continue

            match = re_erase_fail_count.search(line)
            if match:
                self.disk_data['erase_fail_count'] = int(match.group(1))
                continue

            match = re_temp.search(line)
            if match:
                self.disk_data['temperature'] = int(match.group(1))
                continue

            match = re_hours.search(line)
            if match:
                hours = int(float(match.group(1)) + 0.5)
                self.disk_data['hours_on'] = hours

        self.disk_data['nr_grown_defects'] = 0
        if 'realloc_sectors' in self.disk_data:
            self.disk_data['nr_grown_defects'] += self.disk_data['realloc_sectors']
        if 'reported_uncorrect' in self.disk_data and use_uncorrect:
            self.disk_data['nr_grown_defects'] += self.disk_data['reported_uncorrect']
        if 'current_pending_sector' in self.disk_data:
            self.disk_data['nr_grown_defects'] += self.disk_data['current_pending_sector']
        if 'offline_uncorretable' in self.disk_data:
            self.disk_data['nr_grown_defects'] += self.disk_data['offline_uncorretable']
        if 'realloc_event_count' in self.disk_data:
            self.disk_data['nr_grown_defects'] += self.disk_data['realloc_event_count']
        if 'erase_fail_count' in self.disk_data:
            self.disk_data['nr_grown_defects'] += self.disk_data['erase_fail_count']
        

    #--------------------------------------------------------------------------
    def _eval_sas_disk(self, smart_output):

        re_health_state = re.compile(r'^SMART\s+Health\s+Status\s*:\s*(\S.*)',
                re.IGNORECASE)
        re_el_gd_list = re.compile(r'^Elements\s+in\s+grown\s+defect\s+list\s*:\s*(\d+)',
                re.IGNORECASE)
        re_vendor = re.compile(r'^Vendor\s*:\s*(\S.*)', re.IGNORECASE)
        re_product = re.compile(r'^Product\s*:\s*(\S.*)', re.IGNORECASE)
        re_serial = re.compile(r'^Serial\s+number\s*:\s*(\S.*)', re.IGNORECASE)
        re_non_medium_errs = re.compile(r'^Non-medium\s+error\s+count\s*:\s*(\d+)',
                re.IGNORECASE)
        # Current Drive Temperature:     34 C
        re_temp = re.compile(r'^Current\s+Drive\s+Temperature\s*:\s*(\d+)(?:\s*([CF]))?',
                re.IGNORECASE)
        re_hours = re.compile(r'^number\s+of\s+hours\s+powered\s+up\s*=\s*(\d+(?:\.\d*)?)',
                re.IGNORECASE)

        for line in smart_output.splitlines():
            line = line.strip()
            if line == '':
                continue

            match = re_health_state.search(line)
            if match:
                self.disk_data['health_state'] = match.group(1)
                continue

            match = re_el_gd_list.search(line)
            if match:
                self.disk_data['nr_grown_defects'] = int(match.group(1))
                continue

            match = re_vendor.search(line)
            if match:
                self.disk_data['vendor'] = match.group(1)
                continue

            match = re_product.search(line)
            if match:
                self.disk_data['product'] = match.group(1)
                continue

            match = re_serial.search(line)
            if match:
                self.disk_data['serial'] = match.group(1)
                continue

            match = re_non_medium_errs.search(line)
            if match:
                self.disk_data['non_medium_errors'] = int(match.group(1))
                continue

            match = re_temp.search(line)
            if match:
                unit = 'C'
                if match.group(2) and match.group(2).upper() == 'F':
                    unit = 'F'
                temp = float(match.group(1))
                if unit == 'F':
                    temp = ((temp - 32.0) * 5.0 / 9.0) + 0.5
                self.disk_data['temperature'] = int(temp)

            match = re_hours.search(line)
            if match:
                hours = int(float(match.group(1)) + 0.5)
                self.disk_data['hours_on'] = hours

        if 'vendor' in self.disk_data:
            if 'product' in self.disk_data:
                self.disk_data['model'] = (self.disk_data['vendor'] + ' ' +
                        self.disk_data['product'])
            else:
                self.disk_data['model'] = self.disk_data['vendor']
        elif 'product' in self.disk_data:
            self.disk_data['model'] = self.disk_data['product']

    #--------------------------------------------------------------------------
    def _exec_smartctl(self):
        """
        Execute smartctl with all necessary parameters.

        @return: the output on STDOUT
        @rtype: str

        """

        re_no_mega_sas = re.compile(r'failed:\s+SATA\s+device\s+detected,',
             re.IGNORECASE)   

        cmd_list = [self.smartctl_cmd, '-x']
        dev_desc = self.device
        if self.megaraid:
            cmd_list.append('-d')
            cmd_list.append('megaraid,%d' % (self.device_id))
            dev_desc = "%s => megaraid %d" % (self.device, self.device_id)
        cmd_list.append(self.device)

        (ret, stdoutdata, stderrdata) = self.exec_cmd(cmd_list)

        if stdoutdata is None:
            stdoutdata = ''
        stdoutdata = stdoutdata.strip()
        if not stdoutdata:
            self.die("Got no output from smartctl %s." % (dev_desc))

        if self.megaraid:
            if re_no_mega_sas.search(stdoutdata):
                cmd_list = [self.smartctl_cmd, '-x']
                cmd_list.append('-d')
                cmd_list.append('sat+megaraid,%d' % (self.device_id))
                cmd_list.append(self.device)
                (ret, stdoutdata, stderrdata) = self.exec_cmd(cmd_list)
                if stdoutdata is None:
                    stdoutdata = ''
                stdoutdata = stdoutdata.strip()
                if not stdoutdata:
                    self.die("Got no output from smartctl %s is SATA attempt.")

        if self.verbose > 2:
            log.debug("Got output from smartctl %s:\n%s" % (
                    dev_desc, stdoutdata))

        return stdoutdata

#==============================================================================

if __name__ == "__main__":

    pass

#==============================================================================

# vim: fileencoding=utf-8 filetype=python ts=4 expandtab shiftwidth=4 softtabstop=4
