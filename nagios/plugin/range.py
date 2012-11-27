#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
@author: Frank Brehm
@contact: frank.brehm@profitbricks.com
@copyright: (c) 2010 - 2012 by Frank Brehm, Berlin
@summary: Module for a NagiosRange class
"""

# Standard modules
import os
import sys
import re
import logging

# Third party modules

# Own modules

import nagios
from nagios import BaseNagiosError, constant

#---------------------------------------------
# Some module variables

__version__ = '0.2.0'

log = logging.getLogger(__name__)

match_num_val = r'[+-]?\d+(?:\.\d*)'
match_range = r'^(\@)?(?:(' + match_num_val + r'|~):)?(' + match_num_val + r')?$'

re_ws = re.compile(r'\s+')
re_dot = re.compile(r'\.')
re_digit = re.compile(r'[\d~]')
re_range = re.compile(match_range)

#==============================================================================
class NagiosRangeError(BaseNagiosError):
    """Base exception class for all exceptions in this module."""
    pass

#==============================================================================
class InvalidRangeError(NagiosRangeError):
    """
    A special exception, which is raised, if an invaldid range string was found.
    """

    #--------------------------------------------------------------------------
    def __init__(self, wrong_range):
        """
        Constructor.

        @param wrong_range: the wrong range, whiche lead to this exception.
        @type wrong_range: str

        """

        self.wrong_range = wrong_range

    #--------------------------------------------------------------------------
    def __str__(self):
        """Typecasting into a string for error output."""

        return "Wrong range %r." % (self.wrong_range)

#==============================================================================
class NagiosRange(object):
    """
    Encapsulation of a Nagios range, how used by some Nagios plugins.
    """

    #--------------------------------------------------------------------------
    def __init__(self,
            range_str = None,
            start = None,
            end = None,
            invert_match = False,
            initialized = None
            ):
        """
        Initialisation of the NagiosRange object.

        @raise InvalidRangeError: if the given range_str was invalid
        @raise ValueError: on invalid start or end parameters, if
                           range_str was not given

        @param range_str: the range string of the type 'x:y' to use for
                          initialisation of the object, if given,
                          the parameters start, end and invert_match
                          are not considered
        @type range_str: str
        @param start: the start value of the range, infinite, if None
        @type start: long or int or float or None
        @param end: the end value of the range, infinite, if None
        @type end: long or int or float or None
        @param invert_match: invert check logic - if true, then the check
                             results in true, if the value to check is outside
                             the range, not inside
        @type invert_match: bool
        @param initialized: initialisation of this NagiosRange object is complete
        @type initialized: bool

        """

        self._start = None
        """
        @ivar: the start value of the range, infinite, if None
        @type: long or float or None
        """

        self._end = None
        """
        @ivar: the end value of the range, infinite, if None
        @type: long or float or None
        """

        self._invert_match = False
        """
        @ivar: invert check logic - if true, then the check results in true,
               if the value to check is outside the range, not inside
        @type: bool
        """

        self._initialized = False
        """
        @ivar: initialisation of this NagiosRange object is complete
        @type: bool
        """

        if range_str is not None:
            self.parse_range_string(str(range_str))
            return

        if isinstance(start, int) or isinstance(start, long):
            self._start = long(start)
        elif isinstance(start, float):
            self._start = start
        elif start is not None:
            raise ValueError("Start value %r for NagiosRange is unusable." %
                    (start))

        if isinstance(end, int) or isinstance(end, long):
            self._end = long(end)
        elif isinstance(end, float):
            self._end = end
        elif end is not None:
            raise ValueError("End value %r for NagiosRange is unusable." %
                    (end))

        self._invert_match = bool(invert_match)

        if initialized is not None:
            self._initialized = bool(initialized)
        elif self.start is not None or self.end is not None:
            self._initialized = True

    #------------------------------------------------------------
    @property
    def start(self):
        """The start value of the range, infinite, if None."""
        return self._start

    #------------------------------------------------------------
    @property
    def end(self):
        """The end value of the range, infinite, if None."""
        return self._end

    #------------------------------------------------------------
    @property
    def invert_match(self):
        """
        Invert check logic - if true, then the check results in true,
        if the value to check is outside the range, not inside
        """
        return self._invert_match

    #------------------------------------------------------------
    @property
    def initialized(self):
        """The initialisation of this object is complete."""
        return self._initialized

    #--------------------------------------------------------------------------
    def __str__(self):
        """Typecasting into a string."""

        if not self.initialized:
            return ''

        res = ''
        if self.invert_match:
            res = '@'

        if self.start is None:
            res += '~'
        else:
            res += str(self.start)

        res += ':'
        if self.end is not None:
            res += str(self.end)

        return res

    #--------------------------------------------------------------------------
    def __repr__(self):
        """Typecasting into a string for reproduction."""

        out = '<NagiosRange(start=%r, end=%r, invert_match=%r, initialized=%r>' % (
                self.start, self.end, self.invert_match, self.initialized)

        return out

    #--------------------------------------------------------------------------
    def parse_range_string(self, range_str):
        """
        Parsing the given range_str and set self.start, self.end and
        self.invert_match with the appropriate values.

        @raise InvalidRangeError: if the given range_str was invalid

        @param range_str: the range string of the type 'x:y' to use for
                          initialisation of the object
        @type range_str: str

        """

        # strip out any whitespace
        rstr = re_ws.sub('', range_str)
        log.debug("Parsing given range %r ...", rstr)

        self._start = None
        self._end = None
        self._initialized = False

        # check for valid range definition
        match = re_digit.search(rstr)
        if not match:
            raise InvalidRangeError(range_str)

        log.debug("Parsing range with regex %r ...", match_range)
        match = re_range.search(rstr)
        if not match:
            raise InvalidRangeError(range_str)

        log.debug("Found range parts: %r.", match.groups())
        invert = match.group(1)
        start = match.group(2)
        end = match.group(3)

        if invert is None:
            self._invert_match = False
        else:
            self._invert_match = True

        valid = False

        if start is not None and start != '~':
            if re_dot.search(start):
                start = float(start)
            else:
                start = long(start)
            valid = True
        else:
            start = None

        if end is not None:
            if re_dot.search(end):
                end = float(end)
            else:
                end = long(end)
            valid = True

        if not valid:
            raise InvalidRangeError(range_str)

        if start is not None and end is not None and start > end:
            raise InvalidRangeError(range_str)

        self._start = start
        self._end = end
        self._initialized = True

#==============================================================================

if __name__ == "__main__":

    pass

#==============================================================================

# vim: fileencoding=utf-8 filetype=python ts=4