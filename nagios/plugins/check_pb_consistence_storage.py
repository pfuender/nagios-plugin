#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
@author: Frank Brehm
@contact: frank.brehm@profitbricks.com
@copyright: © 2010 - 2015 by Frank Brehm, Berlin
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
import uuid
import math
import datetime

try:
    import configparser as cfgparser
except ImportError:
    import ConfigParser as cfgparser

# Third party modules

# Own modules

import nagios

from nagios.common import pp

from nagios.plugin.range import NagiosRange

from nagios.plugin.extended import ExtNagiosPluginError
from nagios.plugin.extended import CommandNotFoundError

from nagios.plugins.base_dcm_client_check import DEFAULT_TIMEOUT, DEFAULT_PB_VG
from nagios.plugins.base_dcm_client_check import STORAGE_CONFIG_DIR, DUMMY_LV, BACKUP_LV
from nagios.plugins.base_dcm_client_check import BaseDcmClientPlugin

from dcmanagerclient.client import RestApiError

# --------------------------------------------
# Some module variables

__version__ = '0.9.2'
__copyright__ = 'Copyright (c) 2015 Frank Brehm, Berlin.'

DEFAULT_WARN_VOL_ERRORS = 0
DEFAULT_CRIT_VOL_ERRORS = 2

# LVM_PATH = "/usr/sbin"
LVM_PATH = os.sep + os.path.join('usr', 'sbin')
# LVM_BIN_PATH = '/usr/sbin/lvm'
LVM_BIN_PATH = os.path.join(LVM_PATH, 'lvm')

log = logging.getLogger(__name__)


# =============================================================================
class CfgFileNotValidError(ExtNagiosPluginError):

    # -------------------------------------------------------------------------
    def __init__(self, cfg_file, msg):

        self.cfg_file = cfg_file
        self.msg = None
        if msg:
            m = str(msg).strip()
            if m:
                self.msg = m

    # -------------------------------------------------------------------------
    def __str__(self):

        msg = "Invalid configuration file %r" % (self.cfg_file)
        if self.msg:
            msg += ": %s" % (self.msg)
        msg += "."
        return msg


