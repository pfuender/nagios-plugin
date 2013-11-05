#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
@author: Frank Brehm
@contact: frank.brehm@profitbricks.com
@copyright: © 2010 - 2013 by Frank Brehm, Berlin
@summary: Module for CheckVcbInstancePlugin class
"""

# Standard modules
import os
import sys
import re
import logging
import socket
import textwrap
import time
import select
import signal

from numbers import Number

# Third party modules

from pkg_resources import parse_version

# Own modules

import nagios
from nagios import BaseNagiosError

from nagios.common import pp, caller_search_path

from nagios.plugin import NagiosPluginError

from nagios.plugin.range import NagiosRange

from nagios.plugin.threshold import NagiosThreshold

from nagios.plugins import ExtNagiosPluginError
from nagios.plugins import ExecutionTimeoutError
from nagios.plugins import CommandNotFoundError
from nagios.plugins import ExtNagiosPlugin

#---------------------------------------------
# Some module variables

__version__ = '0.1.0'

log = logging.getLogger(__name__)

DEFAULT_TIMEOUT = 30
DEFAULT_VCB_PORT = 8072
DEFAULT_JOB_ID = 2
DEFAULT_POLLING_INTERVAL = 0.05
DEFAULT_BUFFER_SIZE = 8192

XML_TEMPLATE = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<pjd>
    <job-id>%d</job-id>
    <answer-to-socket>yes</answer-to-socket>
    <command>vcb-info</command>
</pjd>
"""

SIGNAL_NAMES = {
    signal.SIGHUP:  'HUP',
    signal.SIGINT:  'INT',
    signal.SIGABRT: 'ABRT',
    signal.SIGTERM: 'TERM',
    signal.SIGKILL: 'KILL',
    signal.SIGUSR1: 'USR1',
    signal.SIGUSR2: 'USR2',
}

STATUS = {
    'unknown':          0,
    'progress':         3,
    'failed':           4,
    'succeeded':        5,
    'in_progress_cont': 6,
    'continuing':       10,
}

re_parse_result = re.compile(r'^([^,]+),(\d+),(\d+),(.*)$', re.DOTALL)

# VCB_VERSION=8.6.29
re_version = re.compile(r'^\s*VCB_VERSION\s*=\s*(\S+)',
        re.IGNORECASE | re.MULTILINE)

#END_OF_DATA=TRUE
re_end_of_data = re.compile(r'^\s*end_of_data\s*=\s*(\S+)',
        re.IGNORECASE | re.MULTILINE)
re_true = re.compile(r'^(?:true|yes|[1-9])', re.IGNORECASE)

#==============================================================================
class SocketTransportError(NagiosPluginError):
    pass

#==============================================================================
class SocketConnectTimeoutError(SocketTransportError):
    pass

#==============================================================================
class NoListeningError(SocketTransportError):
    pass

#==============================================================================
class RequestStatusError(NagiosPluginError):
    pass

#==============================================================================
class RequestStatus(object):
    """
    A class for handling status replies from provisioning daemon.
    """

    #--------------------------------------------------------------------------
    def __init__(self, job_id = None, state = None,
            error_code = None, message = None):
        """
        Constructor.

        @param job_id: the job ID of this reply
        @type job_id: int
        @param state: the reply state (see VCB)
        @type state: int
        @param error_code: the VDC error code
        @type error_code: int
        @param message: the textual reply message
        @type message: str

        @return: None

        """

        self._job_id = job_id

        self._state = state

        self._error_code = error_code

        self._message = message

    #------------------------------------------------------------
    @property
    def job_id(self):
        """The job ID of this reply."""
        return self._job_id

    #------------------------------------------------------------
    @property
    def state(self):
        """The reply state (see VCB)."""
        return self._state

    #------------------------------------------------------------
    @property
    def error_code(self):
        """The VDC error code (old unused trash from somewhere)."""
        return self._error_code

    #------------------------------------------------------------
    @property
    def message(self):
        """The textual reply message."""
        return self._message

    #--------------------------------------------------------------------------
    def __str__(self):
        """
        Typecasting function for translating object structure into a string.

        @return: string as used as a reply from the provisioning daemon
        @rtype:  str
        """

        jid = self.job_id
        if jid is None:
            jid = '0'

        st = self.state
        if st is None:
            st = 0

        ec = self.error_code
        if ec is None:
            ec = 0

        msg = self.message
        if msg is None:
            msg = '<No message>'

        s = "%s,%d,%d,%s" % (jid, st, ec, msg)
        return s

    #--------------------------------------------------------------------------
    def as_dict(self):
        """
        Typecasting into a dictionary.

        @return: structure as dict
        @rtype:  dict

        """

        res = {
           '__class_name__': self.__class__.__name__,
            'error_code': self.error_code,
            'job_id': self.job_id,
            'message': self.message,
            'state': self.state,
        }

        return res

