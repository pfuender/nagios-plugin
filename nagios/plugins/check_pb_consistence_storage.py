#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
@author: Frank Brehm
@contact: frank.brehm@profitbricks.com
@copyright: © 2010 - 2014 by Frank Brehm, Berlin
@summary: Module for CheckPbConsistenceStoragePlugin class for checking
          consistence of storage volumes against the target state
          of the provisioning database
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

import nagios
from nagios import BaseNagiosError

from nagios.common import pp, caller_search_path

from nagios.plugin import NagiosPluginError

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

__version__ = '0.7.2'
__copyright__ = 'Copyright (c) 2014 Frank Brehm, Berlin.'

DEFAULT_TIMEOUT = 60
DEFAULT_API_URL = 'https://dcmanager.pb.local/dc/api'
DEFAULT_API_AUTHTOKEN = '604a3b5f6db67e5a3a48650313ddfb2e8bcf211b'
DEFAULT_PB_VG = 'storage'
STORAGE_CONFIG_DIR = os.sep + os.path.join('storage', 'config')
DUMMY_LV = 'ed00-0b07-71ed-000c0ffee000'

DEFAULT_WARN_VOL_ERRORS = 0
DEFAULT_CRIT_VOL_ERRORS = 2

#LVM_PATH = "/usr/sbin"
LVM_PATH = os.sep + os.path.join('usr', 'sbin')
# LVM_BIN_PATH = '/usr/sbin/lvm'
LVM_BIN_PATH = os.path.join(LVM_PATH, 'lvm')

log = logging.getLogger(__name__)

#==============================================================================
class CfgFileNotValidError(ExtNagiosPluginError):

    #--------------------------------------------------------------------------
    def __init__(self, cfg_file, msg):

        self.cfg_file = cfg_file
        self.msg = None
        if msg:
            m = str(msg).strip()
            if m:
                self.msg = m

    #--------------------------------------------------------------------------
    def __str__(self):

        msg = "Invalid configuration file %r" % (self.cfg_file)
        if self.msg:
            msg += ": %s" % (self.msg)
        msg += "."
        return msg

