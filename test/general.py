#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@author: Frank Brehm
@contact: frank.brehm@profitbricks.com
@organization: Profitbricks GmbH
@copyright: (c) 2010-2012 by Profitbricks GmbH
@license: GPL3
@summary: general used functions an objects used for unit tests on nagios
          plugin framework
"""

import unittest
import os
import sys
import logging
import tempfile
import copy
import pprint
import argparse

import nagios

#==============================================================================
# module variables and helper functions

COLOR_CODE = {
    'ENDC':              0,  # RESET COLOR
    'BOLD':              1,
    'UNDERLINE':         4,
    'BLINK':             5,
    'INVERT':            7,
    'CONCEALD':          8,
    'STRIKE':            9,
    'GREY30':           90,
    'GREY40':            2,
    'GREY65':           37,
    'GREY70':           97,
    'GREY20_BG':        40,
    'GREY33_BG':       100,
    'GREY80_BG':        47,
    'GREY93_BG':       107,
    'DARK_RED':         31,
    'RED':              91,
    'RED_BG':           41,
    'LIGHT_RED_BG':    101,
    'DARK_YELLOW':      33,
    'YELLOW':           93,
    'YELLOW_BG':        43,
    'LIGHT_YELLOW_BG': 103,
    'DARK_BLUE':        34,
    'BLUE':             94,
    'BLUE_BG':          44,
    'LIGHT_BLUE_BG':   104,
    'DARK_MAGENTA':     35,
    'PURPLE':           95,
    'MAGENTA_BG':       45,
    'LIGHT_PURPLE_BG': 105,
    'DARK_CYAN':        36,
    'AUQA':             96,
    'CYAN_BG':          46,
    'LIGHT_AUQA_BG':   106,
    'DARK_GREEN':       32,
    'GREEN':            92,
    'GREEN_BG':         42,
    'LIGHT_GREEN_BG':  102,
    'BLACK':            30,
}

#------------------------------------------------------------------------------
def termcode(num):

    return '\033[%sm' % (num)

#------------------------------------------------------------------------------
def colorstr(message, color):
    """
    Wrapper function to colorize the message.

    @param message: The message to colorize
    @type message: str
    @param color: The color to use, must be one of the keys of COLOR_CODE
    @type color: str

    @return: the colorized message
    @rtype: str

    """

    tcode = ''
    if isinstance(color, (list, tuple)):
        for c in color:
            tcode += termcode(COLOR_CODE[c])
    else:
        tcode = termcode(COLOR_CODE[color])

    return tcode + message + termcode(COLOR_CODE['ENDC'])

#==============================================================================

logger = logging.getLogger(__name__)

#==============================================================================
def pp(value):
    """
    Returns a pretty print string of the given value.

    @return: pretty print string
    @rtype: str
    """

    pretty_printer = pprint.PrettyPrinter(indent = 4)
    return pretty_printer.pformat(value)

#==============================================================================
def get_arg_verbose():

    arg_parser = argparse.ArgumentParser()

    arg_parser = argparse.ArgumentParser()
    arg_parser.add_argument("-v", "--verbose", action = "count",
            dest = 'verbose', help = 'Increase the verbosity level')
    args = arg_parser.parse_args()

    return args.verbose

#==============================================================================
def init_root_logger(verbose = 0):

    root_log = logging.getLogger()
    root_log.setLevel(logging.INFO)
    if verbose:
         root_log.setLevel(logging.DEBUG)

    appname = os.path.basename(sys.argv[0])
    format_str = appname + ': '
    if verbose:
        if verbose > 1:
            format_str += '%(name)s(%(lineno)d) %(funcName)s() '
        else:
            format_str += '%(name)s '
    format_str += '%(levelname)s - %(message)s'
    formatter = None
    formatter = ColoredFormatter(format_str)

    # create log handler for console output
    lh_console = logging.StreamHandler(sys.stderr)
    if verbose:
        lh_console.setLevel(logging.DEBUG)
    else:
        lh_console.setLevel(logging.INFO)
    lh_console.setFormatter(formatter)

    root_log.addHandler(lh_console)


#==============================================================================

class ColoredFormatter(logging.Formatter):
    # A variant of code found at:
    #  http://stackoverflow.com/questions/384076/how-can-i-make-the-python-logging-output-to-be-colored

    LEVEL_COLOR = {
        'DEBUG':    None,
        'INFO':     'GREEN',
        'WARNING':  'YELLOW',
        'ERROR':    ('BOLD', 'RED'),
        'CRITICAL': 'RED_BG',
    }

    #--------------------------------------------------------------------------
    def __init__(self, msg):

        logging.Formatter.__init__(self, msg)

    #------------------------------------------------------------
    @property
    def color_debug(self):
        """The color used to output debug messages."""
        return self.LEVEL_COLOR['DEBUG']

    @color_debug.setter
    def color_debug(self, value):
        self.LEVEL_COLOR['DEBUG'] = value

    #------------------------------------------------------------
    @property
    def color_info(self):
        """The color used to output info messages."""
        return self.LEVEL_COLOR['INFO']

    @color_info.setter
    def color_info(self, value):
        self.LEVEL_COLOR['INFO'] = value

    #------------------------------------------------------------
    @property
    def color_warning(self):
        """The color used to output warning messages."""
        return self.LEVEL_COLOR['WARNING']

    @color_warning.setter
    def color_warning(self, value):
        self.LEVEL_COLOR['WARNING'] = value

    #------------------------------------------------------------
    @property
    def color_error(self):
        """The color used to output error messages."""
        return self.LEVEL_COLOR['ERROR']

    @color_error.setter
    def color_error(self, value):
        self.LEVEL_COLOR['ERROR'] = value

    #------------------------------------------------------------
    @property
    def color_critical(self):
        """The color used to output critical messages."""
        return self.LEVEL_COLOR['CRITICAL']

    @color_critical.setter
    def color_critical(self, value):
        self.LEVEL_COLOR['CRITICAL'] = value

    #--------------------------------------------------------------------------
    def format(self, record):

        record = copy.copy(record)
        levelname = record.levelname

        if levelname in self.LEVEL_COLOR:

            record.name = colorstr(record.name, 'BOLD')
            record.filename = colorstr(record.filename, 'BOLD')
            record.module = colorstr(record.module, 'BOLD')
            record.funcName = colorstr(record.funcName, 'BOLD')
            record.pathname = colorstr(record.pathname, 'BOLD')
            record.processName = colorstr(record.processName, 'BOLD')
            record.threadName = colorstr(record.threadName, 'BOLD')

            if self.LEVEL_COLOR[levelname] is not None:
                record.levelname = colorstr(levelname, self.LEVEL_COLOR[levelname])
                record.msg = colorstr(record.msg, self.LEVEL_COLOR[levelname])

        return logging.Formatter.format(self, record)

#==============================================================================

if __name__ == '__main__':

    pass

#==============================================================================

# vim: tabstop=4 expandtab shiftwidth=4 softtabstop=4 nu
