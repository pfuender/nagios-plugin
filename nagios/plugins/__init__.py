#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
@author: Frank Brehm
@contact: frank.brehm@profitbricks.com
@copyright: © 2010 - 2013 by Frank Brehm, Berlin
@summary: Modules for extended NagiosPlugin classes
"""

# Standard modules
import os
import sys
import logging

# Third party modules

# Own modules

import nagios
from nagios import BaseNagiosError

from nagios.common import pp

from nagios.plugin import NagiosPluginError
from nagios.plugin import NagiosPlugin

from nagios.plugin.argparser import lgpl3_licence_text, default_timeout

#---------------------------------------------
# Some module variables

__version__ = '0.1.0'

log = logging.getLogger(__name__)

#==============================================================================
class ExtNagiosPluginError(NagiosPluginError):
    """Special exceptions, which are raised in this module."""

    pass

#==============================================================================
class ExtNagiosPlugin(NagiosPlugin):
    """
    An extended Nagios plugin class.

    """

    #--------------------------------------------------------------------------
    def __init__(self, usage = None, shortname = None,
            version = nagios.__version__, url = None, blurb = None,
            licence = lgpl3_licence_text, extra = None, plugin = None,
            timeout = default_timeout, verbose = 0):
        """
        Constructor of the ExtNagiosPlugin class.

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
        @param verbose: verbosity level inside the module
        @type verbose: int

        """

        self._verbose = 0
        """
        @ivar: The verbosity level inside the module.
        @type: int
        """
        if value:
            self.value = value

        super(ExtNagiosPlugin, self).__init__(
                usage = usage,
                shortname = shortname,
                version = version,
                url = url,
                blurb = blurb,
                licence = licence,
                extra = extra,
                plugin = plugin,
                timeout = timeout
        )

    #------------------------------------------------------------
    @property
    def verbose(self):
        """The verbosity level inside the module."""
        return self._verbose

    @verbose.setter
    def verbose(self, value):
        val = int(value)
        if val < 0:
            log.warn("A negative verbose level (%r)is not supported.", value)
        else:
            self._verbose = val

    #--------------------------------------------------------------------------
    def as_dict(self):
        """
        Typecasting into a dictionary.

        @return: structure as dict
        @rtype:  dict

        """

        d = super(ExtNagiosPlugin, self).as_dict()

        d['verbose'] = self.verbose

        return d

#==============================================================================

if __name__ == "__main__":

    pass

#==============================================================================

# vim: fileencoding=utf-8 filetype=python ts=4
