#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
@author: Frank Brehm
@contact: frank.brehm@profitbricks.com
@copyright: © 2010 - 2015 by Frank Brehm, Berlin
@summary: Module for a class for a nagios/icinga plugin to check the state
          of physical drives on a MegaRaid adapter
"""

# Standard modules
import re
import logging
import textwrap

# Third party modules

# Own modules

import nagios

import nagios.plugin

import nagios.plugin.functions
from nagios.plugin.functions import max_state

import nagios.plugins.check_megaraid
from nagios.plugins.check_megaraid import CheckMegaRaidPlugin

# --------------------------------------------
# Some module variables

__version__ = '0.2.3'

log = logging.getLogger(__name__)


# =============================================================================
class CheckMegaRaidPdPlugin(CheckMegaRaidPlugin):
    """
    A special NagiosPlugin class for checking the state of physical drives
    a LSI MegaRaid adapter.
    """

    # -------------------------------------------------------------------------
    def __init__(self):
        """
        Constructor of the CheckMegaRaidPdPlugin class.
        """

        usage = """\
                %(prog)s [-v] [-a <adapter_nr>]:
                """
        usage = textwrap.dedent(usage).strip()
        usage += '\n       %(prog)s --usage'
        usage += '\n       %(prog)s --help'

        blurb = "Copyright (c) 2015 Frank Brehm, Berlin.\n\n"
        blurb += "Checks the number of the state of physical drives on a LSI MegaRaid adapter."

        super(CheckMegaRaidPdPlugin, self).__init__(
            shortname='MEGARAID_PD',
            usage=usage, blurb=blurb,
            version=__version__,
        )

        self._add_args()

        self.drive_list = []
        self.drive = {}

    # -------------------------------------------------------------------------
    def as_dict(self):
        """
        Typecasting into a dictionary.

        @return: structure as dict
        @rtype:  dict

        """

        d = super(CheckMegaRaidPdPlugin, self).as_dict()

        return d

    # -------------------------------------------------------------------------
    def _add_args(self):
        """
        Adding all necessary arguments to the commandline argument parser.
        """

        super(CheckMegaRaidPdPlugin, self)._add_args()

    # -------------------------------------------------------------------------
    def parse_args(self, args=None):
        """
        Executes self.argparser.parse_args().

        If overridden by successors, it should be called via super().

        @param args: the argument strings to parse. If not given, they are
                     taken from sys.argv.
        @type args: list of str or None

        """

        super(CheckMegaRaidPdPlugin, self).parse_args(args)

    # -------------------------------------------------------------------------
    def call(self):
        """
        Method to call the plugin directly.
        """

        state = nagios.state.ok
        out = "State of physical drives of MegaRaid adapter %d seems to be okay." % (
            self.adapter_nr)

        # Enclosure Device ID: 0
        re_enc = re.compile(r'^\s*Enclosure\s+Device\s+ID\s*:\s*(\d+)', re.IGNORECASE)
        # Slot Number: 23
        re_slot = re.compile(r'^\s*Slot\s+Number\s*:\s*(\d+)', re.IGNORECASE)
        # Device Id: 6
        re_dev_id = re.compile(r'^\s*Device\s+Id\s*:\s*(\d+)', re.IGNORECASE)
        # Media Error Count: 0
        re_media_errors = re.compile(
            r'^\s*Media\s+Error\s+Count\s*:\s*(\d+)', re.IGNORECASE)
        # Other Error Count: 0
        re_other_errors = re.compile(
            r'^\s*Other\s+Error\s+Count\s*:\s*(\d+)', re.IGNORECASE)
        # Predictive Failure Count: 0
        re_pred_failures = re.compile(
            r'^\s*Predictive\s+Failure\s+Count\s*:\s*(\d+)', re.IGNORECASE)
        # Firmware state: Online, Spun Up
        re_fw_state = re.compile(r'^\s*Firmware\s+state\s*:\s*(\S+.*)', re.IGNORECASE)
        # Foreign State: None
        re_foreign_state = re.compile(
            r'^\s*Foreign\s+state\s*:\s*(\S+.*)', re.IGNORECASE)

        good_fw_states = (
            r'Online,\s+Spun\s+Up',
            r'Hotspare,\s+Spun\s+Up',
            r'Hotspare,\s+Spun\s+Down',
            r'Unconfigured\(good\),\s+Spun\s+Up',
            r'Unconfigured\(good\),\s+Spun\s+Down',
        )
        warn_fw_states = (
            r'Rebuild',
            r'Copyback',
        )
        good_fw_pattern = r'^\s*(?:' + r'|'.join(good_fw_states) + r')\s*$'
        warn_fw_pattern = r'^\s*(?:' + r'|'.join(warn_fw_states) + r')\s*$'
        re_good_fw_state = re.compile(good_fw_pattern, re.IGNORECASE)
        re_warn_fw_state = re.compile(warn_fw_pattern, re.IGNORECASE)

        drives_total = 0
        args = ('-PdList',)
        (stdoutdata, stderrdata, ret, exit_code) = self.megacli(args)
        if self.verbose > 3:
            log.debug("Output on StdOut:\n%s", stdoutdata)

        cur_dev = None

        for line in stdoutdata.splitlines():

            line = line.strip()
            m = re_enc.search(line)
            if m:
                if cur_dev:
                    if ('enclosure' in cur_dev) and ('slot' in cur_dev):
                        pd_id = '[%d:%d]' % (
                            cur_dev['enclosure'], cur_dev['slot'])
                        self.drive_list.append(pd_id)
                        self.drive[pd_id] = cur_dev

                cur_dev = {}
                drives_total += 1
                cur_dev = {
                    'enclosure': int(m.group(1)),
                    'media_errors': 0,
                    'other_errors': 0,
                    'predictive_failures': 0,
                    'fw_state': None,
                    'foreign_state': None,
                }
                continue

            m = re_slot.search(line)
            if m:
                if cur_dev:
                    cur_dev['slot'] = int(m.group(1))
                continue

            m = re_dev_id.search(line)
            if m:
                if cur_dev:
                    cur_dev['dev_id'] = int(m.group(1))
                continue

            m = re_media_errors.search(line)
            if m:
                if cur_dev:
                    cur_dev['media_errors'] = int(m.group(1))
                continue

            m = re_other_errors.search(line)
            if m:
                if cur_dev:
                    cur_dev['other_errors'] = int(m.group(1))
                continue

            m = re_pred_failures.search(line)
            if m:
                if cur_dev:
                    cur_dev['predictive_failures'] = int(m.group(1))
                continue

            m = re_fw_state.search(line)
            if m:
                if cur_dev:
                    cur_dev['fw_state'] = m.group(1)
                continue

            m = re_foreign_state.search(line)
            if m:
                if cur_dev:
                    cur_dev['foreign_state'] = m.group(1)
                continue

        if cur_dev:
            if ('enclosure' in cur_dev) and ('slot' in cur_dev):
                pd_id = '[%d:%d]' % (cur_dev['enclosure'], cur_dev['slot'])
                self.drive_list.append(pd_id)
                self.drive[pd_id] = cur_dev

        media_errors = 0
        other_errors = 0
        predictive_failures = 0
        fw_state_wrong = 0
        foreign_state_wrong = 0
        errors = []

        for pd_id in self.drive_list:
            cur_dev = self.drive[pd_id]
            found_errors = False
            drv_desc = []
            disk_state = nagios.state.ok

            if cur_dev['media_errors']:
                disk_state = max_state(disk_state, nagios.state.critical)
                found_errors = True
                drv_desc.append("%d media errors" % (cur_dev['media_errors']))
                media_errors += 1
            if cur_dev['other_errors']:
                found_errors = True
                drv_desc.append("%d other errors" % (cur_dev['other_errors']))
                other_errors += 1
            if cur_dev['predictive_failures']:
                disk_state = max_state(disk_state, nagios.state.critical)
                found_errors = True
                drv_desc.append("%d predictive failures" % (cur_dev['predictive_failures']))
                predictive_failures += 1
            if not re_good_fw_state.search(cur_dev['fw_state']):
                if re_warn_fw_state.search(cur_dev['fw_state']):
                    disk_state = max_state(disk_state, nagios.state.warning)
                else:
                    disk_state = max_state(disk_state, nagios.state.critical)
                found_errors = True
                drv_desc.append("wrong firmware state %r" % (cur_dev['fw_state']))
                fw_state_wrong += 1
            if cur_dev['foreign_state'].lower() != "none":
                disk_state = max_state(disk_state, nagios.state.critical)
                found_errors = True
                drv_desc.append("wrong foreign state %r" % (cur_dev['foreign_state']))
                foreign_state_wrong += 1
            if found_errors:
                state = max_state(state, disk_state)
                dd = "drive %s has " % (pd_id)
                dd += ' and '.join(drv_desc)
                errors.append(dd)
            if found_errors or self.verbose > 1:
                log.debug(
                    "State of drive %s is %s.", pd_id,
                    nagios.plugin.functions.STATUS_TEXT[disk_state])

        log.debug("Found %d drives.", drives_total)
        if self.verbose > 2:
            log.debug("Found Pds:\n%s", self.drive_list)
            log.debug("Found Pd data:\n%s", self.drive)

        if errors:
            out = ', '.join(errors)

        self.add_perfdata(label='drives_total', value=drives_total, uom='')
        self.add_perfdata(label='media_errors', value=media_errors, uom='')
        self.add_perfdata(label='other_errors', value=other_errors, uom='')
        self.add_perfdata(label='predictive_failures', value=predictive_failures, uom='')
        self.add_perfdata(label='wrong_fw_state', value=fw_state_wrong, uom='')
        self.add_perfdata(label='wrong_foreign_state', value=foreign_state_wrong, uom='')

        self.exit(state, out)

# =============================================================================

if __name__ == "__main__":

    pass

# =============================================================================

# vim: fileencoding=utf-8 filetype=python ts=4 et
