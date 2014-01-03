#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
@author: Frank Brehm
@contact: frank.brehm@profitbricks.com
@copyright: © 2010 - 2014 by Frank Brehm, Berlin
@summary: Module for a class for a nagios/icinga plugin to check the state
          of the Battery Backup Unit (BBU) of a LSI MegaRaid adapter
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

from nagios.plugin.functions import max_state

from nagios.plugin.range import NagiosRange

from nagios.plugin.threshold import NagiosThreshold

from nagios.plugin.extended import ExtNagiosPluginError
from nagios.plugin.extended import ExecutionTimeoutError
from nagios.plugin.extended import CommandNotFoundError
from nagios.plugin.extended import ExtNagiosPlugin

import nagios.plugins.check_megaraid
from nagios.plugins.check_megaraid import CheckMegaRaidPlugin

#---------------------------------------------
# Some module variables

__version__ = '0.2.1'

log = logging.getLogger(__name__)

# Example output
'''
BBU status for Adapter: 0

BatteryType: CVPM02
Voltage: 9418 mV
Current: 0 mA
Temperature: 24 C
Battery State: Optimal
BBU Firmware Status:

  Charging Status              : None
  Voltage                                 : OK
  Temperature                             : OK
  Learn Cycle Requested                   : No
  Learn Cycle Active                      : No
  Learn Cycle Status                      : OK
  Learn Cycle Timeout                     : No
  I2c Errors Detected                     : No
  Battery Pack Missing                    : No
  Battery Replacement required            : No
  Remaining Capacity Low                  : No
  Periodic Learn Required                 : No
  Transparent Learn                       : No
  No space to cache offload               : No
  Pack is about to fail & should be replaced : No
  Cache Offload premium feature required  : No
  Module microcode update required        : No

BBU GasGauge Status: 0x6448
  Pack energy             : 328 J
  Capacitance             : 100
  Remaining reserve space : 92


Exit Code: 0x00

'''

