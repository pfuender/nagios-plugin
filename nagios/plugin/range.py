#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
@author: Frank Brehm
@contact: frank.brehm@profitbricks.com
@copyright: (c) 2010 - 2012 by Frank Brehm, Berlin
@summary: Module for a NagiosPluginRange class
"""

# Standard modules
import os
import sys
import re

# Third party modules

# Own modules

import nagios
from nagios import BaseNagiosError, constant

#---------------------------------------------
# Some module variables

__version__ = '0.1.0'

#==============================================================================
class InvalidRangeError(BaseNagiosError):
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

if __name__ == "__main__":

    pass

#==============================================================================

# vim: fileencoding=utf-8 filetype=python ts=4