# =============================================================================
class CheckPbConsistenceStoragePlugin(BaseDcmClientPlugin):
    """
    A special Nagios/Icinga plugin to check the existent volumes on a storage
    server against the target state from provisioning database.
    The target volumes from database are get via REST API calls.
    """

    # -------------------------------------------------------------------------
    def __init__(self):
        """
        Constructor of the CheckPbConsistenceStoragePlugin class.
        """

        failed_commands = []

        usage = (
            "%(prog)s [options] [-H <server_name>] [-c <critical_volume_errors>]"
            " [-w <warning_volume_errors>]")
        usage += '\n       %(prog)s --usage'
        usage += '\n       %(prog)s --help'

        blurb = __copyright__ + "\n\n"
        blurb += (
            "Checks the existent volumes on a storage server against "
            "the target state from provisioning database.")

        self._hostname = socket.gethostname()
        """
        @ivar: the hostname of the current storage server
        @type: str
        """

        super(CheckPbConsistenceStoragePlugin, self).__init__(
            shortname='PB_CONSIST_STORAGE',
            usage=usage, blurb=blurb,
            timeout=DEFAULT_TIMEOUT,
        )

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
               before a critical result is given
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

    # -----------------------------------------------------------
    @property
    def hostname(self):
        """The hostname of the current storage server."""
        return self._hostname

    # -----------------------------------------------------------
    @property
    def pb_vg(self):
        """The name of the ProfitBricks storage volume group."""
        return self._pb_vg

    # -----------------------------------------------------------
    @property
    def warning(self):
        """The warning threshold of the test."""
        return self._warning

    # -----------------------------------------------------------
    @property
    def critical(self):
        """The critical threshold of the test."""
        return self._critical

    # -----------------------------------------------------------
    @property
    def lvm_command(self):
        """The 'lvm' command in operating system."""
        return self._lvm_command

    # -------------------------------------------------------------------------
    def as_dict(self):
        """
        Typecasting into a dictionary.

        @return: structure as dict
        @rtype:  dict

        """

        d = super(CheckPbConsistenceStoragePlugin, self).as_dict()

        d['hostname'] = self.hostname
        d['lvm_command'] = self.lvm_command
        d['pb_vg'] = self.pb_vg
        d['warning'] = self.warning
        d['critical'] = self.critical

        return d

    # -------------------------------------------------------------------------
    def add_args(self):
        """
        Adding all necessary arguments to the commandline argument parser.
        """

        msg_tpl = (
            "Generate %s state if the sum of missing, erroneous and "
            "orphaned volumes is higher (Default: %%(default)d).")

        msg = msg_tpl % ('warning')
        self.add_arg(
            '-w', '--warning',
            metavar='NUMBER',
            dest='warning',
            required=True,
            type=int,
            default=DEFAULT_WARN_VOL_ERRORS,
            help=msg,
        )

        msg = msg_tpl % ('critical')
        self.add_arg(
            '-c', '--critical',
            metavar='NUMBER',
            dest='critical',
            type=int,
            required=True,
            default=DEFAULT_CRIT_VOL_ERRORS,
            help=msg,
        )

        self.add_arg(
            '-H', '--hostname', '--host',
            metavar='NAME',
            dest='hostname',
            help=(
                "The hostname of the current storage server (Default: %r)." % (self.hostname)),
        )

        self.add_arg(
            '--vg', '--volume-group',
            metavar='VG',
            dest='pb_vg',
            help=(
                "The name of the ProfitBricks storage volume group (Default: %r)." % (
                    DEFAULT_PB_VG)),
        )

        super(CheckPbConsistenceStoragePlugin, self).add_args()

    # -------------------------------------------------------------------------
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
            warning=self.warning,
            critical=self.critical,
        )

    # -------------------------------------------------------------------------
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

    # -------------------------------------------------------------------------
    def run(self):
        """Main execution method."""

        state = nagios.state.ok
        out = "Storage volumes on %r seems to be okay." % (
            self.hostname)

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
            self.add_perfdata(label=key, value=self.count[key])

        if self.verbose > 1:
            log.debug("Got following counts:\n%s", pp(self.count))

        self.exit(state, out)

    # -------------------------------------------------------------------------
    def compare(self):

        for lv in self.lvm_lvs:

            if self.verbose > 3:
                log.debug("Checking LV %s/%s ...", lv['vgname'], lv['lvname'])
            self.count['total'] += 1

            # the Backup volume
            if lv['lvname'] == BACKUP_LV:
                self.count['dummy'] += 1
                log.debug("LV %s/%s is the backup volume.", lv['vgname'], lv['lvname'])
                continue

            # volume group not 'storage' or volume name not a shortened GUID
            if not lv['is_pb_vol']:
                self.count['alien'] += 1
                log.debug(
                    "LV %s/%s is not a valid Profitbricks volume.", lv['vgname'], lv['lvname'])
                continue

            # LVM snapshots don't count
            if lv['is_snapshot']:
                self.count['snapshots'] += 1
                log.debug(
                    "LV %s/%s is a valid Profitbricks LVM snapshot.", lv['vgname'], lv['lvname'])
                continue

            # open LVs with extension '-snap' also don't count
            if lv['has_snap_ext'] and lv['is_open']:
                self.count['snapshots'] += 1
                log.debug(
                    "LV %s/%s is an opened, valid splitted LVM snapshot.",
                    lv['vgname'], lv['lvname'])
                continue

            # our sealed bottled coffee volume
            if lv['lvname'] == DUMMY_LV:
                self.count['dummy'] += 1
                log.debug(
                    "LV %s/%s is the notorious dummy device.", lv['vgname'], lv['lvname'])
                continue

            guid = '600144f0-' + lv['lvname']
            if self.verbose > 3:
                log.debug("Searching for GUID %r ...", guid)

            if guid not in self.all_api_volumes:

                if lv['cfg_file_exists'] and lv['cfg_file_valid'] and lv['remove_timestamp']:
                    # Zombie == should be removed sometimes
                    self.count['zombies'] += 1
                    if self.verbose > 1:
                        ts = lv['remove_timestamp']
                        dd = datetime.datetime.fromtimestamp(ts)
                        log.debug(
                            "LV %s/%s has a remove timestamp of %d (%s)" % (
                                lv['vgname'], lv['lvname'], ts, dd))
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
                log.info(
                    "LV %s/%s has no config file %r.",
                    lv['vgname'], lv['lvname'], lv['cfg_file'])
                del self.all_api_volumes[guid]
                continue

            if lv['remove_timestamp']:
                prov_state = self.all_api_volumes[guid]['state']
                if prov_state and 'delete' in prov_state:
                    # Volume is on deletion
                    if self.verbose > 2:
                        log.debug(
                            "LV %s/%s will deleted sometimes.",
                            lv['vgname'], lv['lvname'])
                    self.count['zombies'] += 1
                    continue
                # Volume should be there, but remove date was set
                self.count['error'] += 1
                ts = lv['remove_timestamp']
                dd = datetime.datetime.fromtimestamp(ts)
                log.info(
                    "LV %s/%s is valid, but has a remove timestamp of %d (%s)",
                    lv['vgname'], lv['lvname'], ts, dd)
                del self.all_api_volumes[guid]
                continue

            cur_size = lv['total']
            target_size = self.all_api_volumes[guid]['size']
            if cur_size != target_size:
                # different sizes between database and current state
                self.count['error'] += 1
                log.info(
                    "LV %s/%s has a wrong size, current %d MiB, provisioned %d MiB.",
                    lv['vgname'], lv['lvname'], cur_size, target_size)
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
                        log.debug(
                            "%s %s is on deletion in database.", voltype, guid)
                    self.count['zombies'] += 1
                    continue

                if prov_state and 'to_be_created' in prov_state:
                    # Volume is on creation
                    if self.verbose > 2:
                        log.debug(
                            "%s %s is on creation in database.", voltype, guid)
                    self.count['ok'] += 1
                    continue

                # These volumes should be there
                log.info(
                    "%s %s with a size of %d MiB doesn't exists.", voltype,
                    guid, self.all_api_volumes[guid]['size'])
                self.count['missing'] += 1

    # -------------------------------------------------------------------------
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
            storages = self.api.vstorages(pstorage=self.hostname)
        except RestApiError as e:
            self.die(str(e))
        except Exception as e:
            self.die("%s: %s" % (e.__class__.__name__, e))

        first_volume = True
        for stor in storages:

            if self.verbose > 2 and (first_volume or self.verbose > 4):
                log.debug("Got Storage volume from API:\n%s", pp(stor))
            first_volume = False

            replicated = stor[key_replicated]
            size = stor[key_size]
            if replicated:
                size += 4

            state = None

            guid = None
            for replica in stor[key_replicas]:
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

    # -------------------------------------------------------------------------
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
            images = self.api.vimages(pstorage=self.hostname)
        except RestApiError as e:
            self.die(str(e))
        except Exception as e:
            self.die("%s: %s" % (e.__class__.__name__, e))

        first_volume = True
        for stor in images:

            if self.verbose > 2 and (first_volume or self.verbose > 4):
                log.debug("Got Image volume from API:\n%s", pp(stor))
            first_volume = False

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
            for replica in stor[key_replicas]:
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

    # -------------------------------------------------------------------------
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
            snapshots = self.api.vsnapshots(pstorage=self.hostname)
        except RestApiError as e:
            self.die(str(e))
        except Exception as e:
            self.die("%s: %s" % (e.__class__.__name__, e))

        first_volume = True
        for stor in snapshots:

            if self.verbose > 2 and (first_volume or self.verbose > 4):
                log.debug("Got Snapshot volume from API:\n%s", pp(stor))
            first_volume = False

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

    # -------------------------------------------------------------------------
    def get_lvm_lvs(self):

        self.lvm_lvs = []

        pat_pb_vol = (
            r'^(?:[\da-f]{4}-){3}[\da-f]{12}(-snap)?'
            r'(-del-\d{4}[-_]?\d{2}[-_]?\d{2}[-_]?\d{2}[-_:]?\d{2}(?:[-_:]?\d{2}))?$')
        if self.verbose > 3:
            log.debug("Regex for a PB Volume: %r", pat_pb_vol)
        re_pb_vol = re.compile(pat_pb_vol, re.IGNORECASE)

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
            (
                "lv_name,vg_name,stripes,stripesize,lv_attr,lv_uuid,devices,"
                "lv_path,vg_extent_size,lv_size,origin")
        ]

        (ret_code, std_out, std_err) = self.exec_cmd(cmd)
        if ret_code:
            msg = (
                "Error %d listing LVM logical volumes: %s" % (ret_code, std_err))
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
                log.debug(
                    "Got LV %s/%s, size %d MiB ...", lv['vgname'], lv['lvname'], lv['total'])

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
                lv['cfg_file'] = os.path.join(
                    STORAGE_CONFIG_DIR, (lv['lvname'] + '.ini'))
                if os.path.exists(lv['cfg_file']):
                    lv['cfg_file_exists'] = True
                    try:
                        lv['remove_timestamp'] = self.get_remove_timestamp(
                            lv['cfg_file'])
                        lv['cfg_file_valid'] = True
                    except CfgFileNotValidError as e:
                        log.debug("Error reading %r: %s", lv['cfg_file'], e)

            self.lvm_lvs.append(lv)

    # -------------------------------------------------------------------------
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

# =============================================================================

if __name__ == "__main__":

    pass

# =============================================================================

# vim: fileencoding=utf-8 filetype=python ts=4 et sw=4
