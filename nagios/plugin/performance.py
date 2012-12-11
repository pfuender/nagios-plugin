#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
@author: Frank Brehm
@contact: frank.brehm@profitbricks.com
@copyright: (c) 2010 - 2012 by Frank Brehm, Berlin
@summary: Module for a NagiosPerformance class
"""

# Standard modules
import os
import sys
import re
import logging
import numbers

from numbers import Number

# Third party modules

# Own modules

import nagios
from nagios import BaseNagiosError

from nagios.plugin.range import NagiosRangeError
from nagios.plugin.range import InvalidRangeError
from nagios.plugin.range import InvalidRangeValueError
from nagios.plugin.range import NagiosRange

from nagios.plugin.threshold import NagiosThreshold

#---------------------------------------------
# Some module variables

__version__ = '0.1.0'

log = logging.getLogger(__name__)

# Some regular expressions ...
re_ws = re.compile(r'\s')
re_not_word = re.compile(r'\W')
re_trailing_semicolons = re.compile(r';;$')
re_slash = re.compile(r'/')
re_leading_slash = re.compile(r'^/')

#==============================================================================
class NagiosPerformanceError(BaseNagiosError):
    """
    Base class for all exception classes and object, raised in this module.
    """

    pass

#==============================================================================
class NagiosPerformance(object):
    """
    A class for handling nagios.plugin performance data.
    """

    #--------------------------------------------------------------------------
    def __init__(self, label, value, uom = None, threshold = None,
            warning = None, critical = None, min_data = None, max_data = None):
        """
        Initialisation of the NagiosPerformance object.

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

        self._label = str(label).strip()
        """
        @ivar: the label of the performance data
        @type: str
        """
        if label is None or self._label == '':
            raise NagiosPerformanceError(("Empty label %r for " +
                    "NagiosPerformance given.") % (label))

        self._value = value
        """
        @ivar: the value of the performance data
        @type: Number
        """
        if not isinstance(value, Number):
            raise NagiosPerformanceError(("Wrong value %r for " +
                    "NagiosPerformance given.") % (value))

        self._uom = ''
        """
        @ivar: the unit of measure
        @type: str
        """
        if uom is not None:
            # remove all whitespaces
            self._uom = re_ws.sub('', str(uom))

        warn_range = NagiosRange()
        if warning:
            warn_range = NagiosRange(warning)

        crit_range = NagiosRange()
        if critical:
            crit_range = NagiosRange(critical)

        self._threshold = None
        """
        @ivar: the threshold object containing the warning and the
               critical threshold
        @type: NagiosThreshold
        """
        if isinstance(threshold, NagiosThreshold):
            self._threshold = threshold
        elif threshold is not None:
            raise NagiosPerformanceError(("The given threshold %r " +
                    "is neither None nor a NagiosThreshold object.") %
                    (threshold))
        else:
            self._threshold = NagiosThreshold(
                    warning = warn_range,
                    critical = crit_range
            )

        self._min_data = None
        """
        @ivar: the minimum data for performance output
        @type: Number or None
        """
        if min_data is not None:
            if not isinstance(min_data, Number):
                raise NagiosPerformanceError(("The given min_data %r " +
                        "is not None and not a Number.") % (min_data))
            else:
                self._min_data = min_data

        self._max_data = None
        """
        @ivar: the maximum data for performance output
        @type: Number or None
        """
        if max_data is not None:
            if not isinstance(max_data, Number):
                raise NagiosPerformanceError(("The given max_data %r " +
                        "is not None and not a Number.") % (max_data))
            else:
                self._max_data = max_data

    #------------------------------------------------------------
    @property
    def label(self):
        """The label of the performance data."""
        return self._label

    #------------------------------------------------------------
    @property
    def clean_label(self):
        """Returns a "clean" label for use as a dataset name in RRD, ie, it
        converts characters that are not [a-zA-Z0-9_] to _."""

        name = self.label
        if name == '/':
            name = "root"
        elif re_slash.search(name):
            name = re_leading_slash.sub('', name)
            name = re_slash.sub('_', name)

        name = re_not_word.sub('_', name)
        return name

    #------------------------------------------------------------
    @property
    def rrdlabel(self):
        """Returns a string based on 'label' that is suitable for use as
        dataset name of an RRD i.e. munges label to be 1-19 characters long
        with only characters [a-zA-Z0-9_]."""

        return self.clean_label[0:18]

    #------------------------------------------------------------
    @property
    def value(self):
        """The value of the performance data."""
        return self._value

    #------------------------------------------------------------
    @property
    def uom(self):
        """The unit of measure."""
        return self._uom

    #------------------------------------------------------------
    @property
    def threshold(self):
        """The threshold object containing the warning and the critical threshold."""
        return self._threshold

    #------------------------------------------------------------
    @property
    def warning(self):
        """The warning threshold for performance data."""
        if self._threshold.warning.is_set:
            return self._threshold.warning
        else:
            None

    #------------------------------------------------------------
    @property
    def critical(self):
        """The critical threshold for performance data."""
        if self._threshold.critical.is_set:
            return self._threshold.critical
        else:
            None

    #------------------------------------------------------------
    @property
    def min_data(self):
        """The minimum data for performance output."""
        return self._min_data

    #------------------------------------------------------------
    @property
    def max_data(self):
        """The maximum data for performance output."""
        return self._max_data

    #--------------------------------------------------------------------------
    def __repr__(self):
        """Typecasting into a string for reproduction."""

        out = ('<NagiosPerformance(label=%r, value=%r, uom=%r, threshold=%r, ' +
                'min_data=%r, max_data=%r)>' % (self.label, self.value, self.uom,
                self.threshold, self.min_data, self.max_data)

        return out

    #--------------------------------------------------------------------------
    def status(self):
        """
        Returns the Nagios state of the current value against the thresholds

        @return: nagios.state
        @rtype: int

        """

        return self.threshold.get_status([self.value])

    #--------------------------------------------------------------------------
    @staticmethod
    def _nvl(value):
        """Map None to ''."""

        if value is None:
            return ''
        return str(value)

    #--------------------------------------------------------------------------
    def perfoutput(self):
        """
        Outputs the data in NagiosPlugin perfdata format i.e.
        label=value[uom];[warn];[crit];[min];[max].

        """

        # Add quotes if label contains a space character
        label = self.label
        if re_ws.search(label):
            label = "'" + self.label + "'"

        out = "%s=%s%s;%s;%s;%s;%s" % (
                label,
                self.value,
                self._nvl(self.uom),
                self._nvl(self.warning.single_val()),
                self._nvl(self.critical.single_val()),
                self._nvl(self.min_data),
                self._nvl(self.max_data),
        )

        # omit trailing ;;
        out = re_trailing_semicolons.sub('', out)

        return out

#==============================================================================

if __name__ == "__main__":

    pass

#==============================================================================

# vim: fileencoding=utf-8 filetype=python ts=4
