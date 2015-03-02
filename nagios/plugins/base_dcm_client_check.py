#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
@author: Frank Brehm
@contact: frank.brehm@profitbricks.com
@copyright: © 2010 - 2015 by Frank Brehm, Berlin
@summary: Module for BaseDcmClientPlugin class for a base class
          of DcManager-Client dependend plugin classes
"""

# Standard modules
import os
import sys
import logging

# Third party modules

# Own modules

import nagios

from nagios.common import pp

from nagios.plugin import NagiosPluginError

from nagios.plugin.argparser import lgpl3_licence_text, default_timeout

from nagios.plugin.extended import ExtNagiosPlugin

from nagios.plugin.config import NoConfigfileFound
from nagios.plugin.config import NagiosPluginConfig

from dcmanagerclient.client import DEFAULT_CFG_FILES, DEFAULT_API_URL
from dcmanagerclient.client import RestApi

# --------------------------------------------
# Some module variables

__version__ = '0.3.2'
__copyright__ = 'Copyright (c) 2015 Frank Brehm, Berlin.'

DEFAULT_TIMEOUT = 60
DEFAULT_PB_VG = 'storage'
STORAGE_CONFIG_DIR = os.sep + os.path.join('storage', 'config')
DUMMY_LV = 'ed00-0b07-71ed-000c0ffee000'
DUMMY_CRC = '4bf5f4063c838835'
BACKUP_LV = 'zzz_backup'

log = logging.getLogger(__name__)


# =============================================================================
class FunctionNotImplementedError(NagiosPluginError, NotImplementedError):
    """
    Error class for not implemented functions.
    """

    # -------------------------------------------------------------------------
    def __init__(self, function_name, class_name):
        """
        Constructor.

        @param function_name: the name of the not implemented function
        @type function_name: str
        @param class_name: the name of the class of the function
        @type class_name: str

        """

        self.function_name = function_name
        if not function_name:
            self.function_name = '__unkown_function__'

        self.class_name = class_name
        if not class_name:
            self.class_name = '__unkown_class__'

    # -------------------------------------------------------------------------
    def __str__(self):
        """
        Typecasting into a string for error output.
        """

        msg = "Function %(func)s() has to be overridden in class '%(cls)s'."
        return msg % {'func': self.function_name, 'cls': self.class_name}


# =============================================================================
class BaseDcmClientPlugin(ExtNagiosPlugin):
    """
    A base Nagios/Icinga plugin class for checks in conjunction
    with the DcManager-Client.
    """

    # -------------------------------------------------------------------------
    def __init__(
        self, usage=None, shortname=None, version=nagios.__version__, url=None,
            blurb=None, licence=lgpl3_licence_text, extra=None, plugin=None,
            timeout=default_timeout, verbose=0, prepend_searchpath=None,
            append_searchpath=None):
        """
        Constructor of the BaseDcmClientPlugin class.

        @param usage: Short usage message used with --usage/-? and with missing
                      required arguments, and included in the longer --help
                      output. Can include %(prog)s placeholder which will be
                      replaced with the plugin name, e.g.::

                          usage = 'Usage: %(prog)s -H <hostname> -p <ports> [-v]'

        @type usage: str
        @param shortname: the shortname of the plugin
        @type shortname: str
        @param version: Plugin version number, included in the --version/-V
                        output, and in the longer --help output. e.g.::

                            $ ./check_tcp_range --version
                            check_tcp_range 0.2 [http://www.openfusion.com.au/labs/nagios/]
        @type version: str
        @param url: URL for info about this plugin, included in the
                    --version/-V output, and in the longer --help output.
                    Maybe omitted.
        @type url: str or None
        @param blurb: Short plugin description, included in the longer
                      --help output. Maybe omitted.
        @type blurb: str or None
        @param licence: License text, included in the longer --help output. By
                        default, this is set to the standard nagios plugins
                        LGPLv3 licence text.
        @type licence: str or None
        @param extra: Extra text to be appended at the end of the longer --help
                      output, maybe omitted.
        @type extra: str or None
        @param plugin: Plugin name. This defaults to the basename of your plugin.
        @type plugin: str or None
        @param timeout: Timeout period in seconds, overriding the standard
                        timeout default (15 seconds).
        @type timeout: int
        @param verbose: verbosity level inside the module
        @type verbose: int
        @param prepend_searchpath: a single path or a list of paths to prepend
                                   to the search path list
        @type prepend_searchpath: str or list of str
        @param append_searchpath: a single path oor a list of paths to append
                                  to the search path list
        @type append_searchpath: str or list of str

        """

        super(BaseDcmClientPlugin, self).__init__(
            usage=usage,
            shortname=shortname,
            version=version,
            url=url,
            blurb=blurb,
            licence=licence,
            extra=extra,
            plugin=plugin,
            timeout=timeout,
            verbose=verbose,
            prepend_searchpath=prepend_searchpath,
            append_searchpath=append_searchpath,
        )

        self.api = None
        """
        @ivar: an initialized REST API client object
        @type: RestApi
        """

        self.add_args()

    # -------------------------------------------------------------------------
    def as_dict(self):
        """
        Typecasting into a dictionary.

        @return: structure as dict
        @rtype:  dict

        """

        d = super(BaseDcmClientPlugin, self).as_dict()

        d['api'] = None
        if self.api:
            d['api'] = self.api.__dict__

        return d

    # -------------------------------------------------------------------------
    def add_args(self):
        """
        Adding all necessary arguments to the commandline argument parser.
        """

        self.add_arg(
            '-E', '--extra-config-file', '--dcm-conf',
            dest='extra_config_file',
            metavar='FILE',
            help=(
                ("An extra configuration file, which overrides the settings from "
                    "the standard configuration files %r and from environment.") % (
                    DEFAULT_CFG_FILES,)),
        )

        self.add_arg(
            '--api-url',
            dest="api_url",
            metavar='URL',
            help=("The URL of the REST API (Default: %(default)r)." % {
                'default': DEFAULT_API_URL}),
        )

    # -------------------------------------------------------------------------
    def parse_args(self, args=None):
        """
        Executes self.argparser.parse_args().

        @param args: the argument strings to parse. If not given, they are
                     taken from sys.argv.
        @type args: list of str or None

        """

        super(BaseDcmClientPlugin, self).parse_args(args)

    # -------------------------------------------------------------------------
    def parse_args_second(self):
        """
        Dummy function to evaluate command line parameters after evaluating
        the configuration.

        Does nothing and CAN be overwritten by descendant classes.

        """

        return

    # -------------------------------------------------------------------------
    def _read_config(self):
        """
        Read configuration from an optional configuration file.
        """

        cfg = NagiosPluginConfig()
        try:
            configs = cfg.read()
            log.debug("Read configuration files:\n%s", pp(configs))
        except NoConfigfileFound as e:
            log.debug("Could not read NagiosPluginConfig: %s", e)
            return

        if self.verbose > 2:
            log.debug("Read configuration:\n%s", pp(cfg.__dict__))
        self.read_config(cfg)

    # -------------------------------------------------------------------------
    def read_config(self, cfg):
        """
        Read configuration from an already read in configuration file.

        @param cfg: the already read in nagion configuration
        @type cfg: NagiosPluginConfig

        This method may be overridden.
        """

        return

    # -------------------------------------------------------------------------
    def __call__(self):
        """
        Method to call the plugin directly.
        """

        try:

            self.parse_args()
            self.init_root_logger()

            self._read_config()
            self.parse_args_second()

            log.debug("Creating REST API client object ...")
            self.api = RestApi.from_config(
                extra_config_file=self.argparser.args.extra_config_file,
                api_url=self.argparser.args.api_url,
                timeout=self.timeout,
            )

            if self.verbose > 2:
                log.debug("Current object:\n%s", pp(self.as_dict()))

            self.pre_run()
            self.run()

        except Exception as e:
            state = nagios.state.unknown
            ename = e.__class__.__name__
            appname = os.path.basename(sys.argv[0])
            out = "%s on executing %r: %s" % (ename, appname,  e)
            if self.verbose:
                self.handle_error(str(e), ename, do_traceback=True)

            self.exit(state, out)

    # -------------------------------------------------------------------------
    def pre_run(self):
        """
        Dummy function to run before the main routine.
        Could be overwritten by descendant classes.

        """

        if self.verbose > 2:
            log.debug("executing pre_run() ...")

    # -------------------------------------------------------------------------
    def run(self):
        """
        Dummy function as main routine.

        MUST be overwritten by descendant classes.

        """

        raise FunctionNotImplementedError('_run()', self.__class__.__name__)


# =============================================================================

if __name__ == "__main__":

    pass

# =============================================================================

# vim: fileencoding=utf-8 filetype=python ts=4 et sw=4
