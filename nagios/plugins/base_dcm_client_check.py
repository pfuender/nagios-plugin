#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
@author: Frank Brehm
@contact: frank.brehm@profitbricks.com
@copyright: © 2010 - 2014 by Frank Brehm, Berlin
@summary: Module for BaseDcmClientPlugin class for a base class
          of DcManager-Client dependend plugin classes
"""

# Standard modules
import os
import sys
import re
import logging

try:
    from urllib.parse import urlparse
except ImportError:
    from urlparse import urlparse

try:
    import configparser as cfgparser
except ImportError:
    import ConfigParser as cfgparser


# Third party modules

# Own modules

import nagios
from nagios import BaseNagiosError

from nagios.common import pp, caller_search_path

from nagios.plugin import NagiosPluginError

from nagios.plugin.argparser import lgpl3_licence_text, default_timeout

from nagios.plugin.range import NagiosRange

from nagios.plugin.threshold import NagiosThreshold

from nagios.plugin.extended import ExtNagiosPluginError
from nagios.plugin.extended import ExecutionTimeoutError
from nagios.plugin.extended import CommandNotFoundError
from nagios.plugin.extended import ExtNagiosPlugin

from nagios.plugin.config import NoConfigfileFound
from nagios.plugin.config import NagiosPluginConfig

from dcmanagerclient.client import RestApi, RestApiError

#---------------------------------------------
# Some module variables

__version__ = '0.1.0'
__copyright__ = 'Copyright (c) 2014 Frank Brehm, Berlin.'

DEFAULT_API_URL = 'https://dcmanager.pb.local/api'
DEFAULT_API_TOKEN = ''

DEFAULT_CFG_FILES = (
    os.sep + os.path.join('etc', 'dcmanager.ini'),
    os.path.expanduser(os.path.join('~', '.dcmanager')),
)

log = logging.getLogger(__name__)

#==============================================================================
class FunctionNotImplementedError(NagiosPluginError, NotImplementedError):
    """
    Error class for not implemented functions.
    """

    #--------------------------------------------------------------------------
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

    #--------------------------------------------------------------------------
    def __str__(self):
        """
        Typecasting into a string for error output.
        """

        msg = "Function %(func)s() has to be overridden in class '%(cls)s'."
        return msg % {'func': self.function_name, 'cls': self.class_name}


#==============================================================================
class BaseDcmClientPlugin(ExtNagiosPlugin):
    """
    A base Nagios/Icinga plugin class for checks in conjunction
    with the DcManager-Client.
    """

    #--------------------------------------------------------------------------
    def __init__(self, usage = None, shortname = None,
            version = nagios.__version__, url = None, blurb = None,
            licence = lgpl3_licence_text, extra = None, plugin = None,
            timeout = default_timeout, verbose = 0, prepend_searchpath = None,
            append_searchpath = None, dcm_cfg_file = None):
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
        @param dcm_cfg_file: one or more additional configuration files
                             for the DcManage-Client
        @type dcm_cfg_file: str or list of str or None

        """

        super(BaseDcmClientPlugin, self).__init__(
                usage = usage,
                shortname = shortname,
                version = version,
                url = url,
                blurb = blurb,
                licence = licence,
                extra = extra,
                plugin = plugin,
                timeout = timeout,
                verbose = verbose,
                prepend_searchpath = prepend_searchpath,
                append_searchpath = append_searchpath,
        )

        def_api_url = os.environ.get('RESTAPI_URL') or DEFAULT_API_URL
        self._api_url =  urlparse(def_api_url)
        """
        @ivar: The URL of the REST API
        @type: urlparse.ParseResult
        """

        self._api_authtoken = os.environ.get('RESTAPI_AUTHTOKEN') or DEFAULT_API_TOKEN
        """
        @ivar: The authorization token for the REST API
        @type: str
        """

        self.api = None
        """
        @ivar: an initialized REST API clinet object
        @type: RestApi
        """

        self.dcm_cfg_files = []
        """
        @ivar: additional configuration files for the DcManage-Client
        @type: list of str
        """
        if isinstance(dcm_cfg_file, list) or isinstance(dcm_cfg_file, tuple):
            for cfile in dcm_cfg_file:
                self.dcm_cfg_files.append(str(cfile))
        elif dcm_cfg_file:
            self.dcm_cfg_files.append(str(dcm_cfg_file))

        self.extra_config_file = None
        """
        @ivar: an extra configuration file, given per commandline option,
               which overrides the api_url and api_authtoken for the standard
               configuration files and from environment
        @type: str
        """

        self.dcm_config_files = []
        """
        @ivar: a list with all evaluated DcManager config files
        @type: list of str
        """

        self.api = None
        """
        @ivar: a RestApi client object
        @type: RestApi
        """

    #------------------------------------------------------------
    @property
    def api_url(self):
        """The URL of the REST API."""
        return self._api_url

    @api_url.setter
    def api_url(self, value):
        self._api_url = urlparse(value)

    #------------------------------------------------------------
    @property
    def api_authtoken(self):
        """The authorization token for the REST API."""
        return self._api_authtoken

    @api_authtoken.setter
    def api_authtoken(self, value):
        self._api_authtoken = str(value).strip()

    #--------------------------------------------------------------------------
    def as_dict(self):
        """
        Typecasting into a dictionary.

        @return: structure as dict
        @rtype:  dict

        """

        d = super(BaseDcmClientPlugin, self).as_dict()

        d['api_url'] = self.api_url
        d['api_authtoken'] = self.api_authtoken
        d['api'] = None
        if self.api:
            d['api'] = self.api.__dict__

        return d

    #--------------------------------------------------------------------------
    def _add_args(self):
        """
        Adding all necessary arguments to the commandline argument parser.
        """

        self.add_arg(
                '-E', '--extra-config-file', '--dcm-conf',
                dest = 'extra_config_file',
                metavar = 'FILE',
                help = (("An extra configuration file, which overrides the " +
                        "settings from the standard configuration files %r and " +
                        "from environment.") % (DEFAULT_CFG_FILES,)),
        )

        self.add_arg(
                '--api-url',
                dest = "api_url",
                metavar = 'URL',
                help = ("The URL of the REST API (Default: %(default)r)." % {
                        'default': self.api_url.geturl()}),
        )



    #--------------------------------------------------------------------------
    def parse_args(self, args = None):
        """
        Executes self.argparser.parse_args().

        @param args: the argument strings to parse. If not given, they are
                     taken from sys.argv.
        @type args: list of str or None

        """

        super(BaseDcmClientPlugin, self).parse_args(args)

        if self.args.extra_config_file:
            self.extra_config_file = self.args.extra_config_file

        if self.args.api_url:
            self.api_url = self.args.api_url

    #--------------------------------------------------------------------------
    def parse_args_second(self):
        """
        Dummy function to evaluate command line parameters after evaluating
        the configuration.

        Does nothing and CAN be overwritten by descendant classes.

        """

        return

    #--------------------------------------------------------------------------
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

        if cfg.has_section('dcmanager_rest_api'):

            cfg_api_url = None
            if cfg.has_option('dcmanager_rest_api', 'url'):
                cfg_api_url = cfg.get('dcmanager_rest_api', 'url')
            if cfg_api_url:
                cfg_api_url = cfg_api_url.strip()
            if cfg_api_url:
                if self.verbose > 1:
                    log.debug("Got a REST API URL from config: %r", cfg_api_url)
                self._api_url = cfg_api_url

            cfg_api_authtoken = None
            if cfg.has_option('dcmanager_rest_api', 'authtoken'):
                cfg_api_authtoken = cfg.get('dcmanager_rest_api', 'authtoken')
            if cfg_api_authtoken:
                if self.verbose > 3:
                    log.debug("Got a REST API authentication token from config: %r",
                            cfg_api_authtoken)
                self._api_authtoken = cfg_api_authtoken

        self.read_config(cfg)

    #--------------------------------------------------------------------------
    def read_config(self, cfg):
        """
        Read configuration from an optional configuration file.

        This method may be overridden.
        """

        return

    #--------------------------------------------------------------------------
    def _read_default_dcm_cfg_files(self):
        """Reading in the default configuration files::
            * /etc/dcmanager.ini
            * ~/.dcmanager
        """

        for cfg_file in DEFAULT_CFG_FILES:
            if os.path.exists(cfg_file) and os.path.isfile(cfg_file):
                self.read_dcm_cfg_file(cfg_file)

        for cfg_file in self.dcm_cfg_files.reverse():
            if os.path.exists(cfg_file) and os.path.isfile(cfg_file):
                self.read_dcm_cfg_file(cfg_file)

    #--------------------------------------------------------------------------
    def _read_extra_dcm_cfg_file(self):

        if not self.extra_config_file:
            return

        if not os.path.exists(self.extra_config_file):
            msg = "Config file %r doesn't exists." % (self.extra_config_file)
            log.error(msg)
            sys.exit(1)

        if not os.path.isfile(self.extra_config_file):
            msg = "Config file %r is not a regular file." % (self.extra_config_file)
            log.error(msg)
            sys.exit(1)

        if not os.access(self.extra_config_file, os.R_OK):
            msg = "No read access for config file %r." % (self.extra_config_file)
            log.error(msg)
            sys.exit(1)

        log.debug("Reading extra DcManager configuration file %r ...",
                self.extra_config_file)
        self.read_dcm_cfg_file(self.extra_config_file)

    #--------------------------------------------------------------------------
    def _read_dcm_cfg_file(self, cfg_file):
        """
        The underlying method to read in the configuration file of
        the DcManager client.
        """

        if not os.path.exists(cfg_file):
            msg = "Config file %r doesn't exists." % (cfg_file)
            sys.stderr.write("%s\n" % (msg))
            return

        if not os.path.isfile(cfg_file):
            msg = "Config file %r is not a regular file." % (cfg_file)
            sys.stderr.write("%s\n" % (msg))
            return

        if not os.access(cfg_file, os.R_OK):
            msg = "No read access for config file %r." % (cfg_file)
            sys.stderr.write("%s\n" % (msg))
            return

        cfg = cfgparser.ConfigParser()
        cfg.read(cfg_file)

        for section in cfg.sections():

            if not section.lower() == "client":
                continue

            # [client]/url
            if cfg.has_option(section, 'url'):
                v = None
                try:
                    v = urlparse(cfg.get(section, 'url'))
                except (AttributeError, ValueError) as e:
                    msg = "Invalid value %r for [client]/url in %r." % (
                            cfg.get(section, 'url'), cfg_file)
                    sys.stderr.write("%s\n" % (msg))
                else:
                    if v.scheme:
                        self._api_url = v
                    else:
                        msg = "Invalid value %r for [client]/url in %r." % (
                                cfg.get(section, 'url'), cfg_file)
                        sys.stderr.write("%s\n" % (msg))

            # [client]/authtoken
            if cfg.has_option(section, 'authtoken'):
                self.api_authtoken = cfg.get(section, 'authtoken')

        self.dcm_config_files.insert(0, cfg_file)

    #--------------------------------------------------------------------------
    def __call__(self):
        """
        Method to call the plugin directly.
        """

        self.parse_args()
        self.init_root_logger()

        self._read_default_dcm_cfg_files()
        self._read_config()
        self.parse_args_second()
        self._read_extra_dcm_cfg_file()

        self.api = RestApi(
                url = self.api_url.geturl(),
                authtoken = self.api_authtoken,
                timeout = self.timeout,
        )

        if self.verbose > 2:
            log.debug("Current object:\n%s", pp(self.as_dict()))

        self.pre_run()
        self.run()

    #--------------------------------------------------------------------------
    def pre_run(self):
        """
        Dummy function to run before the main routine.
        Could be overwritten by descendant classes.

        """

        if self.verbose > 2:
            log.debug("executing pre_run() ...")

    #--------------------------------------------------------------------------
    def run(self):
        """
        Dummy function as main routine.

        MUST be overwritten by descendant classes.

        """

        raise FunctionNotImplementedError('_run()', self.__class__.__name__)


#==============================================================================

if __name__ == "__main__":

    pass

#==============================================================================

# vim: fileencoding=utf-8 filetype=python ts=4 et sw=4
