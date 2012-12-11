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

#==============================================================================
class NagiosPerformance(object):
    """
    A class for handling nagios.plugin performance data.
    """

#==============================================================================

if __name__ == "__main__":

    pass

#==============================================================================

# vim: fileencoding=utf-8 filetype=python ts=4
