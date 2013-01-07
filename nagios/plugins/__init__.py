#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
@author: Frank Brehm
@contact: frank.brehm@profitbricks.com
@copyright: © 2010 - 2013 by Frank Brehm, Berlin
@summary: Modules for extended NagiosPlugin classes
"""

# Standard modules
import os
import sys
import logging

# Third party modules

# Own modules

import nagios
from nagios import BaseNagiosError

from nagios.common import pp

from nagios.plugin import NagiosPluginError
from nagios.plugin import NagiosPlugin

#---------------------------------------------
# Some module variables

__version__ = '0.1.0'

log = logging.getLogger(__name__)

#==============================================================================
class ExtNagiosPluginError(NagiosPluginError):
    """Special exceptions, which are raised in this module."""

    pass



#==============================================================================

if __name__ == "__main__":

    pass

#==============================================================================

# vim: fileencoding=utf-8 filetype=python ts=4
