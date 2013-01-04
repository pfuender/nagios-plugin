#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
@author: Frank Brehm
@contact: frank.brehm@profitbricks.com
@copyright: © 2010 - 2013 by Frank Brehm, Berlin
@summary: Module for a NagiosPluginConfig class
"""

# Standard modules
import os
import sys
import logging

import ConfigParser

from ConfigParser import ConfigParser

# Third party modules

# Own modules

import nagios
from nagios import BaseNagiosError

#---------------------------------------------
# Some module variables

__version__ = '0.2.2'

cfgfile_basenames = ('plugins.ini', 'nagios-plugins.ini')
nagios_cfgdirs = (
        '/etc/nagios',
        '/usr/local/nagios/etc',
        '/usr/local/etc/nagios',
        '/etc/opt/nagios',
)
general_cfgdirs = (
        '/etc',
        '/usr/local/etc',
        '/etc/opt',
)

log = logging.getLogger(__name__)

#==============================================================================
class NoConfigfileFound(BaseNagiosError):
    """
    Exception class indicating, that no config files are given and no
    config files on standard locations were found.
    """

    def __str__(self):
        """Typecasting into str with a default message."""

        return ("No configuration files given and no configuration files " +
                "found on standard locations.")

#==============================================================================
class NagiosPluginConfig(ConfigParser, object):
    """
    Subclass of ConfigParser with a changed read() method.
    """

    #--------------------------------------------------------------------------
    def read(self, filenames = None):
        """
        Overridden read method of ConfigParser class to search for default
        configuration files, if no filenames are given.
        """

        # transform filenames into a list, if a single string was given
        if isinstance(filenames, basestring):
            filenames = [filenames]
        elif filenames is None:
            filenames = []

        if not len(filenames):

            found = False

            if 'NAGIOS_CONFIG_PATH' in os.environ:
                paths = os.environ['NAGIOS_CONFIG_PATH']
                for path in paths.split(':'):
                    for bname in cfgfile_basenames:
                        fname = os.path.join(path, bname)
                        log.debug("Searching for config in %r ...", fname)
                        if os.path.isfile(fname):
                            filenames.insert(0, fname)
                            found = True
                        if found:
                            break
                    if found:
                        break

            if not found:
                for path in nagios_cfgdirs:
                    bname = cfgfile_basenames[0]
                    fname = os.path.join(path, bname)
                    log.debug("Searching for config in %r ...", fname)
                    if os.path.isfile(fname):
                        filenames.insert(0, fname)
                        found = True
                    if found:
                        break

            if not found:
                for path in general_cfgdirs:
                    bname = cfgfile_basenames[1]
                    fname = os.path.join(path, bname)
                    log.debug("Searching for config in %r ...", fname)
                    if os.path.isfile(fname):
                        filenames.insert(0, fname)
                        found = True
                    if found:
                        break

            if not found:
                raise NoConfigfileFound('')

        log.debug("Using config files: %r", filenames)
        # Note: ConfigParser is an old-style class!! super() doesn't work.
        return ConfigParser.read(self, filenames)

    #--------------------------------------------------------------------------
    def write(self, fileobject):
        """Wrapper to disallow write operations to configfile."""

        raise NotImplementedError("Write access not permitted.")

#==============================================================================

if __name__ == "__main__":

    pass

#==============================================================================

# vim: fileencoding=utf-8 filetype=python ts=4
