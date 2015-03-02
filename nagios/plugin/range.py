#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
@author: Frank Brehm
@contact: frank.brehm@profitbricks.com
@copyright: © 2010 - 2015 by Frank Brehm, Berlin
@summary: Module for a NagiosRange class
"""

# Standard modules
import re
import logging

from numbers import Number

# Third party modules

# Own modules

from nagios import BaseNagiosError

# --------------------------------------------
# Some module variables

__version__ = '0.2.3'

log = logging.getLogger(__name__)

match_num_val = r'[+-]?\d+(?:\.\d*)?'
match_range = r'^(\@)?(?:(' + match_num_val + r'|~)?:)?(' + match_num_val + r')?$'

re_ws = re.compile(r'\s+')
re_dot = re.compile(r'\.')
re_digit = re.compile(r'[\d~]')
re_range = re.compile(match_range)


# =============================================================================
class NagiosRangeError(BaseNagiosError):
    """Base exception class for all exceptions in this module."""
    pass


# =============================================================================
class InvalidRangeError(NagiosRangeError):
    """
    A special exception, which is raised, if an invalid range string was found.
    """

    # -------------------------------------------------------------------------
    def __init__(self, wrong_range):
        """
        Constructor.

        @param wrong_range: the wrong range, whiche lead to this exception.
        @type wrong_range: str

        """

        self.wrong_range = wrong_range

    # -------------------------------------------------------------------------
    def __str__(self):
        """Typecasting into a string for error output."""

        return "Wrong range %r." % (self.wrong_range)


# =============================================================================
class InvalidRangeValueError(NagiosRangeError):
    """
    A special exception, which is raised, if an invalid value should be checked
    against the current range object.
    """

    # -------------------------------------------------------------------------
    def __init__(self, value):
        """
        Constructor.

        @param value: the wrong value, whiche lead to this exception.
        @type value: object

        """

        self.value = value

    # -------------------------------------------------------------------------
    def __str__(self):
        """Typecasting into a string for error output."""

        return "Wrong value %r to check against a range." % (self.value)


# =============================================================================
class NagiosRange(object):
    """
    Encapsulation of a Nagios range, how used by some Nagios plugins.
    """

    # -------------------------------------------------------------------------
    def __init__(
        self, range_str=None, start=None, end=None,
            invert_match=False, initialized=None):
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
            self.parse_range_string(range_str)
            return

        if isinstance(start, int):
            self._start = int(start)
        elif isinstance(start, float):
            self._start = start
        elif start is not None:
            raise ValueError(
                "Start value %r for NagiosRange is unusable." % (start))

        if isinstance(end, int):
            self._end = int(end)
        elif isinstance(end, float):
            self._end = end
        elif end is not None:
            raise ValueError(
                "End value %r for NagiosRange is unusable." % (end))

        self._invert_match = bool(invert_match)

        if initialized is not None:
            self._initialized = bool(initialized)
        elif self.start is not None or self.end is not None:
            self._initialized = True

    # -----------------------------------------------------------
    @property
    def start(self):
        """The start value of the range, infinite, if None."""
        return self._start

    # -----------------------------------------------------------
    @property
    def end(self):
        """The end value of the range, infinite, if None."""
        return self._end

    # -----------------------------------------------------------
    @property
    def invert_match(self):
        """
        Invert check logic - if true, then the check results in true,
        if the value to check is outside the range, not inside
        """
        return self._invert_match

    # -----------------------------------------------------------
    @property
    def is_set(self):
        """The initialisation of this object is complete."""
        return self._initialized

    # -----------------------------------------------------------
    @property
    def initialized(self):
        """The initialisation of this object is complete."""
        return self._initialized

    # -------------------------------------------------------------------------
    def __str__(self):
        """Typecasting into a string."""

        if not self.initialized:
            return ''

        res = ''
        if self.invert_match:
            res = '@'

        if self.start is None:
            res += '~:'
        elif self.start != 0:
            res += str(self.start) + ':'

        if self.end is not None:
            res += str(self.end)

        return res

    # -------------------------------------------------------------------------
    def as_dict(self):
        """
        Typecasting into a dictionary.

        @return: structure as dict
        @rtype:  dict

        """

        d = {
            '__class__': self.__class__.__name__,
            'start': self.start,
            'end': self.end,
            'invert_match': self.invert_match,
            'initialized': self.initialized,
        }

        return d

    # -------------------------------------------------------------------------
    def __repr__(self):
        """Typecasting into a string for reproduction."""

        out = '<NagiosRange(start=%r, end=%r, invert_match=%r, initialized=%r)>' % (
            self.start, self.end, self.invert_match, self.initialized)

        return out

    # -------------------------------------------------------------------------
    def single_val(self):
        """
        Returns a single Number value.

        @return: self.end, if set, else self.start, if set, else None
        @rtype: Number or None

        """

        if not self.initialized:
            return None
        if self.end is not None:
            return self.end
        return self.start

    # -------------------------------------------------------------------------
    def parse_range_string(self, range_str):
        """
        Parsing the given range_str and set self.start, self.end and
        self.invert_match with the appropriate values.

        @raise InvalidRangeError: if the given range_str was invalid

        @param range_str: the range string of the type 'x:y' to use for
                          initialisation of the object
        @type range_str: str or Number

        """

        # range is a Number - all clear
        if isinstance(range_str, Number):
            self._start = 0
            self._end = range_str
            self._initialized = True
            return

        range_str = str(range_str)

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

        start_should_infinity = False

        if start is not None:
            if start == '~':
                start_should_infinity = True
                start = None
            else:
                if re_dot.search(start):
                    start = float(start)
                else:
                    start = int(start)
                valid = True

        if start is None:
            if start_should_infinity:
                log.debug("The start is None, but should be infinity.")
            else:
                log.debug("The start is None, but should be NOT infinity.")

        if end is not None:
            if re_dot.search(end):
                end = float(end)
            else:
                end = int(end)
            if start is None and not start_should_infinity:
                start = 0
            valid = True

        if not valid:
            raise InvalidRangeError(range_str)

        if start is not None and end is not None and start > end:
            raise InvalidRangeError(range_str)

        self._start = start
        self._end = end
        self._initialized = True

    # -------------------------------------------------------------------------
    def check_range(self, value):
        """Recverse method of self.check(), it inverts the result of check()
        to provide the exact same behaviour like the check_range() method
        of the Perl Nagios::Plugin::Range object."""

        if self.check(value):
            return False
        return True

    # -------------------------------------------------------------------------
    def __contains__(self, value):
        """
        Special method to implement the 'in' operator. With the help of this
        method it's possible to write such things like::

            my_range = NagiosRange(80)
            ....

            val = 5
            if val in my_range:
                print "Value %r is in range '%s'." % (val, my_range)
            else:
                print "Value %r is NOT in range '%s'." % (val, my_range)

        @param value: the value to check against the current range
        @type value: int or long or float

        """

        return self.check(value)

    # -------------------------------------------------------------------------
    def check(self, value):
        """
        Checks the given value against the current range.

        @raise NagiosRangeError: if the current range is not initialized
        @raise InvalidRangeValueError: if the given value is not a number

        @param value: the value to check against the current range
        @type value: int or long or float

        @return: the value is inside the range or not.
                 if self.invert_match is True, then this retur value is reverted
        @rtype: bool

        """

        if not self.initialized:
            raise NagiosRangeError(
                "The current NagiosRange object is not initialized.")

        if not isinstance(value, Number):
            raise InvalidRangeValueError(value)

        my_true = True
        my_false = False
        if self.invert_match:
            my_true = False
            my_false = True

        if self.start is not None and self.end is not None:
            if self.start <= value and value <= self.end:
                return my_true
            else:
                return my_false

        if self.start is not None and self.end is None:
            if value >= self.start:
                return my_true
            else:
                return my_false

        if self.start is None and self.end is not None:
            if value <= self.end:
                return my_true
            else:
                return my_false

        raise NagiosRangeError(
            "This point should never been reached in "
            "checking a value against a range.")

        return my_false

# =============================================================================

if __name__ == "__main__":

    pass

# =============================================================================

# vim: fileencoding=utf-8 filetype=python ts=4 et
