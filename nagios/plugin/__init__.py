#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
@author: Frank Brehm
@contact: frank.brehm@profitbricks.com
@copyright: © 2010 - 2015 by Frank Brehm, Berlin
@summary: Modules for NagiosPlugin class
"""

# Standard modules
import os
import sys
import logging
import signal
import errno

from numbers import Number

# Third party modules

# Own modules

import nagios
from nagios import BaseNagiosError

from nagios.common import pp

import nagios.plugin.functions
from nagios.plugin.functions import get_shortname

from nagios.plugin.argparser import NagiosPluginArgparseError
from nagios.plugin.argparser import NagiosPluginArgparse
from nagios.plugin.argparser import lgpl3_licence_text, default_timeout

from nagios.plugin.threshold import NagiosThreshold

from nagios.plugin.performance import NagiosPerformanceError
from nagios.plugin.performance import NagiosPerformance

#---------------------------------------------
# Some module variables

__version__ = '0.4.0'

log = logging.getLogger(__name__)

#==============================================================================
class NagiosPluginError(BaseNagiosError):
    """Special exceptions, which are raised in this module."""

    pass

#==============================================================================
class NPReadTimeoutError(NagiosPluginError, IOError):
    """
    Special error class indicating a timout error on reading of a file.
    """

    #--------------------------------------------------------------------------
    def __init__(self, timeout, filename):
        """
        Constructor.

        @param timeout: the timout in seconds leading to the error
        @type timeout: float
        @param filename: the filename leading to the error
        @type filename: str

        """

        t_o = None
        try:
            t_o = float(timeout)
        except ValueError:
            pass
        self.timeout = t_o

        strerror = "Timeout error on reading"
        if t_o is not None:
            strerror += " (timeout after %0.1f secs)" % (t_o)

        if filename is None:
            super(NPReadTimeoutError, self).__init__(
                    errno.ETIMEDOUT, strerror)
        else:
            super(NPReadTimeoutError, self).__init__(
                    errno.ETIMEDOUT, strerror, filename)

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
            self._shortname = get_shortname(plugin = plugin)

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

    @shortname.setter
    def shortname(self, value):
        new_name = str(value).strip()
        if not new_name:
            msg = "New shortname %r may not be empty."
            raise NagiosPluginError(msg % (value))
        self._shortname = new_name

    #--------------------------------------------------------------------------
    def as_dict(self):
        """
        Typecasting into a dictionary.

        @return: structure as dict
        @rtype:  dict

        """

        d = {
                '__class__': self.__class__.__name__,
                'shortname': self.shortname,
                'argparser': None,
                'perfdata': [],
                'messages': self.messages,
                'threshold': None,
        }

        if self.argparser:
            d['argparser'] = self.argparser.as_dict()

        for pdata in self.perfdata:
            d['perfdata'].append(pdata.as_dict())

        if self.threshold:
            d['threshold'] = self.threshold.as_dict()

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
        fields.append("shortname=%r" % (self.shortname))
        fields.append("argparser=%r" % (self.argparser))
        fields.append("perfdata=%r" % (self.perfdata))
        fields.append("messages=%r" % (self.messages))
        fields.append("threshold=%r" % (self.threshold))

        out += ", ".join(fields) + ")>"
        return out

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
    def add_arg(self, *names, **kwargs):
        """top level interface to my NagiosPluginArgparse object."""

        if self.argparser:
            self.argparser.add_arg(*names, **kwargs)
        else:
            log.warn("Called add_arg() without a valid " +
                    "NagiosPluginArgparse object.")

    #--------------------------------------------------------------------------
    def parse_args(self, args = None):
        """
        Executes self.argparser.parse_args().

        @param args: the argument strings to parse. If not given, they are
                     taken from sys.argv.
        @type args: list of str or None

        """

        if args is None:
            args = sys.argv[1:]

        if self.argparser:
            log.debug("Parsing commandline arguments: %r", args)
            self.argparser.parse_args(args)
        else:
            log.warn("Called parse_args() without a valid " +
                    "NagiosPluginArgparse object.")

    #--------------------------------------------------------------------------
    def getopts(self, args = None):
        """
        Wrapper for self.parse_args().

        @param args: the argument strings to parse.
        @type args: list of str or None

        """

        self.parse_args(args)

    #--------------------------------------------------------------------------
    def all_perfoutput(self):
        """Generates a string with all formatted performance data."""

        return ' '.join([x.perfoutput() for x in self.perfdata])

    #--------------------------------------------------------------------------
    def set_thresholds(self, warning = None, critical = None):
        """
        Initialisation of self.threshold as a the NagiosThreshold object.

        @param warning: the warning threshold
        @type warning: str, int, long, float or NagiosRange
        @param critical: the critical threshold
        @type critical: str, int, long, float or NagiosRange

        @return: the generated threshold object
        @rtype: NagiosThreshold

        """

        self.threshold = NagiosThreshold(
                warning = warning, critical = critical)

        return self.threshold

    #--------------------------------------------------------------------------
    def check_threshold(self, value, warning = None, critical = None):
        """
        Evaluates value against the thresholds and returns nagios.state.ok,
        nagios.state.warning or nagios.state.critical.

        The thresholds may be:
            - explicitly set by passing 'warning' and/or 'critical' parameters
              to check_threshold() or
            - explicitly set by calling set_thresholds() before check_threshold(),
              or
            - implicitly set by command-line parameters -w, -c, --critical or
              --warning, if you have run plugin.parse_args()

        @param value: the value to check
        @type value: Number
        @param warning: the warning threshold for the given value
        @type warning: NagiosRange, str or None
        @param critical: the critical threshold for the given value
        @type critical: NagiosRange, str or None

        @return: an exit value ready to pass to nagios_exit(), e.g.::

                    plugin.nagios_exit(
                            code = plugin.check_threshold(value),
                            message = (" sample result was %d" % (value)),
                    )

        @rtype: int

        """

        if not isinstance(value, Number):
            msg = "Value %r must be a number on calling check_threshold()."
            raise NagiosPluginError(msg % (value))

        if warning is not None or critical is not None:
            self.set_thresholds(
                    warning = warning,
                    critical = critical,
            )
        elif self.threshold:
            pass
        elif self.argparser is not None and self.argparser.has_parsed:
            self.set_thresholds(
                    warning = getattr(self.argparser.args, 'warning', None),
                    critical = getattr(self.argparser.args, 'critical', None),
            )
        else:
            return nagios.state.unknown

        return self.threshold.get_status(value)

    #--------------------------------------------------------------------------
    def nagios_exit(self, code, message):
        """Wrapper method for nagios.plugin.functions.nagios_exit()."""

        return nagios.plugin.functions.nagios_exit(code, message, self)

    #--------------------------------------------------------------------------
    def nagios_die(self, message):
        """Wrapper method for nagios.plugin.functions.nagios_die()."""

        return nagios.plugin.functions.nagios_die(message, self)

    #--------------------------------------------------------------------------
    def exit(self, code, message):
        """Wrapper method for nagios.plugin.functions.nagios_exit()."""

        return nagios.plugin.functions.nagios_exit(code, message, self)

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

    #--------------------------------------------------------------------------
    def add_message(self, code, *messages):
        """Adds one ore more messages to self.messages under the appropriate
           subkey, which is defined by the code."""

        key = str(code).upper()
        if (not key in nagios.plugin.functions.ERRORS and
                not code in nagios.plugin.functions.STATUS_TEXT):
            msg = "Invalid error code %r on calling add_message()." % (code)
            raise NagiosPluginError(msg)

        if key.lower() in ('unknown', 'dependent'):
            msg = "Error code %r not supported by add_message()." % (code)
            raise NagiosPluginError(msg)

        if code in nagios.plugin.functions.STATUS_TEXT:
            key = nagios.plugin.functions.STATUS_TEXT[code]
        key = key.lower()

        if not key in self.messages:
            self.messages[key] = []
        for msg in messages:
            self.messages[key].append(msg)

    #--------------------------------------------------------------------------
    def check_messages(self, critical = None, warning = None, ok = None,
            join = ' ', join_all = False):
        """
        Method to check the given messages and the messages under self.messages
        and to returning an appropriate return code and/or result message.

        @param critical: a list or a single critical message
        @type critical: list of str or str or None
        @param warning: a list or a single warning message
        @type warning: list of str or str or None
        @param ok: a list or a single message
        @type ok: list of str or str or None
        @param join: a string used to join the relevant list to generate the
                     message string returned. I.e. if the 'critical' list
                     is non-empty, check_messages would return
                     as the result message::

                        join.join(critical)

        @type join: str
        @param join_all: by default only one, the appropriate set of messages
                         are joined and returned in the result message. If the
                         result is critical, only the 'critical' messages
                         are included. If join_all is supplied, however,
                         it will be used as a string to join the resultant
                         critical, warning, and ok messages together i.e. all
                         messages are joined and returned.
        @type join_all: str

        @return: the appropriate nagios return code and the appropriate message
        @rtype: tuple

        """

        args = {
            'join': join,
            'join_all': join_all,
        }

        if critical is None:
            critical = []
        elif isinstance(critical, str):
            critical = [critical]
        for msg in self.messages['critical']:
            critical.append(msg)
        args['critical'] = critical

        if warning is None:
            warning = []
        elif isinstance(warning, str):
            warning = [warning]
        for msg in self.messages['warning']:
            warning.append(msg)
        args['warning'] = warning

        if ok is None:
            ok = []
        elif isinstance(ok, str):
            ok = [ok]
        for msg in self.messages['ok']:
            ok.append(msg)
        if ok:
            args['ok'] = ok

        log.debug("Arguments for nagios.plugin.functions.check_messages():\n%r",
                args)

        return nagios.plugin.functions.check_messages(**args)

    #--------------------------------------------------------------------------
    def read_file(self, filename, timeout = 2, quiet = False):
        """
        Reads the content of the given filename.

        @raise IOError: if file doesn't exists or isn't readable
        @raise PbReadTimeoutError: on timeout reading the file

        @param filename: name of the file to read
        @type filename: str
        @param timeout: the amount in seconds when this method should timeout
        @type timeout: int
        @param quiet: increases the necessary verbosity level to
                      put some debug messages
        @type quiet: bool

        @return: file content
        @rtype:  str

        """

        def read_alarm_caller(signum, sigframe):
            '''
            This nested function will be called in event of a timeout

            @param signum:   the signal number (POSIX) which happend
            @type signum:    int
            @param sigframe: the frame of the signal
            @type sigframe:  object
            '''

            raise NPReadTimeoutError(timeout, filename)

        timeout = abs(int(timeout))

        if not os.path.isfile(filename):
            raise IOError(errno.ENOENT, "File doesn't exists", filename)
        if not os.access(filename, os.R_OK):
            raise IOError(errno.EACCES, 'Read permission denied', filename)

        if not quiet:
            log.debug("Reading file content of %r ...", filename)

        signal.signal(signal.SIGALRM, read_alarm_caller)
        signal.alarm(timeout)

        content = ''
        fh = open(filename, 'r')
        for line in fh.readlines():
            content += line
        fh.close()

        signal.alarm(0)

        return content


#==============================================================================

if __name__ == "__main__":

    pass

#==============================================================================

# vim: fileencoding=utf-8 filetype=python ts=4 expandtab
