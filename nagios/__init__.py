#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
@author: Frank Brehm
@contact: frank.brehm@profitbricks.com
@copyright: (c) 2010 - 2012 by Frank Brehm, Berlin
@summary: Base modules for Nagios check plugins written in Python
"""

__author__ = 'Frank Brehm <frank.brehm@profitbricks.com>'
__copyright__ = '(C) 2010-2012 by profitbricks.com'
__contact__ = 'frank.brehm@profitbricks.com'
__version__ = '0.2.6-1'
__license__ = 'GPL3'

#==============================================================================

class BaseNagiosError(Exception):
    pass

#==============================================================================
class FakeExitError(BaseNagiosError):
    """
    Special exception class indicating a faked nagios_exit().

    It can be used in unit tests.

    """

    #--------------------------------------------------------------------------
    def __init__(self, exit_value, msg):
        """
        Constructor.

        @param exit_value: the exit value, which should be given back to OS.
        @type exit_value: int
        @param msg: the error message, which should be displayed on exit.
        @type msg: str

        """

        self.exit_value = int(exit_value)
        self.msg = str(msg)

    #--------------------------------------------------------------------------
    def __str__(self):
        """Typecasting into a string for error output."""

        return "Faked exit to OS. Exit value: %d, message: %r" % (
                self.exit_value, self.msg)

#==============================================================================

def constant(f):

    #------------------------------------------------------------
    def fset(self, value):
        raise SyntaxError('Constants may not changed.')

    #------------------------------------------------------------
    def fget(self):
        return f()

    #------------------------------------------------------------
    return property(fget, fset)

#==============================================================================

class _State(object):

    #------------------------------------------------------------
    @constant
    def ok():
        return 0

    #------------------------------------------------------------
    @constant
    def warning():
        return 1

    #------------------------------------------------------------
    @constant
    def critical():
        return 2

    #------------------------------------------------------------
    @constant
    def unknown():
        return 3

    #------------------------------------------------------------
    @constant
    def dependend():
        return 4

#==============================================================================

state = _State()

#==============================================================================

if __name__ == "__main__":

    pass

#==============================================================================

# vim: fileencoding=utf-8 filetype=python ts=4
