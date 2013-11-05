#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
@author: Frank Brehm
@contact: frank.brehm@profitbricks.com
@copyright: © 2010 - 2013 by Frank Brehm, Berlin
@summary: Module for CheckMegaRaidPlugin class for a nagios/icinga plugin
          to check a LSI MegaRaid adapter and volumes
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

from nagios.plugin.range import NagiosRange

from nagios.plugin.threshold import NagiosThreshold

from nagios.plugin.argparser import default_timeout

from nagios.plugins import ExtNagiosPluginError
from nagios.plugins import ExecutionTimeoutError
from nagios.plugins import CommandNotFoundError
from nagios.plugins import ExtNagiosPlugin

#---------------------------------------------
# Some module variables

__version__ = '0.4.0'

log = logging.getLogger(__name__)

re_exit_code = re.compile(r'^\s*Exit\s*Code\s*:\s+0x([0-9a-f]+)', re.IGNORECASE)
re_no_adapter = re.compile(r'^\s*User\s+specified\s+controller\s+is\s+not\s+present',
        re.IGNORECASE)

#==============================================================================
class CheckMegaRaidPlugin(ExtNagiosPlugin):
    """
    A special NagiosPlugin class for checking the state of a LSI MegaRaid
    adapter and its connected enclosures, physical drives and logical volumes.
    """

    #--------------------------------------------------------------------------
    def __init__(self, usage = None, shortname = None, version = None,
            blurb = None,):
        """
        Constructor of the CheckMegaRaidPlugin class.

        @param usage: Short usage message used with --usage/-? and with missing
                      required arguments, and included in the longer --help
                      output. Can include %(prog)s placeholder which will be
                      replaced with the plugin name, e.g.::

                          usage = 'Usage: %(prog)s -H <hostname> -p <ports> [-v]'

        @type usage: str
        @param shortname: the shortname of the plugin
        @type shortname: str
        @param version: Plugin version number, included in the --version/-V
                        output, and in the longer --help output. e.g.::

                            $ ./check_tcp_range --version
                            check_tcp_range 0.2 [http://www.openfusion.com.au/labs/nagios/]
        @type version: str
        @param blurb: Short plugin description, included in the longer
                      --help output. Maybe omitted.
        @type blurb: str or None

        """

        used_version = __version__
        if version:
            used_version = str(version) + (' (%s)' % (__version__))

        super(CheckMegaRaidPlugin, self).__init__(
                usage = usage, blurb = blurb, shortname = shortname,
                version = used_version,
        )

        self._adapter_nr = 0
        """
        @ivar: the number of the MegaRaid adapter (e.g. 0)
        @type: str
        """

        self._megacli_cmd = None
        """
        @ivar: the path to the executable MegaCli command
        @type: str
        """

        self._timeout = default_timeout
        """
        @ivar: the timeout on execution of MegaCli in seconds
        @type: int
        """

        self._init_megacli_cmd()

    #------------------------------------------------------------
    @property
    def adapter_nr(self):
        """The number of the MegaRaid adapter (e.g. 0)."""
        return self._adapter_nr

    #------------------------------------------------------------
    @property
    def megacli_cmd(self):
        """The path to the executable MegaCli command."""
        return self._megacli_cmd

    #------------------------------------------------------------
    @property
    def timeout(self):
        """The timeout on execution of MegaCli in seconds."""
        return self._timeout

    #--------------------------------------------------------------------------
    def as_dict(self):
        """
        Typecasting into a dictionary.

        @return: structure as dict
        @rtype:  dict

        """

        d = super(CheckMegaRaidPlugin, self).as_dict()

        d['adapter_nr'] = self.adapter_nr
        d['megacli_cmd'] = self.megacli_cmd
        d['timeout'] = self.timeout

        return d

    #--------------------------------------------------------------------------
    def _add_args(self):
        """
        Adding all necessary arguments to the commandline argument parser.
        """

        self.add_arg(
                '-a', '--adapter-nr',
                metavar = 'NR',
                dest = 'adapter_nr',
                required = True,
                type = int,
                default = 0,
                help = ("The number of the MegaRaid adapter to check " + 
                        "(Default: %(default)d)."),
        )

        self.add_arg(
                '--megacli',
                metavar = 'CMD',
                dest = 'megacli_cmd',
                default = self.megacli_cmd,
                help = ("The path to the executable MegaCli command " +
                        "(Default: %(default)r)."),
        )

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

        def is_exe(fpath):
            return os.path.isfile(fpath) and os.access(fpath, os.X_OK)

        exe_names = ('MegaCli64', 'MegaCli', 'megacli')
        if given_path:
            # Normalize the given path, if it exists.
            if os.path.isabs(given_path):
                if not is_exe(given_path):
                    return None
                return os.path.realpath(given_path)
            exe_names = (given_path,)

        search_paths = os.environ["PATH"].split(os.pathsep)
        sbin_paths = (
            os.sep + 'sbin',
            os.sep + os.path.join('usr', 'sbin'),
            os.sep + os.path.join('usr', 'local', 'sbin'),
            os.sep + os.path.join('opt', 'bin'),
            os.sep + os.path.join('opt', 'sbin'),
        )
        for sbin in sbin_paths:
            if not sbin in search_paths:
                search_paths.append(sbin)

        for exe_name in exe_names:
            for path in os.environ["PATH"].split(os.pathsep):
                path = path.strip('"')
                exe_file = os.path.join(path, exe_name)
                if is_exe(exe_file):
                    return exe_file

        return None

    #--------------------------------------------------------------------------
    def parse_args(self, args = None):
        """
        Executes self.argparser.parse_args().

        If overridden by successors, it should be called via super().

        @param args: the argument strings to parse. If not given, they are
                     taken from sys.argv.
        @type args: list of str or None

        """

        super(CheckMegaRaidPlugin, self).parse_args(args)

        self._adapter_nr = self.argparser.args.adapter_nr

        if self.argparser.args.timeout:
            self._timeout = self.argparser.args.timeout

        if self.argparser.args.megacli_cmd:

            megacli_cmd = self._get_megacli_cmd(self.argparser.args.megacli_cmd)
            if not megacli_cmd:
                self.die(("Could not find MegaCli command %r." %
                        self.argparser.args.megacli_cmd))
            self._megacli_cmd = megacli_cmd

    #--------------------------------------------------------------------------
    def pre_call(self):
        """
        A method, which is called before the underlaying actions are called.
        """

        self.parse_args()
        self.init_root_logger()

        if not self.megacli_cmd:
            self.die("Could not find 'MegaCli64' or 'MegaCli' in OS PATH.")

    #--------------------------------------------------------------------------
    def __call__(self):

        self.pre_call()

        if self.verbose > 2:
            log.debug("Current object:\n%s", pp(self.as_dict()))

        self.call()

    #--------------------------------------------------------------------------
    def call(self):
        """
        Method to call the plugin directly.
        """

        self.die("The method call() must be overridden in inherited class %r." % (
                self.__class__.__name__))

    #--------------------------------------------------------------------------
    def megacli(self, args, nolog = True, no_adapter = False):
        """
        Method to call MegaCli directly with the given arguments.

        @param args: the arguments given on calling the binary. If args is of
                     type str, then this will used as a single argument in
                     calling MegaCli (no shell command line splitting).
        @type args: list of str or str
        @param nolog: don't append -NoLog to the command line parameters
        @type nolog: bool
        @param no_adapter: don't append '-a<adapter_nr>' to the
                           command line parameters
        @type no_adapter: bool

        @return: a tuple with four values:
                 * the output on STDOUT
                 * the output on STDERR
                 * the return value to the operating system
                 * the exit value extracted from output
        @rtype: tuple

        """

        cmd_list = [self.megacli_cmd]
        if args:
            if isinstance(args, str):
                cmd_list.append(args)
            else:
                for arg in args:
                    cmd_list.append(arg)

        if not no_adapter:
            cmd_list.append('-a')
            cmd_list.append(("%d" % (self.adapter_nr)))

        if nolog:
            cmd_list.append('-NoLog')

        cmd_list = [str(element) for element in cmd_list]

        (ret, stdoutdata, stderrdata) = self.exec_cmd(cmd_list)

        exit_code = ret
        no_adapter_found = False
        if stdoutdata:
            for line in stdoutdata.splitlines():

                if not no_adapter:
                    if re_no_adapter.search(line):
                        self.die('The specified controller %d is not present.' % (
                                self.adapter_nr))

                match = re_exit_code.search(line)
                if match:
                    exit_code = int(match.group(1), 16)
                    continue

        return (stdoutdata, stderrdata, ret, exit_code)


#==============================================================================

if __name__ == "__main__":

    pass

#==============================================================================

# vim: fileencoding=utf-8 filetype=python ts=4 et
