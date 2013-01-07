#!/usr/bin/env python
# -*- coding: utf-8 -*-
'''
@author: Frank Brehm
@contact: frank.brehm@profitbricks.com
@organization: Profitbricks GmbH
@copyright: (c) 2010-2012 by Profitbricks GmbH
@license: GPL3
@summary: module for some common used objects and routines
          for the nagion plugin module
'''

# Standard modules
import sys
import os
import logging
import pprint

__author__ = 'Frank Brehm <frank.brehm@profitbricks.com>'
__copyright__ = '(C) 2010-2013 by profitbricks.com'
__contact__ = 'frank.brehm@profitbricks.com'
__version__ = '0.1.0'
__license__ = 'GPL3'

log = logging.getLogger(__name__)

#------------------------------------------------------------------------------
# Module variables

#==============================================================================

# Currently the only function
def pp(value):
    '''
    Returns a pretty print string of the given value.

    @return: pretty print string
    @rtype: str
    '''

    pretty_printer = pprint.PrettyPrinter(indent=4)
    return pretty_printer.pformat(value)

#==============================================================================

if __name__ == "__main__":
    pass

#==============================================================================

# vim: tabstop=4 expandtab shiftwidth=4 softtabstop=4 nu