#==============================================================================
class CheckVcbInstancePlugin(ExtNagiosPlugin):
    """
    A special NagiosPlugin class for checking a running instance of VCB
    on a ProfitBricks physical server (pserver).
    """

    #--------------------------------------------------------------------------
    def __init__(self):
        """
        Constructor of the CheckVcbInstancePlugin class.
        """

        usage = """\
                %(prog)s [options] -H <server_address> [-P <VCB port>]
                """
        usage = textwrap.dedent(usage).strip()
        usage += '\n       %(prog)s --usage'
        usage += '\n       %(prog)s --help'

        blurb = "Copyright (c) 2013 Frank Brehm, Berlin.\n\n"
        blurb += "Checks the state and version of a running VCB instance."

        super(CheckVcbInstancePlugin, self).__init__(
                shortname = 'VCB_INSTANCE',
                usage = usage, blurb = blurb,
                version = __version__, timeout = DEFAULT_TIMEOUT,
        )

        self._host_address = None
        """
        @ivar: the DNS name or IP address of the host, running the VCB
        @type: str
        """

        self._vcb_port = DEFAULT_VCB_PORT
        """
        @ivar: the TCP port of VCB on the host to check
        @type: int
        """

        self._min_version = None
        """
        @ivar: the minimum version number of the running VCB
        @type: str or None
        """

        self._job_id = DEFAULT_JOB_ID
        """
        @ivar: the Job-Id to use in PJD to send to VCB
        @type: int
        """

        self._polling_interval = DEFAULT_POLLING_INTERVAL

        self._buffer_size = DEFAULT_BUFFER_SIZE

        self._should_shutdown = False

        self._cancel_signal = None

        self._add_args()

    #------------------------------------------------------------
    @property
    def host_address(self):
        """The DNS name or IP address of the host, running the VCB."""
        return self._host_address

    #------------------------------------------------------------
    @property
    def vcb_port(self):
        """The TCP port of VCB on the host to check."""
        return self._vcb_port

    @vcb_port.setter
    def vcb_port(self, value):
        v = abs(int(value))
        if v == 0:
            raise ValueError("The port must not be zero.")
        if v >= 2 ** 16:
            raise ValueError("The port must not greater than %d." % (
                    (2 ** 16 - 1)))
        self._vcb_port = v

    #------------------------------------------------------------
    @property
    def min_version(self):
        """The minimum version number of the running VCB."""
        return self._min_version

    #------------------------------------------------------------
    @property
    def cancel_signal(self):
        """Which signal got the process to cancel it."""
        return self._cancel_signal

    #------------------------------------------------------------
    @property
    def job_id(self):
        """The Job-Id to use in PJD to send to VCB."""
        return self._job_id

    @job_id.setter
    def job_id(self, value):
        v = int(value)
        self._job_id = abs(v)

    #------------------------------------------------------------
    @property
    def timeout(self):
        """Seconds before plugin times out."""
        if not hasattr(self, 'argparser'):
            return DEFAULT_TIMEOUT
        return self.argparser.args.timeout

    #------------------------------------------------------------
    @property
    def polling_interval(self):
        """The polling interval on network socket."""
        return self._polling_interval

    @polling_interval.setter
    def polling_interval(self, value):
        v = float(value)
        if v == 0:
            raise ValueError("The polling interval must not be zero.")
        self._polling_interval = abs(v)

    #------------------------------------------------------------
    @property
    def buffer_size(self):
        """The size of the buffer for the socket operation."""
        return self._buffer_size

    @buffer_size.setter
    def buffer_size(self, value):
        v = abs(int(value))
        if v < 512:
            raise ValueError("The buffer size must be greater than 512 bytes.")
        self._buffer_size = v

    #------------------------------------------------------------
    @property
    def should_shutdown(self):
        """Should the current process shutdown by a signal from outside."""
        return self._should_shutdown

    @should_shutdown.setter
    def should_shutdown(self, value):
        self._should_shutdown = bool(value)

    #--------------------------------------------------------------------------
    def as_dict(self):
        """
        Typecasting into a dictionary.

        @return: structure as dict
        @rtype:  dict

        """

        d = super(CheckVcbInstancePlugin, self).as_dict()

        d['host_address'] = self.host_address
        d['vcb_port'] = self.vcb_port
        d['min_version'] = self.min_version
        d['job_id'] = self.job_id
        d['timeout'] = self.timeout
        d['polling_interval'] = self.polling_interval
        d['should_shutdown'] = self.should_shutdown
        d['buffer_size'] = self.buffer_size
        d['cancel_signal'] = self.cancel_signal

        return d

    #--------------------------------------------------------------------------
    def _add_args(self):
        """
        Adding all necessary arguments to the commandline argument parser.
        """

        self.add_arg(
                '-H', '--host-address', '--host',
                metavar = 'ADDRESS',
                dest = 'host_address',
                required = True,
                help = ("The DNS name or IP address of the host, " +
                        "running the VCB (mandantory)."),
        )

        self.add_arg(
                '-P', '--port',
                metavar = 'PORT',
                dest = 'vcb_port',
                type = int,
                default = DEFAULT_VCB_PORT,
                help = ("The TCP port of VCB on the host to check " +
                        "(Default: %(default)d)."),
        )

        self.add_arg(
                '--min-version',
                metavar = 'VERSION',
                dest = 'min_version',
                help = ("The minimum version number of the running VCB. " +
                        "If given and the VCB version is less then this, " +
                        "a warning is generated."),
        )

        self.add_arg(
                '-J', '--job-id',
                metavar = 'ID',
                dest = 'job_id',
                type = int,
                default = DEFAULT_JOB_ID,
                help = ("The Job-Id to use in PJD to send to VCB " +
                        "(Default: %(default)d)."),
        )

        self.add_arg(
            '-b', '--buffer',
            metavar = 'SIZE',
            dest = 'buffer_size',
            type = int,
            default = DEFAULT_BUFFER_SIZE,
            help = ("The size of the buffer for the socket operation in " +
                    "bytes (Default: %(default)d)."),
        )

    #--------------------------------------------------------------------------
    def parse_args(self, args = None):
        """
        Executes self.argparser.parse_args().

        @param args: the argument strings to parse. If not given, they are
                     taken from sys.argv.
        @type args: list of str or None

        """

        super(CheckVcbInstancePlugin, self).parse_args(args)

        self._host_address = self.argparser.args.host_address
        if self.argparser.args.vcb_port:
            self.vcb_port = self.argparser.args.vcb_port
        if self.argparser.args.min_version:
            self._min_version = self.argparser.args.min_version
        if self.argparser.args.job_id:
            self.job_id = self.argparser.args.job_id
        if self.argparser.args.buffer_size is not None:
            self.buffer_size = self.argparser.args.buffer_size

    #--------------------------------------------------------------------------
    def __call__(self):
        """
        Method to call the plugin directly.
        """

        self.parse_args()
        self.init_root_logger()

        state = nagios.state.ok
        out = "VCB on %r port %d seems to be okay." % (
                self.host_address, self.vcb_port)

        if self.verbose > 2:
            log.debug("Current object:\n%s", pp(self.as_dict()))


        signal.signal(signal.SIGHUP, self.exit_signal_handler)
        signal.signal(signal.SIGINT, self.exit_signal_handler)
        signal.signal(signal.SIGABRT, self.exit_signal_handler)
        signal.signal(signal.SIGTERM, self.exit_signal_handler)
        signal.signal(signal.SIGUSR1, self.exit_signal_handler)
        signal.signal(signal.SIGUSR2, self.exit_signal_handler)

        xml = XML_TEMPLATE % (self.job_id)
        if self.verbose > 3:
            log.debug("XML to send:\n%s", xml)

        result = ''
        do_parse = False
        result_rcvd = False
        rstatus = None
        got_version = None

        try:
            result = self.send(xml)
            result = result.strip()
            do_parse = True
            result_rcvd = True
        except NoListeningError, e:
            result = "Error: " + str(e).strip()
            state = nagios.state.critical
        except SocketTransportError, e:
            result = "Error: " + str(e).strip()
            state = nagios.state.critical
        except Exception, e:
            result = "Error %s on checking VCB on %r port %d: %s" % (
                    e.__class__.__name__, self.host_address,
                    self.vcb_port, e)
            state = nagios.state.critical

        if self.verbose > 1:
            log.debug("Got result:\n%s.", result)

        if do_parse:
            try:
                rstatus = self.parse_result(result)
                while rstatus.state == STATUS['progress']:
                    lines = result.splitlines()
                    line_removed = lines.pop(0)
                    log.debug("Removed first line %r", line_removed)
                    result = '\n'.join(lines)
                    rstatus = self.parse_result(result)

                if rstatus.state != STATUS['succeeded']:
                    state = self.max_state(state, nagios.state.critical)
                result = rstatus.message
                result_rcvd = True
            except RequestStatusError, e:
                result = "Could not understand message: %s" % (result)
                state = self.max_state(state, nagios.state.critical)

        if result_rcvd:
            got_version = self.parse_for_version(result)
            result = ' '.join(result.splitlines())
            log.debug("Got a version of: %r", got_version)
            if got_version is None:
                state = self.max_state(state, nagios.state.warning)
                result += ' - no version found.'
            elif self.min_version is not None:
                parsed_version_expected = parse_version(self.min_version)
                if self.verbose > 1:
                    log.debug("Expecting parsed version %r.", parsed_version_expected)
                parsed_version_got = parse_version(got_version)
                if self.verbose > 1:
                    log.debug("Got parsed version %r.", parsed_version_got)
                if parsed_version_got < parsed_version_expected:
                    state = self.max_state(state, nagios.state.warning)
                    result += ' - version is less than %r.' % (self.min_version)

        out = result

        self.exit(state, out)

    #--------------------------------------------------------------------------
    def parse_for_version(self, msg):
        """
        Parses in the given message for a version string.
        """

        match = re_version.search(msg)
        if not match:
            return None
        return match.group(1)

    #--------------------------------------------------------------------------
    def exit_signal_handler(self, signum, frame):
        """
        Handler as a callback function for getting a signal from somewhere.

        @param signum: the gotten signal number
        @type signum: int
        @param frame: the current stack frame
        @type frame: None or a frame object

        """

        signame = "%d"  % (signum)
        if signum in SIGNAL_NAMES:
            signame = SIGNAL_NAMES[signum]

        log.debug("Got a signal %r.", signame)

        if (signum == signal.SIGUSR1) or (signum == signal.SIGUSR2):
            log.debug("Nothing to do on signal USR1 or USR2.")
            return

        log.info("Canceled.")
        self._cancel_signal = signame

        self.should_shutdown = True

    #--------------------------------------------------------------------------
    def send(self, message):
        """
        Sends the message over network socket to the recipient.
        It waits for all replies and gives them back all.

        @raise NoListeningError: if VCB isn't listening on the given port
        @raise SocketTransportError: on some communication errors or timeouts

        @param message: the message to send over the network
        @type message: str

        @return: response from server, or None
        @rtype: str

        """

        if self.verbose > 2:
            msg = "Sending message to %r, port %d with a timeout of %d seconds."
            log.debug(msg, self.host_address, self.vcb_port, self.timeout)

        def connect_alarm_caller(signum, sigframe):
            '''
            This nested function will be called in event of a timeout

            @param signum:   the signal number (POSIX) which happend
            @type signum:    int
            @param sigframe: the frame of the signal
            @type sigframe:  object
            '''

            raise SocketConnectTimeoutError("Timeout connecting to %r port %d." % (
                self.host_address, self.vcb_port))

        s = None
        sa = None
        for res in socket.getaddrinfo(self.host_address, self.vcb_port,
                socket.AF_UNSPEC, socket.SOCK_STREAM):

            if self.verbose > 3:
                log.debug("Socket address info: %r", res)
            af, socktype, proto, canonname, sa = res

            # Get the socket:
            try:
                signal.signal(signal.SIGALRM, connect_alarm_caller)
                signal.alarm(self.timeout)
                s = socket.socket(af, socktype, proto)
            except socket.error, msg:
                s = None
                continue
            finally:
                signal.alarm(0)

            if self.verbose > 3:
                log.debug("Got a socket: %r.", s)

            # Connect to the socket
            try:
                signal.signal(signal.SIGALRM, connect_alarm_caller)
                signal.alarm(self.timeout)
                s.connect(sa)
            except socket.error, msg:
                s.close()
                s = None
                continue
            finally:
                signal.alarm(0)
            break

        if s is None:
            msg = "VCB seems not to listen on %r, port %d." % (
                    self.host_address, self.vcb_port)
            raise NoListeningError(msg)

        if self.verbose > 3:
            msg = ("Got a socket address of %s." % (str(sa)))
            log.debug(msg)

        # Fileno of client socket
        s_fn = s.fileno()

        # Sending the message
        s.send(message)

        # Wait for an answer
        begin = time.time()
        data = ''
        break_on_timeout = False
        result_line = ''
        chunk = ''

        try:
            while not self.should_shutdown:

                cur_time = time.time()
                secs = cur_time - begin
                if self.verbose > 2:
                    log.debug("Current seconds: %0.2f", secs)

                if secs > self.timeout:
                    break_on_timeout = True
                    break

                rlist, wlist, elist = select.select(
                        [s_fn], [], [], self.polling_interval)

                if s_fn in rlist:
                    data = s.recv(self.buffer_size)
                    if data == '':
                        if self.verbose > 3:
                            log.debug("Socket closed from remote.")
                        if chunk != '':
                            break
                    result_line += data
                    chunk += data
                    match = re_end_of_data.search(result_line)
                    if match:
                        eod = match.group(1)
                        if re_true.search(eod):
                            log.debug("End of data reached.")
                            result_line = re_end_of_data.sub('', result_line)
                            break

                else:
                    if chunk != '':
                        chunk = ''

        except select.error, e:
            if e[0] == 4:
                pass
            else:
                log.error("Error in select(): "  + str(e))

        s.close()

        if break_on_timeout:
            secs = time.time() - begin
            msg = 'Timeout after %0.2f seconds.' % (secs)
            raise SocketTransportError(msg)

        return result_line

    #--------------------------------------------------------------------------
    def parse_result(self, message):
        """
        Parses the given string to get an instance of a RequestStatus object.

        @raise RequestStatusError: if not successful.

        @param message: the message to parse into a RequestStatus object.
        @type message: str


        """

        if message is None:
            raise RequestStatusError("Cannot parse a None object.")

        message = str(message).strip()

        match = re_parse_result.search(message)
        if not match:
            msg = (("Parsing error. Message %r doesn't match " +
                    "a status reply message.") % (message))
            raise RequestStatusError(msg)

        request_status = RequestStatus(
            job_id = str(match.group(1)).strip(),
            state = int(match.group(2)),
            error_code = int(match.group(3)),
            message = match.group(4),
        )

        return request_status

#==============================================================================

if __name__ == "__main__":

    pass

#==============================================================================

# vim: fileencoding=utf-8 filetype=python ts=4 et sw=4
