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
__version__ = '0.1.2'
__license__ = 'GPL3'

log = logging.getLogger(__name__)

#------------------------------------------------------------------------------
# Module variables

#==============================================================================

# Currently the only function
def pp(value):
    """
    Returns a pretty print string of the given value.

    @return: pretty print string
    @rtype: str
    """

    pretty_printer = pprint.PrettyPrinter(indent=4)
    return pretty_printer.pformat(value)

#==============================================================================
def caller_search_path(prepend = None, append = None):
    """
    Builds a search path for executables from environment $PATH
    including some standard paths.

    @param prepend: a list of search paths prepending to the result list
    @type prepend: list of str
    @param append: a list of search paths appending to the result list
    @type append: list of str

    @return: list of existing search paths
    @rtype: list

    """

    path_list = []
    search_path = os.environ['PATH']
    if not search_path:
        search_path = os.defpath

    search_path_list = []

    if prepend:
        for d in prepend:
            search_path_list.append(d)

    for d in search_path.split(os.pathsep):
        search_path_list.append(d)

    default_path = [
        '/bin',
        '/usr/bin',
        '/usr/local/bin',
        '/sbin',
        '/usr/sbin',
        '/usr/local/sbin',
        '/opt/bin',
        '/opt/icinga/bin',
        '/opt/nagios/bin',
        '/usr/local/icinga/bin',
        '/usr/local/nagios/bin',
    ]

    # A tribute to my current company 'ProfitBricks GmbH, Berlin, Germany'
    # Frank Brehm, August 2013
    default_path.append('/opt/profitbricks/bin')

    for d in default_path:
        search_path_list.append(d)

    if append:
        for d in append:
            search_path_list.append(d)

    for d in search_path_list:
        if not os.path.exists(d):
            continue
        if not os.path.isdir(d):
            continue
        d_abs = os.path.realpath(d)
        if not d_abs in path_list:
            path_list.append(d_abs)

    return path_list

#==============================================================================

if __name__ == "__main__":
    pass

#==============================================================================

# vim: tabstop=4 expandtab shiftwidth=4 softtabstop=4