#==============================================================================
class CheckMegaRaidBBUPlugin(CheckMegaRaidPlugin):
    """
    A special NagiosPlugin class for checking the state of the BBU of a
    LSI MegaRaid adapter.
    """

    #--------------------------------------------------------------------------
    def __init__(self):
        """
        Constructor of the CheckMegaRaidBBUPlugin class.
        """

        usage = """\
                %(prog)s [-v] [-t <timeout>] [-a <adapter_nr>]
                """
        usage = textwrap.dedent(usage).strip()
        usage += '\n       %(prog)s --usage'
        usage += '\n       %(prog)s --help'

        blurb = "Copyright (c) 2014 Frank Brehm, Berlin.\n\n"
        blurb += "Checks the state of the BBU of a LSI MegaRaid adapter."

        super(CheckMegaRaidBBUPlugin, self).__init__(
                shortname = 'MEGARAID_BBU',
                usage = usage, blurb = blurb,
                version = __version__,
        )

        self._add_args()

    #--------------------------------------------------------------------------
    def as_dict(self):
        """
        Typecasting into a dictionary.

        @return: structure as dict
        @rtype:  dict

        """

        d = super(CheckMegaRaidBBUPlugin, self).as_dict()

        #d['adapter_nr'] = self.adapter_nr

        return d

    #--------------------------------------------------------------------------
    def call(self):
        """
        Method to call the plugin directly.
        """

        state = nagios.state.ok
        out = "BBU of MegaRaid adapter %d seems to be okay." % (self.adapter_nr)

        re_batt_type = re.compile(r'^\s*BatteryType\s*:\s*(\S+.*)', re.IGNORECASE)
        re_batt_state = re.compile(r'^\s*Battery\s*State\s*:\s*(\S+.*)', re.IGNORECASE)
        re_voltage = re.compile(r'^\s*Voltage\s*:\s+(\S+)', re.IGNORECASE)
        re_temp = re.compile(r'^\s*Temperature\s*:\s+(\S+)', re.IGNORECASE)
        re_lc_req = re.compile(r'^\s*Learn\s+Cycle\s+Requested\s*:\s+(\S+)', re.IGNORECASE)
        re_lc_act = re.compile(r'^\s*Learn\s+Cycle\s+Active\s*:\s+(\S+)', re.IGNORECASE)
        re_lc_state = re.compile(r'^\s*Learn\s+Cycle\s+Status\s*:\s+(\S+)', re.IGNORECASE)
        re_lc_tout = re.compile(r'^\s*Learn\s+Cycle\s+Timeout\s*:\s+(\S+)', re.IGNORECASE)
        re_i2c_err = re.compile(r'^\s*I2c\s+Errors\s+Detected\s*:\s+(\S+)', re.IGNORECASE)
        re_bbu_miss = re.compile(r'^\s*Battery\s+Pack\s+Missing\s*:\s+(\S+)', re.IGNORECASE)
        re_bbu_replace = re.compile(r'^\s*Battery\s+Replacement\s+required\s*:\s+(\S+)', re.IGNORECASE)
        re_capac_low = re.compile(r'^\s*Remaining\s+Capacity\s+Low\s*:\s+(\S+)', re.IGNORECASE)
        re_per_learn = re.compile(r'^\s*Periodic\s+Learn\s+Required\s*:\s+(\S+)', re.IGNORECASE)
        re_trans_learn = re.compile(r'^\s*Transparent\s+Learn\s*:\s+(\S+)', re.IGNORECASE)
        re_no_space = re.compile(r'^\s*No\s+space\s+to\s+cache\s+offload\s*:\s+(\S+)', re.IGNORECASE)
        re_pack_fail = re.compile(r'^\s*Pack\s+is\s+about\s+to\s+fail\s+.*:\s+(\S+)', re.IGNORECASE)
        re_micro_upd = re.compile(r'^\s*Module\s+microcode\s+update\s+required\s*:\s+(\S+)', re.IGNORECASE)

        args = ('-AdpBbuCmd', '-GetBbuStatus')
        (stdoutdata, stderrdata, ret, exit_code) = self.megacli(args)
        if self.verbose > 2:
            log.debug("Output on StdOut:\n%s", stdoutdata)

        batt_type = 'unknown'
        batt_state = None       # optimal
        voltage = None          # ok
        temperature = None      # ok
        lc_req = None           # no
        lc_act = None           # no
        lc_state = None         # ok
        lc_timeout = None       # no
        i2c_err = None          # no
        bbu_miss = None         # no
        bbu_replace = None      # no
        capac_low = None        # no
        per_learn = None        # no
        trans_learn = None      # no
        no_space = None         # no
        pack_fail = None        # no
        micro_upd = None        # no

        for line in stdoutdata.splitlines():

            line = line.strip()
            
            match = re_batt_type.search(line)
            if match:
                batt_type = match.group(1)
                continue

            match = re_batt_state.search(line)
            if match:
                batt_state = match.group(1)
                continue

            match = re_voltage.search(line)
            if match:
                voltage = match.group(1).lower()
                continue

            match = re_temp.search(line)
            if match:
                temperature = match.group(1).lower()
                continue

            match = re_lc_req.search(line)
            if match:
                lc_req = match.group(1).lower()
                continue

            match = re_lc_act.search(line)
            if match:
                lc_act = match.group(1).lower()
                continue

            match = re_lc_state.search(line)
            if match:
                lc_state = match.group(1).lower()
                continue

            match = re_lc_tout.search(line)
            if match:
                lc_timeout = match.group(1).lower()
                continue

            match = re_i2c_err.search(line)
            if match:
                i2c_err = match.group(1).lower()
                continue

            match = re_bbu_miss.search(line)
            if match:
                bbu_miss = match.group(1).lower()
                continue

            match = re_bbu_replace.search(line)
            if match:
                bbu_replace = match.group(1).lower()
                continue

            match = re_capac_low.search(line)
            if match:
                capac_low = match.group(1).lower()
                continue

            match = re_per_learn.search(line)
            if match:
                per_learn = match.group(1).lower()
                continue

            match = re_trans_learn.search(line)
            if match:
                trans_learn = match.group(1).lower()
                continue

            match = re_no_space.search(line)
            if match:
                no_space = match.group(1).lower()
                continue

            match = re_pack_fail.search(line)
            if match:
                pack_fail = match.group(1).lower()
                continue

            match = re_micro_upd.search(line)
            if match:
                micro_upd = match.group(1).lower()
                continue

        add_infos = []
        if exit_code:
            state = nagios.state.critical
        elif not batt_state:
            state = nagios.state.critical
            batt_state = 'unknown'
        elif batt_state.lower() != 'optimal':
            state = nagios.state.critical

        if voltage and voltage != 'ok':
            state = max_state(max_state, nagios.state.critical)
            add_infos.append("Voltage is %r." % (voltage))

        if temperature and temperature != 'ok':
            state = max_state(max_state, nagios.state.warning)
            add_infos.append("Temperature is %r." % (temperature))

        if lc_req and lc_req != 'no':
            state = max_state(max_state, nagios.state.warning)
            add_infos.append("Learn Cycle Requested: %r." % (lc_req))

        if lc_act and lc_act != 'no':
            state = max_state(max_state, nagios.state.warning)
            add_infos.append("Learn Cycle Active: %r." % (lc_act))

        if lc_state and lc_state != 'ok':
            state = max_state(max_state, nagios.state.warning)
            add_infos.append("Learn Cycle Status: %r." % (lc_state))

        if lc_timeout and lc_timeout != 'no':
            state = max_state(max_state, nagios.state.warning)
            add_infos.append("Learn Cycle Timeout: %r." % (lc_timeout))

        if i2c_err and i2c_err != 'no':
            state = max_state(max_state, nagios.state.warning)
            add_infos.append("I2c Errors Detected %r." % (i2c_err))

        if bbu_miss and bbu_miss != 'no':
            state = max_state(max_state, nagios.state.critical)
            add_infos.append("Battery Pack Missing: %r." % (bbu_miss))

        if bbu_replace and bbu_replace != 'no':
            state = max_state(max_state, nagios.state.critical)
            add_infos.append("Battery Replacement required: %r." % (bbu_replace))

        if capac_low and capac_low != 'no':
            state = max_state(max_state, nagios.state.warning)
            add_infos.append("Remaining Capacity Low: %r." % (capac_low))

        if per_learn and per_learn != 'no':
            state = max_state(max_state, nagios.state.warning)
            add_infos.append("Periodic Learn Required: %r." % (per_learn))

        if trans_learn and trans_learn != 'no':
            state = max_state(max_state, nagios.state.warning)
            add_infos.append("Transparent Learn: %r." % (trans_learn))

        if no_space and no_space != 'no':
            state = max_state(max_state, nagios.state.warning)
            add_infos.append("No space to cache offload %r." % (no_space))

        if pack_fail and pack_fail != 'no':
            state = max_state(max_state, nagios.state.warning)
            add_infos.append("Pack is about to fail & should be replaced: %r." % (pack_fail))

        if micro_upd and micro_upd != 'no':
            state = max_state(max_state, nagios.state.warning)
            add_infos.append("Module microcode update required: %r." % (micro_upd))

        add_info = ''
        if add_infos:
            add_info = '; ' + ', '.join(add_infos)

        out = "State of BBU of MegaRaid adapter %d (type %s): %s%s" % (
                self.adapter_nr, batt_type, batt_state, add_info)

        self.exit(state, out)


#==============================================================================

if __name__ == "__main__":

    pass

#==============================================================================

# vim: fileencoding=utf-8 filetype=python ts=4 et
