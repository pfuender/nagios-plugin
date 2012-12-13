#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
@author: Frank Brehm
@contact: frank.brehm@profitbricks.com
@copyright: (c) 2010 - 2012 by Frank Brehm, Berlin
@summary: Module for a NagiosPluginArgparse class, a class providing a
          standardised argument processing for Nagios plugins
"""

# Standard modules
import os
import sys
import logging
import pprint

import argparse

from argparse import Namespace

# Third party modules

# Own modules

import nagios
from nagios import BaseNagiosError

#---------------------------------------------
# Some module variables

__version__ = '0.2.0'

log = logging.getLogger(__name__)

lgpl3_licence_text = """
This nagios plugin is free software, and comes with ABSOLUTELY
NO WARRANTY. It may be used, redistributed and/or modified under
the terms of the GNU Lesser General Public License (LGPL), Version 3 (see
http://www.gnu.org/licenses/lgpl).
""".strip()

default_timeout = 15
default_verbose = 0

#==============================================================================
class NagiosPluginArgparse(object):
    """
    A class providing a standardised argument processing for Nagios plugins.
    """

    pass

    #--------------------------------------------------------------------------
    def __init__(self, usage, version = nagios.__version__, url = None,
            blurb = None, licence = lgpl3_licence_text, extra = None,
            plugin = None, timeout = default_timeout):
        """
        Constructor of the NagiosPluginArgparse class.

        Instantiate object::

            from nagios.plugin.argparser import NagiosPluginArgparse

            # Minimum arguments:
            na = NagiosPluginArgparse(
                usage = 'Usage: %(prog)s --hello',
                version = '0.0.1',
            )

        @param usage: Short usage message used with --usage/-? and with missing
                      required arguments, and included in the longer --help
                      output. Can include %(prog)s placeholder which will be
                      replaced with the plugin name, e.g.:

                          usage = 'Usage: %(prog)s -H <hostname> -p <ports> [-v]'
        @type usage: str
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

        self._usage = str(usage).strip()
        """
        @ivar: Short usage message
        @type: str
        """

        self._version = str(version).strip()
        """
        @ivar: Plugin version number.
        @type: str
        """

        self._url = url
        """
        @ivar: URL for info about this plugin
        @type: str or None
        """
        if self._url:
            self._url = self._url.strip()

        self._blurb = blurb
        """
        @ivar: Short plugin description
        @type: str or None
        """
        if self._blurb:
            self._blurb = self._blurb.strip()

        self._licence = str(licence).strip()
        """
        @ivar: License text.
        @type: str
        """

        self._extra = extra
        """
        @ivar: Extra text to be appended at the end of the --help output.
        @type: str or None
        """
        if self._extra:
            self._extra = self._extra.strip()

        default_pluginname = sys.argv[0]
        if 'NAGIOS_PLUGIN' in os.environ:
            default_pluginname = os.environ['NAGIOS_PLUGIN']
        default_pluginname = os.path.basename(default_pluginname)
        self._plugin = default_pluginname
        """
        @ivar: Plugin name. This defaults to the basename of your plugin.
        @type: str
        """
        if plugin:
            p = str(plugin).strip()
            if p:
                self._plugin = p

        self._timeout = default_timeout
        """
        @ivar: Timeout period in seconds.
        @type: int
        """
        if timeout:
            to = int(timeout)
            if to > 0:
                self._timeout = to
            else:
                raise ValueError("Wrong timout %r given, must be > 0." % (
                        timeout))

        self.args = Namespace()
        """
        @ivar: the arguments after parsing the command line
        @type: Namespace
        """

    #------------------------------------------------------------
    @property
    def usage(self):
        """Short usage message."""
        return self._usage

    #------------------------------------------------------------
    @property
    def version(self):
        """Plugin version number."""
        return self._version

    #------------------------------------------------------------
    @property
    def url(self):
        """URL for info about this plugin."""
        return self._url

    #------------------------------------------------------------
    @property
    def blurb(self):
        """Short plugin description."""
        return self._blurb

    #------------------------------------------------------------
    @property
    def licence(self):
        """The licence text."""
        return self._licence

    #------------------------------------------------------------
    @property
    def extra(self):
        """Extra text to be appended at the end of the --help output."""
        return self._extra

    #------------------------------------------------------------
    @property
    def plugin(self):
        """The name of the plugin."""
        return self._plugin

    #------------------------------------------------------------
    @property
    def timeout(self):
        """The timeout period in seconds."""
        return self._timeout

    #--------------------------------------------------------------------------
    def as_dict(self):
        """
        Typecasting into a dictionary.

        @return: structure as dict
        @rtype:  dict

        """

        d = {
                '__class__': self.__class__.__name__,
                'usage': self.usage,
                'version': self.version,
                'url': self.url,
                'blurb': self.blurb,
                'licence': self.licence,
                'extra': self.extra,
                'plugin': self.plugin,
                'timeout': self.timeout,
                'args': self.args,
        }

        return d

    #--------------------------------------------------------------------------
    def __str__(self):
        """
        Typecasting function for translating object structure into a string.

        @return: structure as string
        @rtype:  str

        """

        pretty_printer = pprint.PrettyPrinter(indent = 4)
        return pretty_printer.pformat(self.as_dict())

    #--------------------------------------------------------------------------
    def __repr__(self):
        """Typecasting into a string for reproduction."""

        out = "<%s(" % (self.__class__.__name__)

        fields = []
        fields.append("usage=%r" % (self.usage))
        fields.append("version=%r" % (self.version))
        fields.append("url=%r" % (self.url))
        fields.append("blurb=%r" % (self.blurb))
        fields.append("licence=%r" % (self.licence))
        fields.append("extra=%r" % (self.extra))
        fields.append("plugin=%r" % (self.plugin))
        fields.append("timeout=%r" % (self.timeout))
        fields.append("args=%r" % (self.args))

        out += ", ".join(fields) + ")>"
        return out

    #--------------------------------------------------------------------------
    def parse_args(self, args = None):
        """
        Provides the main parsing functionality. Parses the parameters
        and stores the results in self.args.
        """

        pass

#==============================================================================

if __name__ == "__main__":

    pass

#==============================================================================

# vim: fileencoding=utf-8 filetype=python ts=4