#==============================================================================
class CheckPbConsistenceStoragePlugin(ExtNagiosPlugin):
    """
    A special /Nagios/Icinga plugin to check the existent volumes on a storage
    server against the target state from provisioning database.
    The target volumes from database are get via REST API calls.
    """

    #--------------------------------------------------------------------------
    def __init__(self):
        """
        Constructor of the CheckPbConsistenceStoragePlugin class.
        """

        failed_commands = []

        usage = """\
                %(prog)s [options] [-H <server_name>] [-c <critical_volume_errors>] [-w <warning_volume_errors>]
                """
        usage = textwrap.dedent(usage).strip()
        usage += '\n       %(prog)s --usage'
        usage += '\n       %(prog)s --help'

        blurb = __copyright__ + "\n\n"
        blurb += ("Checks the existent volumes on a storage server against " +
                    "the target state from provisioning database.")

        super(CheckPbConsistenceStoragePlugin, self).__init__(
                shortname = 'PB_CONSIST_STORAGE',
                usage = usage, blurb = blurb,
                version = __version__, timeout = DEFAULT_TIMEOUT,
        )

        self._hostname = socket.gethostname()
        """
        @ivar: the hostname of the current storage server
        @type: str
        """

        self._api_url = None
        """
        @ivar: the URL of the Dc-Manager REST API
        @type: str
        """

        self._api_authtoken = None
        """
        @ivar: the authentication token for the DC-Manager REST API.
        @type: str
        """

        self.api = None
        """
        @ivar: an initialized REST API clinet object
        @type: RestApi
        """

        self._pb_vg = None
        """
        @ivar: the name of the ProfitBricks storage volume group
        """

        self._warning = NagiosRange(DEFAULT_WARN_VOL_ERRORS)
        """
        @ivar: the warning threshold of the test, max number of volume errors,
               before a warning result is given
        @type: NagiosRange
        """

        self._critical = NagiosRange(DEFAULT_CRIT_VOL_ERRORS)
        """
        @ivar: the critical threshold of the test, max number of volume errors,
               before a warning result is given
        @type: NagiosRange
        """

        # /sbin/lvm
        self._lvm_command = LVM_BIN_PATH
        """
        @ivar: the 'lvm' command in operating system
        @type: str
        """
        if not os.path.exists(self.lvm_command):
            self._lvm_command = self.get_command('lvm')
        if not os.path.exists(self.lvm_command):
            failed_commands.append('lvm')

        self.api_volumes = []
        self.api_images = []
        self.api_snapshots = []
        self.all_api_volumes = []
        self.lvm_lvs = []
        self.count = {}

        # Some commands are missing
        if failed_commands:
            raise CommandNotFoundError(failed_commands)

        self._add_args()

    #------------------------------------------------------------
    @property
    def hostname(self):
        """The hostname of the current storage server."""
        return self._hostname

    #------------------------------------------------------------
    @property
    def api_url(self):
        """The URL of the Dc-Manager REST API."""
        return self._api_url

    #------------------------------------------------------------
    @property
    def api_authtoken(self):
        """The authentication token for the DC-Manager REST API."""
        return self._api_authtoken

    #------------------------------------------------------------
    @property
    def pb_vg(self):
        """The name of the ProfitBricks storage volume group."""
        return self._pb_vg

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

    #------------------------------------------------------------
    @property
    def lvm_command(self):
        """The 'lvm' command in operating system."""
        return self._lvm_command

    #--------------------------------------------------------------------------
    def as_dict(self):
        """
        Typecasting into a dictionary.

        @return: structure as dict
        @rtype:  dict

        """

        d = super(CheckPbConsistenceStoragePlugin, self).as_dict()

        d['hostname'] = self.hostname
        d['lvm_command'] = self.lvm_command
        d['api_url'] = self.api_url
        d['api_authtoken'] = self.api_authtoken
        d['pb_vg'] = self.pb_vg
        d['warning'] = self.warning
        d['critical'] = self.critical
        d['api'] = None
        if self.api:
            d['api'] = self.api.__dict__

        return d

    #--------------------------------------------------------------------------
    def _add_args(self):
        """
        Adding all necessary arguments to the commandline argument parser.
        """

        msg_tpl = ("Generate %s state if the sum of missing, erroneous and " +
                "orphaned volumes is higher (Default: %%(default)d).")

        msg = msg_tpl % ('warning')
        self.add_arg(
                '-w', '--warning',
                metavar = 'NUMBER',
                dest = 'warning',
                required = True,
                type = int,
                default = DEFAULT_WARN_VOL_ERRORS,
                help = msg,
        )

        msg = msg_tpl % ('critical')
        self.add_arg(
                '-c', '--critical',
                metavar = 'NUMBER',
                dest = 'critical',
                type = int,
                required = True,
                default = DEFAULT_CRIT_VOL_ERRORS,
                help = msg,
        )

        self.add_arg(
                '-H', '--hostname', '--host',
                metavar = 'NAME',
                dest = 'hostname',
                help = (("The hostname of the current storage server " +
                        "(Default: %r).") % (self.hostname)),
        )

        self.add_arg(
                '--api-url',
                metavar = 'URL',
                dest = 'api_url',
                help = ("The URL of the Dc-Manager REST API (Default: %r)." % (
                        DEFAULT_API_URL)),
        )

        self.add_arg(
                '--api-authtoken',
                metavar = 'TOKEN',
                dest = 'api_authtoken',
                help = ("The authentication token of the Dc-Manager REST API."),
        )

        self.add_arg(
                '--vg', '--volume-group',
                metavar = 'VG',
                dest = 'pb_vg',
                help = ("The name of the ProfitBricks storage volume group (Default: %r)." % (
                        DEFAULT_PB_VG)),
        )

    #--------------------------------------------------------------------------
    def parse_args(self, args = None):
        """
        Executes self.argparser.parse_args().

        @param args: the argument strings to parse. If not given, they are
                     taken from sys.argv.
        @type args: list of str or None

        """

        super(CheckPbConsistenceStoragePlugin, self).parse_args(args)

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

        # define API URL
        if self.argparser.args.api_url:
            self._api_url = self.argparser.args.api_url

        if self.argparser.args.api_authtoken:
            self._api_authtoken = self.argparser.args.api_authtoken

        if not self.api_url:
            self._api_url = os.environ.get('RESTAPI_URL')
        if not self.api_url:
            self._api_url = DEFAULT_API_URL

        # define API authtoken
        if not self.api_authtoken:
            self._api_authtoken = os.environ.get('RESTAPI_AUTHTOKEN')
        if not self.api_authtoken:
            self._api_authtoken = DEFAULT_API_AUTHTOKEN

        # define storage volume group
        if self.argparser.args.pb_vg:
            self._pb_vg = self.argparser.args.pb_vg

        if not self.pb_vg:
            self._pb_vg = os.environ.get('LVM_VG_NAME')
        if not self.pb_vg:
            self._pb_vg = DEFAULT_PB_VG

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
    def read_config(self):
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

    #--------------------------------------------------------------------------
    def __call__(self):
        """
        Method to call the plugin directly.
        """

        self.parse_args()
        self.init_root_logger()

        self.read_config()

        self.parse_args_second()

        state = nagios.state.ok
        out = "Storage volumes on %r seems to be okay." % (
                self.hostname)

        self.api = RestApi(url = self.api_url, authtoken = self.api_authtoken)

        if self.verbose > 2:
            log.debug("Current object:\n%s", pp(self.as_dict()))

        self.all_api_volumes = {}

        self.get_api_storage_volumes()
        for vol in self.api_volumes:
            guid = str(vol['guid'])
            size = vol['size']
            self.all_api_volumes[guid] = {
                'size': size,
                'type': 'vol',
                'state': vol['state'],
            }
        self.api_volumes = None

        self.get_api_image_volumes()
        for vol in self.api_images:
            guid = str(vol['guid'])
            size = vol['size']
            self.all_api_volumes[guid] = {
                'size': size,
                'type': 'img',
                'state': vol['state'],
            }
        self.api_images = None

        self.get_api_snapshot_volumes()
        for vol in self.api_snapshots:
            guid = str(vol['guid'])
            size = vol['size']
            self.all_api_volumes[guid] = {
                'size': size,
                'type': 'snap',
                'state': vol['state'],
            }
        self.api_snapshots = None

        if self.verbose > 2:
            log.debug("All Volumes from API:\n%s", pp(self.all_api_volumes))

        self.get_lvm_lvs()
        if self.verbose > 3:
            log.debug("All Logical Volumes from LVM:\n%s", pp(self.lvm_lvs))

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

        self.compare()

        # Get current state and redefine output, if necessary
        total_errors = self.count['missing'] + self.count['orphans'] + self.count['error']
        state = self.threshold.get_status(total_errors)
        if total_errors == 1:
            out = "One error on provisioned storage volumes."
        elif total_errors > 1:
            out = "Currently %d errors on provisioned storage volumes." % (total_errors)

        # generate performance data (except number of dummy volumes)
        for key in self.count:
            if key == 'dummy':
                continue
            self.add_perfdata(label = key, value = self.count[key])

        if self.verbose > 1:
            log.debug("Got following counts:\n%s", pp(self.count))

        self.exit(state, out)

    #--------------------------------------------------------------------------
    def compare(self):

        for lv in self.lvm_lvs:

            if self.verbose > 3:
                log.debug("Checking LV %s/%s ...", lv['vgname'], lv['lvname'])
            self.count['total'] += 1

            # volume group not 'storage' or volume name not a shortened GUID
            if not lv['is_pb_vol']:
                self.count['alien'] += 1
                log.debug("LV %s/%s is not a valid Profitbricks volume.",
                        lv['vgname'], lv['lvname'])
                continue

            # LVM snapshots don't count
            if lv['is_snapshot']:
                self.count['snapshots'] += 1
                log.debug("LV %s/%s is a valid Profitbricks LVM snapshot.",
                        lv['vgname'], lv['lvname'])
                continue

            # open LVs with extension '-snap' also don't count
            if lv['has_snap_ext'] and lv['is_open']:
                self.count['snapshots'] += 1
                log.debug("LV %s/%s is an opened, valid splitted LVM snapshot.",
                        lv['vgname'], lv['lvname'])
                continue

            # our sealed bottled coffee volume
            if lv['lvname'] == DUMMY_LV:
                self.count['dummy'] += 1
                log.debug("LV %s/%s is the notorious dummy device.",
                        lv['vgname'], lv['lvname'])
                continue

            guid = '600144f0-' + lv['lvname']
            if self.verbose > 3:
                log.debug("Searching for GUID %r ...", guid)

            if not guid in self.all_api_volumes:

                if lv['cfg_file_exists'] and lv['cfg_file_valid'] and lv['remove_timestamp']:
                    # Zombie == should be removed sometimes
                    self.count['zombies'] += 1
                    if self.verbose > 1:
                        ts = lv['remove_timestamp']
                        dd = datetime.datetime.fromtimestamp(ts)
                        log.debug(("LV %s/%s has a remove timestamp " +
                                "of %d (%s)") % (lv['vgname'], lv['lvname'], ts, dd))
                else:

                    # Orphaned == existing, should not be removed, but not in DB
                    self.count['orphans'] += 1
                    msg = "LV %s/%s is orphaned: " % (lv['vgname'], lv['lvname'])
                    if not lv['cfg_file_exists']:
                        msg += "config file %r doesn't exists." % (lv['cfg_file'])
                    elif not lv['cfg_file_valid']:
                        msg += "config file %r is invalid." % (lv['cfg_file'])
                    else:
                        msg += "No remove timestamp defined in %r." % (lv['cfg_file'])
                    log.info(msg)
                continue

            if not lv['cfg_file_exists']:
                # No config file found == Error
                self.count['error'] += 1
                log.info("LV %s/%s has no config file %r.", lv['vgname'],
                        lv['lvname'], lv['cfg_file'])
                del self.all_api_volumes[guid]
                continue

            if lv['remove_timestamp']:
                prov_state = self.all_api_volumes[guid]['state']
                if prov_state and 'delete' in prov_state:
                    # Volume is on deletion
                    if self.verbose > 2:
                        log.debug("LV %s/%s will deleted sometimes.",
                                 lv['vgname'], lv['lvname'])
                    self.count['zombies'] += 1
                    continue
                # Volume should be there, but remove date was set
                self.count['error'] += 1
                ts = lv['remove_timestamp']
                dd = datetime.datetime.fromtimestamp(ts)
                log.info(("LV %s/%s is valid, but has a remove timestamp " +
                        "of %d (%s)"), lv['vgname'], lv['lvname'], ts, dd)
                del self.all_api_volumes[guid]
                continue

            cur_size = lv['total']
            target_size = self.all_api_volumes[guid]['size']
            if cur_size != target_size:
                # different sizes between database and current state
                self.count['error'] += 1
                log.info(("LV %s/%s has a wrong size, current %d MiB, " +
                        "provisioned %d MiB."), lv['vgname'], lv['lvname'],
                        cur_size, target_size)
                del self.all_api_volumes[guid]
                continue

            if self.verbose > 2:
                log.debug("LV %s/%s seems to be ok.", lv['vgname'], lv['lvname'])
            self.count['ok'] += 1
            del self.all_api_volumes[guid]

        # Checking for volumes, they are not in self.all_api_volumes
        if len(self.all_api_volumes.keys()):
            for guid in self.all_api_volumes:
                voltype = 'Volume'
                if self.all_api_volumes[guid]['type'] == 'img':
                    voltype = 'Image'
                elif self.all_api_volumes[guid]['type'] == 'snap':
                    voltype = 'Snapshot'

                prov_state = self.all_api_volumes[guid]['state']

                if prov_state and 'delete' in prov_state:
                    # Volume is on deletion
                    if self.verbose > 2:
                        log.debug("%s %s is on deletion in database.",
                                voltype, guid)
                    self.count['zombies'] += 1
                    continue

                if prov_state and 'to_be_created' in prov_state:
                    # Volume is on creation
                    if self.verbose > 2:
                        log.debug("%s %s is on creation in database.",
                                voltype, guid)
                    self.count['ok'] += 1
                    continue

                # These volumes should be there
                log.info("%s %s with a size of %d MiB doesn't exists.", voltype,
                    guid, self.all_api_volumes[guid]['size'])
                self.count['missing'] += 1

    #--------------------------------------------------------------------------
    def get_api_storage_volumes(self):

        self.api_volumes = []

        key_replicated = 'replicated'
        key_size = 'size'
        key_replicas = 'replicas'
        key_storage_server = 'storage_server'
        key_guid = 'guid'
        key_virtual_state = 'virtual_state'
        if sys.version_info[0] <= 2:
            key_replicated = key_replicated.decode('utf-8')
            key_size = key_size.decode('utf-8')
            key_replicas = key_replicas.decode('utf-8')
            key_storage_server = key_storage_server.decode('utf-8')
            key_guid = key_guid.decode('utf-8')
            key_virtual_state = key_virtual_state.decode('utf-8')

        storages = None
        try:
            storages = self.api.vstorages(pstorage = self.hostname)
        except RestApiError as e:
            self.die(str(e))
        except Exception as e:
            self.die("%s: %s" % (e.__class__.__name__, e))

        for stor in storages:

            if self.verbose > 4:
                log.debug("Got Storage volume from API:\n%s", pp(stor))

            replicated = stor[key_replicated]
            size = stor[key_size]
            if replicated:
                size += 4

            state = None

            guid = None
            for replica in  stor[key_replicas]:
                hn = replica[key_storage_server]
                if sys.version_info[0] <= 2:
                    hn = hn.encode('utf-8')
                if hn == self.hostname:
                    guid = uuid.UUID(replica[key_guid])
                    if key_virtual_state in replica:
                        state = replica[key_virtual_state]
                        if sys.version_info[0] <= 2:
                            state = state.encode('utf-8')
                    break

            if not guid:
                log.debug("No valid GUID found for storage volume:\n%s", pp(stor))
                continue

            if state:
                state = state.lower()

            vol = {
                'guid': guid,
                'replicated': replicated,
                'size': size,
                'state': state,
            }
            self.api_volumes.append(vol)

            if self.verbose > 5:
                log.debug("Transferred data of storage volume:\n%s", pp(vol))

        if self.verbose > 1:
            log.debug("Got %d Storage volumes from API.", len(self.api_volumes))
        if self.verbose > 3:
            log.debug("Got Storage volumes from API:\n%s", pp(self.api_volumes))

    #--------------------------------------------------------------------------
    def get_api_image_volumes(self):

        self.api_images = []

        key_replicated = 'replicate'
        key_size = 'size'
        key_replicas = 'replicas'
        key_storage_server = 'storage_server'
        key_guid = 'guid'
        key_image_type = 'image_type'
        key_virtual_state = 'virtual_state'
        if sys.version_info[0] <= 2:
            key_replicated = key_replicated.decode('utf-8')
            key_size = key_size.decode('utf-8')
            key_replicas = key_replicas.decode('utf-8')
            key_storage_server = key_storage_server.decode('utf-8')
            key_guid = key_guid.decode('utf-8')
            key_image_type = key_image_type.decode('utf-8')
            key_virtual_state = key_virtual_state.decode('utf-8')

        images = None
        try:
            images = self.api.vimages(pstorage = self.hostname)
        except RestApiError as e:
            self.die(str(e))
        except Exception as e:
            self.die("%s: %s" % (e.__class__.__name__, e))

        for stor in images:

            if self.verbose > 4:
                log.debug("Got Image volume from API:\n%s", pp(stor))

            state = None
            if key_virtual_state in stor:
                state = stor[key_virtual_state]
                if sys.version_info[0] <= 2:
                    state = state.encode('utf-8')

            replicated = False
            if stor[key_replicated]:
                replicated = True

            size = stor[key_size]
            size = int(math.ceil(float(size) / 4.0)) * 4
            if replicated:
                size += 4

            img_type = stor[key_image_type]
            if sys.version_info[0] <= 2:
                img_type = img_type.encode('utf-8')

            guid = None
            for replica in  stor[key_replicas]:
                hn = replica[key_storage_server]
                if sys.version_info[0] <= 2:
                    hn = hn.encode('utf-8')
                if hn == self.hostname:
                    guid = uuid.UUID(replica[key_guid])
                    if key_virtual_state in replica:
                        state = replica[key_virtual_state]
                        if sys.version_info[0] <= 2:
                            state = state.encode('utf-8')
                    break

            if not guid:
                log.debug("No valid GUID found for image:\n%s", pp(stor))
                continue

            if state:
                state = state.lower()

            vol = {
                'guid': guid,
                'replicated': replicated,
                'size': size,
                'img_type': img_type,
                'state': state,
            }
            self.api_images.append(vol)

            if self.verbose > 5:
                log.debug("Transferred data of image volume:\n%s", pp(vol))

        if self.verbose > 1:
            log.debug("Got %d Image volumes from API.", len(self.api_images))
        if self.verbose > 3:
            log.debug("Got Image volumes from API:\n%s", pp(self.api_images))

    #--------------------------------------------------------------------------
    def get_api_snapshot_volumes(self):

        self.api_snapshots = []

        key_replicated = 'replicate'
        key_size = 'size'
        key_replicas = 'replicas'
        key_storage_server = 'storage_server'
        key_guid = 'guid'
        key_image_type = 'image_type'
        key_virtual_state = 'virtual_state'
        if sys.version_info[0] <= 2:
            key_replicated = key_replicated.decode('utf-8')
            key_size = key_size.decode('utf-8')
            key_replicas = key_replicas.decode('utf-8')
            key_storage_server = key_storage_server.decode('utf-8')
            key_guid = key_guid.decode('utf-8')
            key_image_type = key_image_type.decode('utf-8')
            key_virtual_state = key_virtual_state.decode('utf-8')

        snapshots = None
        try:
            snapshots = self.api.vsnapshots(pstorage = self.hostname)
        except RestApiError as e:
            self.die(str(e))
        except Exception as e:
            self.die("%s: %s" % (e.__class__.__name__, e))

        for stor in snapshots:

            if self.verbose > 4:
                log.debug("Got Snapshot volume from API:\n%s", pp(stor))

            size = stor[key_size]
            guid = stor[key_guid]

            state = None
            if key_virtual_state in stor:
                state = stor[key_virtual_state]
                if sys.version_info[0] <= 2:
                    state = state.encode('utf-8')
            if state:
                state = state.lower()

            vol = {
                'guid': guid,
                'size': size,
                'state': state,
            }
            self.api_snapshots.append(vol)

            if self.verbose > 5:
                log.debug("Transferred data of storage volume:\n%s", pp(vol))


        if self.verbose > 1:
            log.debug("Got %d Snapshot volumes from API.", len(self.api_snapshots))
        if self.verbose > 3:
            log.debug("Got Snapshot volumes from API:\n%s", pp(self.api_snapshots))

    #--------------------------------------------------------------------------
    def get_lvm_lvs(self):

        self.lvm_lvs = []

        re_pb_vol = re.compile(r'^(?:[\da-f]{4}-){3}[\da-f]{12}(-snap)?$',
                re.IGNORECASE)

        cmd = [
                self.lvm_command,
                "lvs",
                "--nosuffix",
                "--noheadings",
                "--units",
                "b",
                "--separator",
                ";",
                "-o",
                "lv_name,vg_name,stripes,stripesize,lv_attr,lv_uuid,devices,lv_path,vg_extent_size,lv_size,origin"
            ]

        (ret_code, std_out, std_err) = self.exec_cmd(cmd)
        if ret_code:
            msg = (("Error %d listing LVM logical volumes: %s")
                    % (ret_code, std_err))
            self.die(msg)

        lines = std_out.split('\n')

        got_lvs = []

        for line in lines:
            line = line.strip()
            if line == '':
                continue
            if self.verbose > 4:
                log.debug("Checking line %r", line)

            words = line.split(";")

            lv = {}
            lv['lvname'] = words[0].strip()
            lv['vgname'] = words[1].strip()

            lv_name = "%s/%s" % (lv['vgname'], lv['lvname'])
            if lv_name in got_lvs:
                continue
            got_lvs.append(lv_name)

            lv['stripes'] = int(words[2])
            lv['stripesize'] = int(words[3])
            lv['attr'] = words[4].strip()
            lv['uuid'] = words[5].strip()
            lv['devices'] = words[6].strip()
            lv['path'] = words[7].strip()
            lv['extent_size'] = int(words[8])
            lv['total'] = int(words[9]) / 1024 / 1024

            if self.verbose > 3:
                log.debug("Got LV %s/%s, size %d MiB ...", lv['vgname'],
                         lv['lvname'], lv['total'])

            lv['origin'] = words[10].strip()
            if lv['origin'] == '':
                lv['origin'] = None
            lv['is_snapshot'] = False
            if lv['origin'] is not None:
                lv['is_snapshot'] = True
            lv['is_pb_vol'] = False
            lv['has_snap_ext'] = False
            lv['has_ini_file'] = False
            lv['delete_timestamp'] = None
            lv['cfg_file'] = None
            lv['cfg_file_exists'] = False
            lv['cfg_file_valid'] = False
            lv['remove_timestamp'] = None

            lv['is_open'] = False
            if lv['attr'][5] == 'o':
                lv['is_open'] = True

            if lv['vgname'] == self.pb_vg:
                match = re_pb_vol.search(lv['lvname'])
                if match:
                    lv['is_pb_vol'] = True
                    if match.group(1) is not None:
                        lv['has_snap_ext'] = True
            if lv['is_pb_vol'] and not lv['is_snapshot']:
                lv['cfg_file'] = os.path.join(STORAGE_CONFIG_DIR,
                        (lv['lvname'] + '.ini'))
                if os.path.exists(lv['cfg_file']):
                    lv['cfg_file_exists'] = True
                    try:
                        lv['remove_timestamp'] = self.get_remove_timestamp(
                                lv['cfg_file'])
                        lv['cfg_file_valid'] = True
                    except CfgFileNotValidError as e:
                        log.debug("Error reading %r: %s", lv['cfg_file'], e)

            self.lvm_lvs.append(lv)

    #--------------------------------------------------------------------------
    def get_remove_timestamp(self, cfg_file):


        cfg = cfgparser.ConfigParser()
        try:
            cfg.read(cfg_file)
        except Exception as e:
            msg = "%s: %s" % (e.__class__.__name__, e)
            raise CfgFileNotValidError(cfg_file, msg)

        if not cfg.has_section('Volume'):
            return None

        if not cfg.has_option('Volume', "remove_object"):
            return None

        timestamp = cfg.get('Volume', "remove_object")
        try:
            timestamp = int(timestamp)
        except Exception as e:
            msg = "%s: %s" % (e.__class__.__name__, e)
            raise CfgFileNotValidError(cfg_file, msg)

        return timestamp


#==============================================================================

if __name__ == "__main__":

    pass

#==============================================================================

# vim: fileencoding=utf-8 filetype=python ts=4 et sw=4
