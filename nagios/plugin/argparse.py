#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
@author: Frank Brehm
@contact: frank.brehm@profitbricks.com
@copyright: (c) 2010 - 2012 by Frank Brehm, Berlin
@summary: Module for a NagiosPluginArgparse class, a class providing a
          standardised argument processing for Nagios plugins
"""

# Standard modules
import os
import sys
import logging

import argparse

# Third party modules

# Own modules

import nagios
from nagios import BaseNagiosError

#---------------------------------------------
# Some module variables

__version__ = '0.1.0'

log = logging.getLogger(__name__)

#==============================================================================
class NagiosPluginArgparse(object):
    """
    A class providing a standardised argument processing for Nagios plugins.
    """

    pass

#==============================================================================

if __name__ == "__main__":

    pass

#==============================================================================

# vim: fileencoding=utf-8 filetype=python ts=4
