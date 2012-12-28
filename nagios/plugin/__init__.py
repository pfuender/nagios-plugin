#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
@author: Frank Brehm
@contact: frank.brehm@profitbricks.com
@copyright: (c) 2010 - 2012 by Frank Brehm, Berlin
@summary: Modules for NagiosPlugin class
"""

# Standard modules
import os
import sys
import logging
import pprint

# Third party modules

# Own modules

import nagios
from nagios import BaseNagiosError

from nagios.plugin.functions import get_shortname

from nagios.plugin.argparser import NagiosPluginArgparseError
from nagios.plugin.argparser import NagiosPluginArgparse
from nagios.plugin.argparser import lgpl3_licence_text, default_timeout

from nagios.plugin.performance import NagiosPerformanceError
from nagios.plugin.performance import NagiosPerformance

#---------------------------------------------
# Some module variables

__version__ = '0.2.0'

#==============================================================================
class NagiosPluginError(BaseNagiosError):
    """Special exceptions, which are raised in this module."""

    pass

#==============================================================================
class NagiosPlugin(object):
    """
    A encapsulating class for a Nagios plugin.
    """

    pass

    #--------------------------------------------------------------------------
    def __init__(self, usage = None, shortname = None,
            version = nagios.__version__, url = None, blurb = None,
            licence = lgpl3_licence_text, extra = None, plugin = None,
            timeout = default_timeout):
        """
        Constructor of the NagiosPlugin class.

        Instantiate object::

            from nagios.plugin import NagiosPlugin

            # Minimum arguments:
            na = NagiosPlugin(
                usage = 'Usage: %(prog)s --hello',
                version = '0.0.1',
            )

        @param usage: Short usage message used with --usage/-? and with missing
                      required arguments, and included in the longer --help
                      output. Can include %(prog)s placeholder which will be
                      replaced with the plugin name, e.g.:

                          usage = 'Usage: %(prog)s -H <hostname> -p <ports> [-v]'
        @type usage: str
        @param shortname: the shortname of the plugin
        @type shortname: str
        @param version: Plugin version number, included in the --version/-V
                        output, and in the longer --help output. e.g.::

                            $ ./check_tcp_range --version
                            check_tcp_range 0.2 [http://www.openfusion.com.au/labs/nagios/]
        @type version: str
        @param url: URL for info about this plugin, included in the
                    --version/-V output, and in the longer --help output.
                    Maybe omitted.
        @type url: str or None
        @param blurb: Short plugin description, included in the longer
                      --help output. Maybe omitted.
        @type blurb: str or None
        @param licence: License text, included in the longer --help output. By
                        default, this is set to the standard nagios plugins
                        LGPLv3 licence text.
        @type licence: str or None
        @param extra: Extra text to be appended at the end of the longer --help
                      output, maybe omitted.
        @type extra: str or None
        @param plugin: Plugin name. This defaults to the basename of your plugin.
        @type plugin: str or None
        @param timeout: Timeout period in seconds, overriding the standard
                        timeout default (15 seconds).
        @type timeout: int

        """

        self._shortname = shortname
        if self._shortname:
            self._shortname = self._shortname.strip()
        if not self._shortname:
            self._shortname = get_shortname()

        self.argparser = None
        if usage:
            self.argparser = NagiosPluginArgparse(
                    usage = usage,
                    version = version,
                    url = url,
                    blurb = blurb,
                    licence = licence,
                    extra = extra,
                    plugin = plugin,
                    timeout = timeout,
            )

        self.perfdata = []

        self.messages = {
                'warning': [],
                'critical': [],
                'ok': [],
        }

        self.threshold = None

    #------------------------------------------------------------
    @property
    def shortname(self):
        """The shortname of the plugin."""

        return self._shortname

    #--------------------------------------------------------------------------
    def add_perfdata(self, label, value, uom = None, threshold = None,
            warning = None, critical = None, min_data = None, max_data = None):
        """
        Adding a NagiosPerformance object to self.perfdata.

        @param label: the label of the performance data, mandantory
        @type label: str
        @param value: the value of the performance data, mandantory
        @type value: Number
        @param uom: the unit of measure
        @type uom: str or None
        @param threshold: an object for the warning and critical thresholds
                          if set, it overrides the warning and critical parameters
        @type threshold: NagiosThreshold or None
        @param warning: a range for the warning threshold,
                        ignored, if threshold is given
        @type warning: NagiosRange, str, Number or None
        @param critical: a range for the critical threshold,
                        ignored, if threshold is given
        @type critical: NagiosRange, str, Number or None
        @param min_data: the minimum data for performance output
        @type min_data: Number or None
        @param max_data: the maximum data for performance output
        @type max_data: Number or None

        """

        pdata = NagiosPerformance(
                label = label,
                value = value,
                uom = uom,
                threshold = threshold,
                warning = warning,
                critical = critical,
                min_data = min_data,
                max_data = max_data
        )

        self.perfdata.append(pdata)

    #--------------------------------------------------------------------------
    def all_perfoutput(self):
        """Generates a string with all formatted performance data."""

        return ' '.join(map(lambda x: x.perfoutput(), self.perfdata))

    #--------------------------------------------------------------------------
    def set_thresholds(self, warning = None, critical = None):
        """
        Initialisation of self.threshold as a the NagiosThreshold object.

        @param warning: the warning threshold
        @type warning: str, int, long, float or NagiosRange
        @param critical: the critical threshold
        @type critical: str, int, long, float or NagiosRange

        """

        self.threshold = NagiosThreshold(
                warning = warning, critical = critical)

    #--------------------------------------------------------------------------
    def nagios_exit(self, code, message):
        """Wrapper method for nagios.plugin.functions.nagios_exit()."""

        return nagios.plugin.functions.nagios_exit(code, message, self)

    #--------------------------------------------------------------------------
    def nagios_die(self, message):
        """Wrapper method for nagios.plugin.functions.nagios_die()."""

        return nagios.plugin.functions.nagios_die(message, self)

    #--------------------------------------------------------------------------
    def die(self, message):
        """Wrapper method for nagios.plugin.functions.nagios_die()."""

        return nagios.plugin.functions.nagios_die(message, self)

    #--------------------------------------------------------------------------
    def max_state(self, *args):
        """Wrapper method for nagios.plugin.functions.max_state()."""

        return nagios.plugin.functions.max_state(*args)

    #--------------------------------------------------------------------------
    def max_state_alt(self, *args):
        """Wrapper method for nagios.plugin.functions.max_state_alt()."""

        return nagios.plugin.functions.max_state_alt(*args)

#==============================================================================

if __name__ == "__main__":

    pass

#==============================================================================

# vim: fileencoding=utf-8 filetype=python ts=4
