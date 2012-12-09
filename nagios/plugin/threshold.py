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

__version__ = '0.1.0'

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

    #------------------------------------------------------------
    @property
    def warning(self):
        """The warning threshold."""
        return self._warning

    #------------------------------------------------------------
    @property
    def critical(self):
        """The critical threshold."""
        return self._critical

    #--------------------------------------------------------------------------
    def get_status(self, values):
        """
        Checks the given values against the critical and the warning range.


        """

#==============================================================================

if __name__ == "__main__":

    pass

#==============================================================================

# vim: fileencoding=utf-8 filetype=python ts=4
