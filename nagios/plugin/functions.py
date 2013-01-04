#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
@author: Frank Brehm
@contact: frank.brehm@profitbricks.com
@copyright: (c) 2010 - 2012 by Frank Brehm, Berlin
@summary: Module for using in NagiosPlugin class
"""

# Standard modules
import os
import sys
import re

# Third party modules

# Own modules

import nagios

from nagios import FakeExitError

__version__ = '0.2.2'

#---------------------------------------------
# Some module variables

ERRORS = {
    'OK': nagios.state.ok,
    'WARNING': nagios.state.warning,
    'CRITICAL': nagios.state.critical,
    'UNKNOWN': nagios.state.unknown,
    'DEPENDENT': nagios.state.dependend,
}

STATUS_TEXT = {}
for key in ERRORS.keys():
    val = ERRORS[key]
    STATUS_TEXT[val] = key

# _fake_exit flag and accessor/mutator, for testing
_fake_exit = False

# _use_die flag and accessor/mutator, so exceptions can be raised correctly
_use_die = False

#------------------------------------------------------------------------------
def get_shortname(obj = None):

    shortname = None

    if hasattr(obj, 'shortname'):
        return getattr(obj, 'shortname')

    shortname = getattr(obj, 'plugin', None)
    if not shortname:
        if 'NAGIOS_PLUGIN' in os.environ:
            shortname = os.environ['NAGIOS_PLUGIN']
        else:
            shortname = sys.argv[0]

    shortname = os.path.basename(shortname).upper()
    # Remove any leading CHECK_[BY_]
    shortname = re.sub(r'^CHECK_(?:BY_)?', '', shortname)
    # Remove any trailing suffix
    shortname = re.sub(r'\..*$', '', shortname)

    return shortname

#------------------------------------------------------------------------------
def max_state(*args):

    if nagios.state.critical in args:
        return nagios.state.critical
    if nagios.state.warning in args:
        return nagios.state.warning
    if nagios.state.ok in args:
        return nagios.state.ok
    if nagios.state.unknown in args:
        return nagios.state.unknown
    if nagios.state.dependend in args:
        return nagios.state.dependend

    return nagios.state.unknown

#------------------------------------------------------------------------------
def max_state_alt(*args):

    if nagios.state.critical in args:
        return nagios.state.critical
    if nagios.state.warning in args:
        return nagios.state.warning
    if nagios.state.unknown in args:
        return nagios.state.unknown
    if nagios.state.dependend in args:
        return nagios.state.dependend
    if nagios.state.ok in args:
        return nagios.state.ok

    return nagios.state.unknown

#------------------------------------------------------------------------------
def nagios_exit(code, message, plugin_object = None, no_status_line = False):

    # Handle string codes
    if code is not None and code in ERRORS:
        code = ERRORS[code]

    # Set defaults
    if not (code is not None and code in STATUS_TEXT):
        code = nagios.state.unknown
    if message is not None:
        if isinstance(message, list) or isinstance(message, tuple):
            message = ' '.join(lambda x: str(x).strip(), message)
        else:
            message = str(message).strip()

    # Setup output
    output = ''
    if no_status_line:
        if message is None:
            output = "[no message]"
        elif message:
            output = message
    else:
        output = STATUS_TEXT[code]
        if message:
            output += " - " + message
        shortname = None
        if plugin_object:
            shortname = getattr(plugin_object, 'shortname', None)
        # Should happen only if funnctions are called directly
        if not shortname:
            shortname = get_shortname()
        if shortname:
            output = shortname + " " + output
        if plugin_object:
            perfdata = getattr(plugin_object, 'perfdata', None)
            if perfdata and hasattr(plugin_object, 'all_perfoutput'):
                all_perfoutput = getattr(plugin_object, 'all_perfoutput')
                if callable(all_perfoutput):
                    output += ' | ' + all_perfoutput()

    if output:
        output += '\n'

    if _fake_exit:
        raise FakeExitError(code, output)

    return _nagios_exit(code, output)

#------------------------------------------------------------------------------
def _nagios_exit(code, output):

    if output:
        print output
    sys.exit(code)

#------------------------------------------------------------------------------
def nagios_die(message, plugin_object = None, no_status_line = False):

    return nagios_exit(nagios.state.unknown, message,
            plugin_object, no_status_line)

#------------------------------------------------------------------------------
def check_messages(critical, warning, ok = None, join = ' ', join_all = False):

    if join is None:
        join = ' '
    else:
        join = str(join)

    code = nagios.state.ok
    if len(warning):
        code = nagios.state.warning
    if len(critical):
        code = nagios.state.critical

    if not (isinstance(critical, list) or isinstance(critical, tuple)):
        critical = [critical]
    critical_msg = join.join(critical)
    if not (isinstance(warning, list) or isinstance(warning, tuple)):
        warning = [warning]
    warning_msg = join.join(warning)
    ok_msg = ''
    if ok:
        if not (isinstance(ok, list) or isinstance(ok, tuple)):
            ok = [ok]
        ok_msg = join.join(ok)

    message = ''
    if join_all:
        if not isinstance(join_all, basestring):
            join_all = ' :: '
        all_msgs = []
        all_msgs.append(critical_msg)
        all_msgs.append(warning_msg)
        if ok_msg:
            all_msgs.append(ok_msg)
        message = join_all.join(all_msgs)
    else:
        if code == nagios.state.critical:
            message = critical_msg
        elif code == nagios.state.warning:
            message = warning_msg
        else:
            message = ok_msg

    return (code, message)

#==============================================================================

if __name__ == "__main__":

    pass

#==============================================================================

# vim: fileencoding=utf-8 filetype=python ts=4
