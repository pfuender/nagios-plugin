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

from nagios.common import pp, caller_search_path

from nagios.color_syslog import ColoredFormatter

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

#-------------------------------------------------------------------------------
class CommandNotFoundError(ExtNagiosPluginError):
    """
    Special exception, if one ore more OS commands were not found.

    """

    #--------------------------------------------------------------------------
    def __init__(self, cmd_list):
        """
        Constructor.

        @param cmd_list: all not found OS commands.
        @type cmd_list: list

        """

        self.cmd_list = None
        if cmd_list is None:
            self.cmd_list = ["Unknown OS command."]
        elif isinstance(cmd_list, list):
            self.cmd_list = cmd_list
        else:
            self.cmd_list = [cmd_list]

        if len(self.cmd_list) < 1:
            raise ValueError("Empty command list given.")

    #--------------------------------------------------------------------------
    def __str__(self):
        """
        Typecasting into a string for error output.
        """

        cmds = ', '.join(map(lambda x: ("'" + str(x) + "'"), self.cmd_list))
        msg = "Could not found OS command"
        if len(self.cmd_list) != 1:
            msg += 's'
        msg += ": " + cmds
        return msg

#-------------------------------------------------------------------------------
class ExecutionTimeoutError(ExtNagiosPluginError):
    """
    Special error class indicating a timout error on executing an operation
    """

    #--------------------------------------------------------------------------
    def __init__(self, timeout, command):
        """
        Constructor.

        @param timeout: the timeout in second, after which the exception
                        was raised.
        @type timeout: int
        @param command: the command, which should be executed.
        @type command: str

        """

        self.timeout = None
        try:
            self.timeout = int(timeout)
        except ValueError, e:
            log.error("Timeout %r was not an integer value.", timeout)

        self.command = command

    #--------------------------------------------------------------------------
    def __str__(self):
        """Typecasting into a string."""

        msg = None

        if self.timeout is None:
            msg = "Timeout after an unknown time on execution of %r." % (
                    self.command)
        else:
            msg = "Timeout after %d seconds on execution of %r." % (self.command)

        return msg

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
        if verbose:
            self.verbose = verbose

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

    #--------------------------------------------------------------------------
    def get_command(self, cmd, quiet = False):
        """
        Searches the OS search path for the given command and gives back the
        normalized position of this command.
        If the command is given as an absolute path, it check the existence
        of this command.

        @param cmd: the command to search
        @type cmd: str
        @param quiet: No warning message, if the command could not be found,
                      only a debug message
        @type quiet: bool

        @return: normalized complete path of this command, or None,
                 if not found
        @rtype: str or None
        """

        if self.verbose > 2:
            log.debug("Searching for command %r ..." % (cmd))

        if os.path.isabs(cmd):
            if not os.path.exists(cmd):
                log.warning("Command %r doesn't exists." % (cmd))
                return None
            if not os.access(cmd, os.X_OK):
                msg = ("Command %r is not executable." % (cmd))
                log.warning(msg)
                return None
            return os.path.normpath(cmd)

        search_paths = caller_search_path()
        if self.verbose > 2:
            log.debug("Searching command in %r ...", search_paths)

        for d in search_paths:
            p = os.path.join(d, cmd)
            if os.path.exists(p):
                if self.verbose > 2:
                    log.debug("Found %r ..." % (p))
                if os.access(p, os.X_OK):
                    return os.path.normpath(p)
                else:
                    msg = ("Command %r is not executable." % (p))
                    log.debug(msg)

        if quiet:
            if self.verbose > 2:
                log.debug("Command %r not found." % (cmd))
        else:
            log.warning("Command %r not found." % (cmd))
        return None

    #--------------------------------------------------------------------------
    def parse_args(self, args = None):
        """
        Executes self.argparser.parse_args().

        @param args: the argument strings to parse. If not given, they are
                     taken from sys.argv.
        @type args: list of str or None

        """

        super(ExtNagiosPlugin, self).parse_args(args)

        self.verbose = self.argparser.args.verbose

    #--------------------------------------------------------------------------
    def init_root_logger(self):
        """
        Initiialize the root logger.
        """

        root_log = logging.getLogger()
        root_log.setLevel(logging.INFO)
        if self.verbose:
            root_log.setLevel(logging.DEBUG)

        format_str = self.shortname + ': '
        if self.verbose:
            if self.verbose > 1:
                format_str += '%(name)s(%(lineno)d) %(funcName)s() '
            else:
                format_str += '%(name)s '
        format_str += '%(levelname)s - %(message)s'
        formatter = None
        if self.verbose:
            formatter = ColoredFormatter(format_str)
        else:
            formatter = logging.Formatter(format_str)

        # create log handler for console output
        lh_console = logging.StreamHandler(sys.stderr)
        if self.verbose:
            lh_console.setLevel(logging.DEBUG)
        else:
            lh_console.setLevel(logging.INFO)
        lh_console.setFormatter(formatter)

        root_log.addHandler(lh_console)

#==============================================================================

if __name__ == "__main__":

    pass

#==============================================================================

# vim: fileencoding=utf-8 filetype=python ts=4
