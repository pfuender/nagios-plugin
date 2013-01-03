#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
@author: Frank Brehm
@contact: frank.brehm@profitbricks.com
@copyright: (c) 2010 - 2012 by Frank Brehm, Berlin
@summary: Module for a NagiosThreshold class
"""

# Standard modules
import os
import sys
import re
import logging

# Third party modules

# Own modules

import nagios
from nagios import BaseNagiosError

from nagios.plugin.range import NagiosRangeError
from nagios.plugin.range import InvalidRangeError
from nagios.plugin.range import InvalidRangeValueError
from nagios.plugin.range import NagiosRange

#---------------------------------------------
# Some module variables

__version__ = '0.2.0'

log = logging.getLogger(__name__)

#==============================================================================
class NagiosThreshold(object):
    """
    Encapsulation of a Nagios threshold, how used by some Nagios plugins.
    """

    #--------------------------------------------------------------------------
    def __init__(self,
            warning = None,
            critical = None,
            ):
        """
        Initialisation of the NagiosThreshold object.

        @param warning: the warning threshold
        @type warning: str, int, long, float or NagiosRange
        @param critical: the critical threshold
        @type critical: str, int, long, float or NagiosRange

        """

        self._warning = NagiosRange()
        """
        @ivar: the warning threshold
        @type: NagiosRange
        """

        self._critical = NagiosRange()
        """
        @ivar: the critical threshold
        @type: NagiosRange
        """

        self.set_thresholds(
                warning = warning, critical = critical)

    #------------------------------------------------------------
    @property
    def warning(self):
        """The warning threshold."""
        return self._warning

    @warning.setter
    def warning(self, value):
        if value is None or (isinstance(value, basestring) and
                value == ''):
            self._warning = NagiosRange()
            return

        if isinstance(value, NagiosRange):
            self._warning = value
            return

        if isinstance(value, int) or isinstance(value, long):
            value = "%d" % (value)
        elif isinstance(value, float):
            value = "%f" % (value)

        self._warning = NagiosRange(value)

    #------------------------------------------------------------
    @property
    def critical(self):
        """The critical threshold."""
        return self._critical

    @critical.setter
    def critical(self, value):
        if value is None or (isinstance(value, basestring) and
                value == ''):
            self._critical = NagiosRange()
            return

        if isinstance(value, NagiosRange):
            self._critical = value
            return

        if isinstance(value, int) or isinstance(value, long):
            value = "%d" % (value)
        elif isinstance(value, float):
            value = "%f" % (value)

        self._critical = NagiosRange(value)

    #--------------------------------------------------------------------------
    def as_dict(self):
        """
        Typecasting into a dictionary.

        @return: structure as dict
        @rtype:  dict

        """

        d = {
                '__class__': self.__class__.__name__,
                'warning': None,
                'critical': None,
        }

        if self.warning:
            d['warning'] = self.warning.as_dict()

        if self.critical:
            d['critical'] = self.critical.as_dict()

        return d

    #--------------------------------------------------------------------------
    def __repr__(self):
        """Typecasting into a string for reproduction."""

        out = '<NagiosThreshold(warning=%r, critical=%r)>' % (
                self.warning, self.critical)

        return out

    #--------------------------------------------------------------------------
    def set_thresholds(self, warning = None, critical = None):
        """
        Re-Initialisation of the NagiosThreshold object.

        @param warning: the warning threshold
        @type warning: str, int, long, float or NagiosRange
        @param critical: the critical threshold
        @type critical: str, int, long, float or NagiosRange

        """

        self.warning = warning
        self.critical = critical

    #--------------------------------------------------------------------------
    def get_status(self, values):
        """
        Checks the given values against the critical and the warning range.

        @param values: a list with values to check against the critical
                       and warning range property
        @type values: int or long or float or list of them

        @return: a nagios state
        @rtype: int

        """

        if (isinstance(values, int) or isinstance(values, long) or
                isinstance(values, float)):
            values = [values]

        if self.critical.initialized:
            for value in values:
                if not value in self.critical:
                    return nagios.state.critical

        if self.warning.initialized:
            for value in values:
                if not value in self.warning:
                    return nagios.state.warning

        return nagios.state.ok

#==============================================================================

if __name__ == "__main__":

    pass

#==============================================================================

# vim: fileencoding=utf-8 filetype=python ts=4
