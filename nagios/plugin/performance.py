#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
@author: Frank Brehm
@contact: frank.brehm@profitbricks.com
@copyright: © 2010 - 2015 by Frank Brehm, Berlin
@summary: Module for a NagiosPerformance class
"""

# Standard modules
import re
import logging

from numbers import Number

# Third party modules

# Own modules

from nagios import BaseNagiosError

from nagios.plugin.range import NagiosRange

from nagios.plugin.threshold import NagiosThreshold

# --------------------------------------------
# Some module variables

__version__ = '0.1.1'

log = logging.getLogger(__name__)

# Some regular expressions ...
re_ws = re.compile(r'\s')
re_not_word = re.compile(r'\W')
re_trailing_semicolons = re.compile(r';;$')
re_slash = re.compile(r'/')
re_leading_slash = re.compile(r'^/')
re_comma = re.compile(r',')
re_dot = re.compile(r'\.')

pat_value = r'[-+]?[\d\.,]+'
pat_value_neg_inf = pat_value + r'|~'
"""pattern for a range with a negative infinity"""

pat_perfstring = r"^'?([^'=]+)'?=(" + pat_value + r')([\w%]*);?'
pat_perfstring += r'(' + pat_value_neg_inf + r'\:?' + pat_value + r'?)?;?'
pat_perfstring += r'(' + pat_value_neg_inf + r'\:?' + pat_value + r'?)?;?'
pat_perfstring += r'(' + pat_value + r'?)?;?'
pat_perfstring += r'(' + pat_value + r'?)?'

re_perfstring = re.compile(pat_perfstring)

re_perfoutput = re.compile(r'^(.*?=.*?)\s+')


# =============================================================================
class NagiosPerformanceError(BaseNagiosError):
    """
    Base class for all exception classes and object, raised in this module.
    """

    pass


# =============================================================================
class NagiosPerformance(object):
    """
    A class for handling nagios.plugin performance data.
    """

    # -------------------------------------------------------------------------
    def __init__(
        self, label, value, uom=None, threshold=None, warning=None, critical=None,
            min_data=None, max_data=None):
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
            raise NagiosPerformanceError(
                "Empty label %r for NagiosPerformance given." % (label))

        self._value = value
        """
        @ivar: the value of the performance data
        @type: Number
        """
        if not isinstance(value, Number):
            raise NagiosPerformanceError(
                "Wrong value %r for NagiosPerformance given." % (value))

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
            raise NagiosPerformanceError(
                "The given threshold %r is neither None nor a NagiosThreshold object." % (
                    threshold))
        else:
            self._threshold = NagiosThreshold(
                warning=warn_range,
                critical=crit_range
            )

        self._min_data = None
        """
        @ivar: the minimum data for performance output
        @type: Number or None
        """
        if min_data is not None:
            if not isinstance(min_data, Number):
                raise NagiosPerformanceError(
                    "The given min_data %r is not None and not a Number." % (min_data))
            else:
                self._min_data = min_data

        self._max_data = None
        """
        @ivar: the maximum data for performance output
        @type: Number or None
        """
        if max_data is not None:
            if not isinstance(max_data, Number):
                raise NagiosPerformanceError(
                    "The given max_data %r is not None and not a Number." % (max_data))
            else:
                self._max_data = max_data

    # -----------------------------------------------------------
    @property
    def label(self):
        """The label of the performance data."""
        return self._label

    # -----------------------------------------------------------
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

    # -----------------------------------------------------------
    @property
    def rrdlabel(self):
        """Returns a string based on 'label' that is suitable for use as
        dataset name of an RRD i.e. munges label to be 1-19 characters long
        with only characters [a-zA-Z0-9_]."""

        return self.clean_label[0:19]

    # -----------------------------------------------------------
    @property
    def value(self):
        """The value of the performance data."""
        return self._value

    # -----------------------------------------------------------
    @property
    def uom(self):
        """The unit of measure."""
        return self._uom

    # -----------------------------------------------------------
    @property
    def threshold(self):
        """The threshold object containing the warning and the critical threshold."""
        return self._threshold

    # -----------------------------------------------------------
    @property
    def warning(self):
        """The warning threshold for performance data."""
        return self._threshold.warning

    # -----------------------------------------------------------
    @property
    def critical(self):
        """The critical threshold for performance data."""
        return self._threshold.critical

    # -----------------------------------------------------------
    @property
    def min_data(self):
        """The minimum data for performance output."""
        return self._min_data

    # -----------------------------------------------------------
    @property
    def max_data(self):
        """The maximum data for performance output."""
        return self._max_data

    # -------------------------------------------------------------------------
    def __repr__(self):
        """Typecasting into a string for reproduction."""

        out = (
            '<NagiosPerformance(label=%r, value=%r, uom=%r, threshold=%r, '
            'min_data=%r, max_data=%r)>' % (
                self.label, self.value, self.uom, self.threshold, self.min_data, self.max_data))

        return out

    # -------------------------------------------------------------------------
    def as_dict(self):
        """
        Typecasting into a dictionary.

        @return: structure as dict
        @rtype:  dict

        """

        d = {
            '__class__': self.__class__.__name__,
            'label': self.label,
            'value': self.value,
            'uom': self.uom,
            'threshold': self.threshold.as_dict(),
            'min_data': self.min_data,
            'max_data': self.max_data,
            'status': self.status(),
        }

        return d

    # -------------------------------------------------------------------------
    def status(self):
        """
        Returns the Nagios state of the current value against the thresholds

        @return: nagios.state
        @rtype: int

        """

        return self.threshold.get_status([self.value])

    # -------------------------------------------------------------------------
    @staticmethod
    def _nvl(value):
        """Map None to ''."""

        if value is None:
            return ''
        return str(value)

    # -------------------------------------------------------------------------
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
            self._nvl(self.warning),
            self._nvl(self.critical),
            self._nvl(self.min_data),
            self._nvl(self.max_data),
        )

        # omit trailing ;;
        out = re_trailing_semicolons.sub('', out)

        return out

    # -------------------------------------------------------------------------
    @classmethod
    def _parse(cls, string):

        log.debug("Parsing string %r for performance data", string)
        match = re_perfstring.search(string)
        if not match:
            log.warn("String %r was not a valid performance output.", string)
            return None

        log.debug("Found parsed performance output: %r", match.groups())

        if match.group(1) is None or match.group(1) == '':
            log.warn(
                "String %r was not a valid performance output, no label found.", string)
            return None

        if match.group(2) is None or match.group(2) == '':
            log.warn(
                "String %r was not a valid performance output, no value found.", string)
            return None

        info = []
        i = 0
        for field in match.groups():
            val = None
            if i in (0, 2):
                val = field.strip()
            elif field is not None:
                val = re_comma.sub('.', field)
                try:
                    if re_dot.search(field):
                        val = float(field)
                    else:
                        val = int(field)
                except ValueError as e:
                    log.warn(
                        "Invalid performance value %r found: %s", field, str(e))
                    return None
            info.append(val)
            i += 1

        log.debug("Found parfdata fields: %r", info)

        obj = cls(
            label=info[0], value=info[1], uom=info[2], warning=info[3],
            critical=info[4], min_data=info[5], max_data=info[6])

        return obj

    # -------------------------------------------------------------------------
    @classmethod
    def parse_perfstring(cls, perfstring):
        """
        Parses the given string with performance output strings and gives
        back a list of NagiosPerformance objects from all successful parsed
        performance output strings.

        If there is an error parsing the string - which may consists of
        several sets of data -  will return a list with all the
        successfully parsed sets.

        If values are input with commas instead of periods, due to different
        locale settings, then it will still be parsed, but the commas will
        be converted to periods.

        @param perfstring: the string with performance output strings to parse
        @type perfstring: str

        @return: list of NagiosPerformance objects
        @rtype: list

        """

        ps = perfstring.strip()
        perfs = []

        while ps:

            obj = None
            ps = ps.strip()
            if ps == '':
                break

            if ps.count('=') > 1:

                # If there is more than 1 equals sign, split it out and
                # parse individually
                match = re_perfoutput.search(ps)
                if match:
                    obj = match.group(1)
                    ps = re_perfoutput.sub('', ps, 1)
                    obj = cls._parse(ps)
                else:
                    # This could occur if perfdata was soemthing=value=
                    log.warn("Didn't found performance data in %r.", ps)
                    break

            else:
                obj = cls._parse(ps)
                ps = ''

            if obj:
                perfs.append(obj)

        log.debug("Found performance data: %r", perfs)
        return perfs


# =============================================================================

if __name__ == "__main__":

    pass

# =============================================================================

# vim: fileencoding=utf-8 filetype=python ts=4 et
