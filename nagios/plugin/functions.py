#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
@author: Frank Brehm
@contact: frank.brehm@profitbricks.com
@copyright: © 2010 - 2015 by Frank Brehm, Berlin
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
import collections

__version__ = '0.3.0'

# --------------------------------------------
# Some module variables

ERRORS = {
    'OK': nagios.state.ok,
    'WARNING': nagios.state.warning,
    'CRITICAL': nagios.state.critical,
    'UNKNOWN': nagios.state.unknown,
    'DEPENDENT': nagios.state.dependent,
}

STATUS_TEXT = {}
for key in list(ERRORS.keys()):
    val = ERRORS[key]
    STATUS_TEXT[val] = key

# _fake_exit flag and accessor/mutator, for testing
_fake_exit = False

# _use_die flag and accessor/mutator, so exceptions can be raised correctly
_use_die = False


# -----------------------------------------------------------------------------
def get_shortname(obj=None, plugin=None):

    shortname = None

    if hasattr(obj, 'shortname'):
        return getattr(obj, 'shortname')

    if plugin:
        shortname = plugin
    else:
        shortname = getattr(obj, 'plugin', None)
    if not shortname:
        if 'NAGIOS_PLUGIN' in os.environ:
            shortname = os.environ['NAGIOS_PLUGIN']
        else:
            shortname = sys.argv[0]

    shortname = os.path.basename(shortname).upper()
    # Remove any leading CHECK_[BY_]
    shortname = re.sub(r'^CHECK[-_](?:BY[-_])?', '', shortname)
    # Substitute dashes by underscores
    shortname = re.sub(r'-+', '_', shortname)
    # Remove any trailing suffix
    shortname = re.sub(r'\..*$', '', shortname)

    return shortname


# -----------------------------------------------------------------------------
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


# -----------------------------------------------------------------------------
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


# -----------------------------------------------------------------------------
def nagios_exit(code, message, plugin_object=None, no_status_line=False):

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
                if isinstance(all_perfoutput, collections.Callable):
                    output += ' | ' + all_perfoutput()

    if _fake_exit:
        raise FakeExitError(code, output)

    return _nagios_exit(code, output)


# -----------------------------------------------------------------------------
def _nagios_exit(code, output):

    if output:
        print(output)
    sys.exit(code)


# -----------------------------------------------------------------------------
def nagios_die(message, plugin_object=None, no_status_line=False):

    return nagios_exit(
        nagios.state.unknown, message, plugin_object, no_status_line)


# -----------------------------------------------------------------------------
def to_bool(value):
    """
    Converter from string to boolean values (e.g. from configurations)
    """

    if not value:
        return False

    if isinstance(value, bool):
        return value

    try:
        v_int = int(value)
    except ValueError:
        pass
    except TypeError:
        pass
    else:
        if v_int == 0:
            return False
        else:
            return True

    re_yes = re.compile(r'^\s*(?:y(?:es)?|true)\s*$', re.IGNORECASE)
    re_no = re.compile(r'^\s*(?:no?|false|off)\s*$', re.IGNORECASE)

    v_str = ''
    if isinstance(value, str):
        v_str = value
        if sys.version_info[0] <= 2:
            if isinstance(value, unicode):
                v_str = value.encode('utf-8')
    elif sys.version_info[0] > 2 and isinstance(value, bytes):
        v_str = value.decode('utf-8')
    else:
        v_str = str(value)

    if re_yes.search(v_str):
        return True
    if re_no.search(v_str):
        return False

    return bool(value)


# -----------------------------------------------------------------------------
def check_messages(critical, warning, ok=None, join=' ', join_all=False):
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
        if not isinstance(join_all, str):
            join_all = ' :: '
        all_msgs = []
        if critical_msg:
            all_msgs.append(critical_msg)
        if warning_msg:
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

# =============================================================================

if __name__ == "__main__":

    pass

# =============================================================================

# vim: fileencoding=utf-8 filetype=python ts=4 expandtab
