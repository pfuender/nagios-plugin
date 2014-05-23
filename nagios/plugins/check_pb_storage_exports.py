#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
@author: Frank Brehm
@contact: frank.brehm@profitbricks.com
@copyright: © 2010 - 2014 by Frank Brehm, Berlin
@summary: Module for CheckPbStorageExportsPlugin class for checking
          correctness of exported and/or not exported volumes
          on ProfitBricks storage servers
"""

# Standard modules
import os
import sys
import re
import logging
import socket
import textwrap
import time
import socket
import uuid
import math
import datetime


from numbers import Number

try:
    import configparser as cfgparser
except ImportError:
    import ConfigParser as cfgparser

# Third party modules

# Own modules

from pb_base.crc import crc64, crc64_digest

import nagios
from nagios import BaseNagiosError

from nagios.common import pp, caller_search_path

from nagios.plugin import NagiosPluginError

from nagios.plugin.range import NagiosRange

from nagios.plugin.threshold import NagiosThreshold

from nagios.plugin.extended import ExtNagiosPluginError
from nagios.plugin.extended import ExecutionTimeoutError
from nagios.plugin.extended import CommandNotFoundError

from nagios.plugin.config import NoConfigfileFound
from nagios.plugin.config import NagiosPluginConfig

from nagios.plugins.base_dcm_client_check import FunctionNotImplementedError
from nagios.plugins.base_dcm_client_check import DEFAULT_TIMEOUT
from nagios.plugins.base_dcm_client_check import STORAGE_CONFIG_DIR, DUMMY_LV
from nagios.plugins.base_dcm_client_check import BaseDcmClientPlugin

from dcmanagerclient.client import RestApiError

#---------------------------------------------
# Some module variables

__version__ = '0.2.0'
__copyright__ = 'Copyright (c) 2014 Frank Brehm, Berlin.'

DEFAULT_WARN_ERRORS = 0
DEFAULT_CRIT_ERRORS = 2

log = logging.getLogger(__name__)

#==============================================================================
class CheckPbStorageExportsPlugin(BaseDcmClientPlugin):
    """
    A special Nagios/Icinga plugin to check the correctness of exported
    and/or not exported volumes on ProfitBricks storage servers.
    The target volumes and mappings from database are get via REST API calls.
    """

    #--------------------------------------------------------------------------
    def __init__(self):
        """
        Constructor of the CheckPbStorageExportsPlugin class.
        """

        failed_commands = []

        usage = """\
                %(prog)s [options] [-H <server_name>] [-c <critical_errors>] [-w <warning_errors>]
                """
        usage = textwrap.dedent(usage).strip()
        usage += '\n       %(prog)s --usage'
        usage += '\n       %(prog)s --help'

        blurb = __copyright__ + "\n\n"
        blurb += ("Checks correctness of exported and/or not exported volumes " +
                    "on ProfitBricks storage servers.")

        self._hostname = socket.gethostname()
        """
        @ivar: the hostname of the current storage server
        @type: str
        """

        super(CheckPbStorageExportsPlugin, self).__init__(
                shortname = 'PB_STORAGE_EXPORTS',
                usage = usage, blurb = blurb,
                version = __version__, timeout = DEFAULT_TIMEOUT,
        )

        self._warning = NagiosRange(DEFAULT_WARN_ERRORS)
        """
        @ivar: the warning threshold of the test, max number of export errors,
               before a warning result is given
        @type: NagiosRange
        """

        self._critical = NagiosRange(DEFAULT_CRIT_ERRORS)
        """
        @ivar: the critical threshold of the test, max number of export errors,
               before a critical result is given
        @type: NagiosRange
        """

        self.all_api_exports = {}
        self.storage_exports = []
        self.image_exports = []
        self.count = {}

        # Some commands are missing
        if failed_commands:
            raise CommandNotFoundError(failed_commands)

    #------------------------------------------------------------
    @property
    def hostname(self):
        """The hostname of the current storage server."""
        return self._hostname

    #------------------------------------------------------------
    @property
    def warning(self):
        """The warning threshold of the test."""
        return self._warning

    #------------------------------------------------------------
    @property
    def critical(self):
        """The critical threshold of the test."""
        return self._critical

    #--------------------------------------------------------------------------
    def as_dict(self):
        """
        Typecasting into a dictionary.

        @return: structure as dict
        @rtype:  dict

        """

        d = super(CheckPbStorageExportsPlugin, self).as_dict()

        d['hostname'] = self.hostname
        d['warning'] = self.warning
        d['critical'] = self.critical

        return d

    #--------------------------------------------------------------------------
    def add_args(self):
        """
        Adding all necessary arguments to the commandline argument parser.
        """

        msg_tpl = ("Generate %s state if the sum of false or wrong exported " +
                "volumes is higher (Default: %%(default)d).")

        msg = msg_tpl % ('warning')
        self.add_arg(
                '-w', '--warning',
                metavar = 'NUMBER',
                dest = 'warning',
                required = True,
                type = int,
                default = DEFAULT_WARN_ERRORS,
                help = msg,
        )

        msg = msg_tpl % ('critical')
        self.add_arg(
                '-c', '--critical',
                metavar = 'NUMBER',
                dest = 'critical',
                type = int,
                required = True,
                default = DEFAULT_CRIT_ERRORS,
                help = msg,
        )

        self.add_arg(
                '-H', '--hostname', '--host',
                metavar = 'NAME',
                dest = 'hostname',
                help = (("The hostname of the current storage server " +
                        "(Default: %r).") % (self.hostname)),
        )

        super(CheckPbStorageExportsPlugin, self).add_args()

    #--------------------------------------------------------------------------
    def parse_args_second(self):
        """
        Evaluates comand line parameters after evaluating the configuration.
        """

        # define Hostname
        hn = self.argparser.args.hostname
        if hn:
            hn = hn.strip()
        if hn:
            self._hostname = hn.lower()

        # define warning level
        if self.argparser.args.warning is not None:
            self._warning = NagiosRange(self.argparser.args.warning)

        # define critical level
        if self.argparser.args.critical is not None:
            self._critical = NagiosRange(self.argparser.args.critical)

        # set thresholds
        self.set_thresholds(
                warning = self.warning,
                critical = self.critical,
        )

    #--------------------------------------------------------------------------
    def read_config(self, cfg):
        """
        Read configuration from an already read in configuration file.

        @param cfg: the already read in nagion configuration
        @type cfg: NagiosPluginConfig

        """

        if cfg.has_section('general'):
            hostname = None
            if cfg.has_option('general', 'hostname'):
                hostname = cfg.get('general', 'hostname')
            if hostname:
                hostname = hostname.strip()
            if hostname:
                if self.verbose > 1:
                    log.debug("Got a hostname from config: %r", hostname)
                self._hostname = hostname

            vg = None
            if cfg.has_option('general', 'volumegroup'):
                vg = cfg.get('general', 'volumegroup')
            if vg:
                vg = vg.strip()
            if vg:
                if self.verbose > 1:
                    log.debug("Got a volume group from config: %r", vg)
                self._pb_vg = vg

    #--------------------------------------------------------------------------
    def run(self):
        """Main execution method."""

        state = nagios.state.ok
        out = "Storage exports on %r seems to be okay." % (
                self.hostname)

        self.all_api_exports = {}

        self.count = {
                'total': 0,
                'missing': 0,
                'alien': 0,
                'orphans': 0,
                'zombies': 0,
                'snapshots': 0,
                'ok': 0,
                'dummy': 0,
                'error': 0,
        }

        self.get_api_storage_exports()

        self.exit(state, out)

    #--------------------------------------------------------------------------
    def get_api_storage_exports(self):

        self.storage_exports = []
        api_volumes = {}

        key_replicated = 'replicated'
        key_replicas = 'replicas'
        key_storage_server = 'storage_server'
        key_guid = 'guid'
        key_uuid = 'uuid'
        key_pstorage_name = 'pstorage_name'
        key_vstorage_uuid = 'vstorage_uuid'
        key_pserver_name = 'pserver_name'
        if sys.version_info[0] <= 2:
            key_replicated = key_replicated.decode('utf-8')
            key_replicas = key_replicas.decode('utf-8')
            key_storage_server = key_storage_server.decode('utf-8')
            key_guid = key_guid.decode('utf-8')
            key_uuid = key_uuid.decode('utf-8')
            key_pstorage_name = key_pstorage_name.decode('utf-8')
            key_vstorage_uuid = key_vstorage_uuid.decode('utf-8')
            key_pserver_name = key_pserver_name.decode('utf-8')

        log.debug("Retrieving storage volumes from API ...")
        storages = None
        try:
            storages = self.api.vstorages(pstorage = self.hostname)
        except RestApiError as e:
            self.die(str(e))
        except Exception as e:
            self.die("%s: %s" % (e.__class__.__name__, e))

        first = True
        for stor in storages:

            """
            {   'cloned_from': None,
                'cluster': 'de-ka-cluster-01',
                'contract': 31721232,
                'creation_date': '2014-05-21T04:10:38.399',
                'modification_date': '2014-05-21T04:15:35.620',
                'name': 'DWDCStorage_EMEA_D_Mirror',
                'os_type': None,
                'physical_server': 'pserver117',
                'region': 'europe',
                'replicas': [   {   'guid': '600144f0-0001-dc9b-0121-e09d11e3920c',
                                    'storage_server': 'storage201',
                                    'virtual_state': 'AVAILABLE'},
                                {   'guid': '600144f0-0001-dc98-6910-e09d11e3920c',
                                    'storage_server': 'storage103',
                                    'virtual_state': 'AVAILABLE'}],
                'replicated': True,
                'size': 716800,
                'uuid': 'e7abbe07-3d3e-4468-9af4-1bfe8af418dc',
                'virtual_network': '61ba3819-d719-4986-b59d-c6178a32aabe'}
            """

            vl = 4
            if first:
                vl = 2

            if self.verbose > vl:
                log.debug("Got Storage volume from API:\n%s", pp(stor))

            replicated = stor[key_replicated]
            vol_uuid = uuid.UUID(stor[key_uuid])

            guid = None
            for replica in  stor[key_replicas]:
                hn = replica[key_storage_server]
                if sys.version_info[0] <= 2:
                    hn = hn.encode('utf-8')
                if hn == self.hostname:
                    guid = uuid.UUID(replica[key_guid])
                    break

            if not guid:
                log.debug("No valid GUID found for storage volume:\n%s", pp(stor))
                continue

            vol = {
                'guid': guid,
                'replicated': replicated,
            }
            api_volumes[vol_uuid] = vol

            if self.verbose > vl:
                log.debug("Transformed Storage volume %r:\n%s", vol_uuid, pp(vol))

            if first:
                first = False


        log.debug("Retrieving storage mappings from API ...")
        maps = None
        try:
            maps = self.api.vstorage_maps(pstorage = self.hostname)
        except RestApiError as e:
            self.die(str(e))
        except Exception as e:
            self.die("%s: %s" % (e.__class__.__name__, e))

        first = True

        for mapping in maps:

            """
            {   'boot_order': 1,
                'creation_date': '2014-05-23T08:42:32.770',
                'dc_name': 'BKK Pfalz',
                'modification_date': '2014-05-23T08:42:32.770',
                'mount_state': 'AVAILABLE',
                'mount_type': 'VIRTIO',
                'mount_uuid': '8b30c7e8-f9fb-41b3-8b1d-723e1c41ee99',
                'network_uuid': '485abc1d-ec56-81d0-24cc-621cde8f34dc',
                'order_nr': 1,
                'pserver_name': 'pserver220',
                'pserver_uuid': '48385147-3600-0030-48FF-003048FF26B2',
                'pstorage_name': 'storage201',
                'pstorage_uuid': '49434D53-0200-9071-2500-71902500F26D',
                'replicated': True,
                'size_mb': 102400,
                'vm_name': 'replacement',
                'vm_uuid': '001f75f0-fa36-40cc-a628-060d2ecdccc1',
                'vstorage_guid': None,
                'vstorage_name': 'BKK Storage 2',
                'vstorage_uuid': '64f9dd3a-6db9-4405-a023-a0d32203c2aa'}
            """

            if mapping[key_pstorage_name] != self.hostname:
                continue
            if mapping[key_pserver_name] is None:
                continue

            vl = 4
            if first:
                vl = 2

            if self.verbose > vl:
                log.debug("Got Storage mapping from API:\n%s", pp(mapping))

            vol_uuid = uuid.UUID(mapping[key_vstorage_uuid])

            if not vol_uuid in api_volumes:
                log.error("No volume for mapping of %r found.", vol_uuid)
                continue

            guid = api_volumes[vol_uuid]['guid']
            scst_devname =  crc64_digest(str(guid))
            pserver = mapping[key_pserver_name]
            if sys.version_info[0] <= 2:
                pserver = pserver.decode('utf-8')

            m = {
                'uuid': vol_uuid,
                'guid': guid,
                'scst_devname': scst_devname,
                'replicated': api_volumes[vol_uuid]['replicated'],
                'pserver': pserver,
            }
            self.storage_exports.append(m)

            if self.verbose > vl:
                log.debug("Transformed storage mapping:\n%s",  pp(m))

            if first:
                first = False

        log.debug("Finished retrieving storage mappings from API, found %d mappings.",
                len(self.storage_exports))

#==============================================================================

if __name__ == "__main__":

    pass

#==============================================================================

# vim: fileencoding=utf-8 filetype=python ts=4 et sw=4
