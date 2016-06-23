#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
@author: Frank Brehm
@contact: frank.brehm@profitbricks.com
@copyright: © 2010 - 2015 by Frank Brehm, Berlin
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
import uuid
import glob

# Own modules
from pb_base.crc import crc64_digest

import nagios
from nagios.common import pp

from nagios.plugin.range import NagiosRange
from nagios.plugin.extended import CommandNotFoundError

from nagios.plugins.base_dcm_client_check import DEFAULT_TIMEOUT
from nagios.plugins.base_dcm_client_check import DUMMY_LV, DUMMY_CRC
from nagios.plugins.base_dcm_client_check import BaseDcmClientPlugin

from dcmanagerclient.client import RestApiError

# Some module variables
__version__ = '0.3.1'
__copyright__ = 'Copyright (c) 2015 Frank Brehm, Berlin.'

DEFAULT_WARN_ERRORS = 0
DEFAULT_CRIT_ERRORS = 2

SCST_BASE_DIR = os.sep + os.path.join('sys', 'kernel', 'scst_tgt')
SCST_DEV_DIR = os.path.join(SCST_BASE_DIR, 'devices')
SCST_TARGET_DIR = os.path.join(SCST_BASE_DIR, 'targets')
SCST_SRP_TARGET_DIR = os.path.join(SCST_TARGET_DIR, 'ib_srpt')
SCST_SRP_TARGET0_DIR = os.path.join(SCST_SRP_TARGET_DIR, 'ib_srpt_target_0')
SCST_INI_GROUP_DIR = os.path.join(SCST_SRP_TARGET0_DIR, 'ini_groups')
DEFAULT_STORAGE_VG = 'storage'

log = logging.getLogger(__name__)


class CheckPbStorageExportsPlugin(BaseDcmClientPlugin):
    """
    A special Nagios/Icinga plugin to check the correctness of exported
    and/or not exported volumes on ProfitBricks storage servers.
    The target volumes and mappings from database are get via REST API calls.
    """

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
        blurb += ("Checks correctness of exported and/or not exported volumes "
                  "on ProfitBricks storage servers.")

        self._hostname = socket.gethostname()
        """
        @ivar: the hostname of the current storage server
        @type: str
        """

        self._storage_vg = DEFAULT_STORAGE_VG
        self._may_have_rw_img_exports = False
        self._current_cluster = None

        super(CheckPbStorageExportsPlugin, self).__init__(
            shortname='PB_STORAGE_EXPORTS',
            usage=usage, blurb=blurb,
            timeout=DEFAULT_TIMEOUT,
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
        self.existing_exports = {}
        self.count = {}
        self.valid_pservers = {}

        # Some commands are missing
        if failed_commands:
            raise CommandNotFoundError(failed_commands)

    @property
    def hostname(self):
        """The hostname of the current storage server."""
        return self._hostname

    @property
    def warning(self):
        """The warning threshold of the test."""
        return self._warning

    @property
    def critical(self):
        """The critical threshold of the test."""
        return self._critical

    @property
    def storage_vg(self):
        """The storage volume group."""
        return self._storage_vg

    @property
    def current_cluster(self):
        """The cluster of the current storage server."""
        return self._current_cluster

    @property
    def may_have_rw_img_exports(self):
        """Flag indicating, that image volumes may read/write exported."""
        return self._may_have_rw_img_exports

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
        d['storage_vg'] = self.storage_vg
        d['may_have_rw_img_exports'] = self.may_have_rw_img_exports
        d['current_cluster'] = self.current_cluster

        return d

    def add_args(self):
        """
        Adding all necessary arguments to the commandline argument parser.
        """

        msg_tpl = ("Generate %s state if the sum of false or wrong exported "
                   "volumes is higher (Default: %%(default)d).")

        msg = msg_tpl % ('warning')
        self.add_arg(
            '-w', '--warning',
            metavar='NUMBER',
            dest='warning',
            required=True,
            type=int,
            default=DEFAULT_WARN_ERRORS,
            help=msg,
        )

        msg = msg_tpl % ('critical')
        self.add_arg(
            '-c', '--critical',
            metavar='NUMBER',
            dest='critical',
            type=int,
            required=True,
            default=DEFAULT_CRIT_ERRORS,
            help=msg,
        )

        self.add_arg(
            '-H', '--hostname', '--host',
            metavar='NAME',
            dest='hostname',
            help=(("The hostname of the current storage server " +
                   "(Default: %r).") % (self.hostname)),
        )

        self.add_arg(
            '--vg',
            metavar='VOLUME_GROUP',
            dest='storage_vg',
            default=self.storage_vg,
            help="The storage volume group (default %(default)r.",
        )

        self.add_arg(
            '--rw-image-exports',
            dest='may_have_rw_img_exports',
            action='store_true',
            help="May image volumes read/write exported?.",
        )

        super(CheckPbStorageExportsPlugin, self).add_args()

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
        if self.argparser.args.storage_vg:
            self._storage_vg = self.argparser.args.storage_vg

        may_have = getattr(self.argparser, 'may_have_rw_img_exports', False)
        if may_have:
            self._may_have_rw_img_exports = True
        # TODO: delete later
        self._may_have_rw_img_exports = True

        # define warning level
        if self.argparser.args.warning is not None:
            self._warning = NagiosRange(self.argparser.args.warning)

        # define critical level
        if self.argparser.args.critical is not None:
            self._critical = NagiosRange(self.argparser.args.critical)

        # set thresholds
        self.set_thresholds(warning=self.warning, critical=self.critical)

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

    def run(self):
        """Main execution method."""

        state = nagios.state.ok
        out = "Storage exports on %r seems to be okay." % (self.hostname)

        self.get_current_cluster()
        self.get_cluster_pservers()

        self.all_api_exports = {}
        self.existing_exports = {}

        self.count = {
            'exported_devs': 0,
            'exported_luns': 0,
            'missing': 0,
            'alien': 0,
            'ok': 0,
            'dummy': 0,
            'error': 0,
            'needless': 0,
        }

        self.get_api_storage_exports()
        self.get_api_image_exports()
        self.get_existing_exports()

        self.check_exports()
        self.check_ini_groups()

        log.debug("Results of check:\n%s", pp(self.count))

        total_errors = self.count['missing'] + self.count['error'] + self.count['needless']
        state = self.threshold.get_status(total_errors)
        if total_errors == 1:
            out = "There is one error on exported or not exported volumes."
        elif total_errors > 1:
            out = "There are %d errors on exported or not exported volumes." % (total_errors)

        # generate performance data (except number of dummy volumes)
        self.add_perfdata(label='total_errors', value=total_errors,
                          threshold=self.threshold)
        for key in self.count:
            if key == 'dummy':
                continue
            self.add_perfdata(label=key, value=self.count[key])

        self.exit(state, out)

    def get_current_cluster(self):

        try:
            storages = self.api.pstorages(name=self.hostname)
        except RestApiError as e:
            self.die(str(e))
        except Exception as e:
            self.die("%s: %s" % (e.__class__.__name__, e))

        log.debug("Info about current storage server from API:\n%s", pp(storages))

        if not len(storages):
            self.die("Could not find information about current storage server %r." %
                     (self.hostname))

        key_cluster = 'cluster'
        if sys.version_info[0] <= 2:
            key_cluster = key_cluster.decode('utf-8')
        cluster = storages[0][key_cluster]
        if sys.version_info[0] <= 2:
            cluster = cluster.encode('utf-8')
        log.debug("Cluster of current storage server %r: %r", self.hostname, cluster)
        self._current_cluster = cluster

    def get_cluster_pservers(self):

        if not self.current_cluster:
            self.die("No current cluster defined - cannot get pservers.")
            return

        self.valid_pservers = {}

        try:
            pservers = self.api.pservers(cluster=self.current_cluster)
        except RestApiError as e:
            self.die(str(e))
        except Exception as e:
            self.die("%s: %s" % (e.__class__.__name__, e))

        if self.verbose > 3:
            log.debug("Info about pservers in current cluster %r from API:\n%s",
                      self.current_cluster, pp(pservers))

        key_name = 'name'
        key_zone = 'zone'
        if sys.version_info[0] <= 2:
            key_name = key_name.decode('utf-8')
            key_zone = key_zone.decode('utf-8')

        for pserver in pservers:
            """
            {   u'alloc_cores': 22,
                u'alloc_ram': 50465865728,
                u'cluster': u'de-ka-cluster-01',
                u'cores_per_die': 8,
                u'cores_per_package': 16,
                u'dedication': None,
                u'ip': u'10.1.21.59',
                u'liveboot_version': u'liveboot-20131207-1344',
                u'name': u'pserver259',
                u'region': u'europe',
                u'total_cores': 62,
                u'total_ram': 257698037760,
                u'up': True,
                u'uuid': u'C0899115-C3C4-4A0B-9C26-2513CAEEC71C',
                u'vservers': 4,
                u'zone': 2},
            """

            pserver_name = pserver[key_name]
            if sys.version_info[0] <= 2:
                pserver_name = pserver_name.encode('utf-8')

            pserver_zone = pserver[key_zone]
            try:
                if pserver_zone:
                    pserver_zone = int(pserver_zone)
                else:
                    pserver_zone = 0
            except ValueError:
                pserver_zone = -1

            self.valid_pservers[pserver_name] = pserver_zone

        if self.verbose > 2:
            log.debug("Found Pservers in current cluster %r from API:\n%s",
                      self.current_cluster, pp(self.valid_pservers))

    def check_exports(self):

        for storage_export in self.storage_exports:
            self.check_storage_export(storage_export)
            if not storage_export['checked']:
                self.count['missing'] += 1
                log.info("Missing export of storage volume %s (%s) to %r.",
                         storage_export['guid'], storage_export['uuid'],
                         storage_export['pserver'])

        for image_export in self.image_exports:
            self.check_image_export(image_export)
            if not image_export['checked']:
                self.count['missing'] += 1
                log.info("Missing export of image volume %s (%s) to %r.",
                         image_export['guid'], image_export['uuid'],
                         image_export['pserver'])

        for devname in self.existing_exports:
            export = self.existing_exports[devname]
            if export['luns']:
                for ini_group in export['luns']:
                    if export['luns'][ini_group]['checked']:
                        self.count['ok'] += 1
                    else:
                        self.count['needless'] += 1
                        lun_id = export['luns'][ini_group]['id']
                        log.info("Needless export of %r (%s) to %r (LUN %s).",
                                 export['volume'], devname, ini_group, lun_id)
            else:
                log.info("Found SCST device %r (%s) without exported LUNs.",
                         devname, export['volume'])
                self.count['needless'] += 1

    def check_storage_export(self, storage_export):

        devname = storage_export['scst_devname']
        if devname in self.existing_exports:
            export = self.existing_exports[devname]
            uuid = storage_export['uuid']
            ini_group = storage_export['pserver']
            if ini_group in export['luns']:
                lun_id = export['luns'][ini_group]['id']
                export['luns'][ini_group]['checked'] = True
                storage_export['checked'] = True
                if export['read_only']:
                    self.count['error'] += 1
                    log.info("Export of storage volume %s (%s) must not be read_only.",
                             export['guid'], uuid)
                if self.verbose > 2:
                    log.debug("Found export for storage volume %s (%s) to %r (LUN %s).",
                              export['guid'], uuid, ini_group, lun_id)

    def check_image_export(self, image_export):

        devname = image_export['scst_devname']
        if devname in self.existing_exports:
            export = self.existing_exports[devname]
            uuid = image_export['uuid']
            ini_group = image_export['pserver']
            if ini_group in export['luns']:
                lun_id = export['luns'][ini_group]['id']
                export['luns'][ini_group]['checked'] = True
                image_export['checked'] = True
                if not export['read_only']:
                    if not self.may_have_rw_img_exports:
                        self.count['error'] += 1
                    log.info("Export of image volume %s (%s) must be read_only.",
                             export['guid'], uuid)
                if self.verbose > 2:
                    log.debug("Found export for image volume %s (%s) to %r (LUN %s).",
                              export['guid'], uuid, ini_group, lun_id)

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
            storages = self.api.vstorages(pstorage=self.hostname, contract_infos=False)
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
                'size': 716800,
                'uuid': 'e7abbe07-3d3e-4468-9af4-1bfe8af418dc',
                'virtual_network': '61ba3819-d719-4986-b59d-c6178a32aabe'}
            """

            vl = 4
            if first:
                vl = 2

            if self.verbose > vl:
                log.debug("Got Storage volume from API:\n%s", pp(stor))

            replicated = True
            if key_replicated in stor:
                replicated = stor[key_replicated]
            vol_uuid = uuid.UUID(stor[key_uuid])

            guid = None
            for replica in stor[key_replicas]:
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
            maps = self.api.vstorage_maps(pstorage=self.hostname)
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
                'size_mb': 102400,
                'vm_name': 'replacement',
                'vm_uuid': '001f75f0-fa36-40cc-a628-060d2ecdccc1',
                'vstorage_guid': None,
                'vstorage_name': 'BKK Storage 2',
                'vstorage_uuid': '64f9dd3a-6db9-4405-a023-a0d32203c2aa'}
            """

            if mapping[key_pstorage_name] != self.hostname:
                continue

            pserver = mapping[key_pserver_name]
            if pserver is None:
                continue
            if pserver not in self.valid_pservers:
                log.debug("Storage export to %r not considered.", pserver)
                continue

            vl = 4
            if first:
                vl = 2

            if self.verbose > vl:
                log.debug("Got Storage mapping from API:\n%s", pp(mapping))

            vol_uuid = uuid.UUID(mapping[key_vstorage_uuid])

            if vol_uuid not in api_volumes:
                log.error("No volume for mapping of %r found.", vol_uuid)
                continue

            guid = api_volumes[vol_uuid]['guid']
            scst_devname = crc64_digest(str(guid))
            if sys.version_info[0] <= 2:
                pserver = pserver.encode('utf-8')

            m = {
                'uuid': vol_uuid,
                'guid': guid,
                'scst_devname': scst_devname,
                'replicated': api_volumes[vol_uuid]['replicated'],
                'pserver': pserver,
                'checked': False,
            }
            self.storage_exports.append(m)

            if self.verbose > vl:
                log.debug("Transformed storage mapping:\n%s", pp(m))

            if first:
                first = False

        log.debug("Finished retrieving storage mappings from API, found %d mappings.",
                  len(self.storage_exports))

    def get_api_image_exports(self):

        self.image_exports = []
        api_volumes = {}

        key_replicated = 'replicate'
        key_replicas = 'replicas'
        key_storage_server = 'storage_server'
        key_guid = 'guid'
        key_uuid = 'uuid'
        key_pstorage_name = 'pstorage_name'
        key_vstorage_uuid = 'vstorage_uuid'
        key_image_uuid = 'image_uuid'
        key_pserver_name = 'pserver_name'
        if sys.version_info[0] <= 2:
            key_replicated = key_replicated.decode('utf-8')
            key_replicas = key_replicas.decode('utf-8')
            key_storage_server = key_storage_server.decode('utf-8')
            key_guid = key_guid.decode('utf-8')
            key_uuid = key_uuid.decode('utf-8')
            key_pstorage_name = key_pstorage_name.decode('utf-8')
            key_vstorage_uuid = key_vstorage_uuid.decode('utf-8')
            key_image_uuid = key_image_uuid.decode('utf-8')
            key_pserver_name = key_pserver_name.decode('utf-8')

        log.debug("Retrieving image volumes from API ...")
        images = None
        try:
            images = self.api.vimages(pstorage=self.hostname)
        except RestApiError as e:
            self.die(str(e))
        except Exception as e:
            self.die("%s: %s" % (e.__class__.__name__, e))

        first = True
        for img in images:

            """
            {   'absolute_path': 'ftp://getimgs:oahohthaeV5yuozahWos@imageserver/3111/iso-images/'
                                 'windows-VirtIO-driver-0.1.30.iso',
                'contract': 31720930,
                'creation_date': '2014-02-06T14:55:19.333',
                'image_type': 'CDROM',
                'modification_date': '2014-02-06T14:55:19.333',
                'replicas': [   {   'guid': '600144f0-0001-d843-4c30-8f3e11e3ae16',
                                    'storage_server': 'storage108',
                                    'virtual_state': 'AVAILABLE'},
                                {   'guid': '600144f0-0001-d843-4c31-8f3e11e3ae16',
                                    'storage_server': 'storage203',
                                    'virtual_state': 'AVAILABLE'}],
                'replicate': True,
                'size': 272,
                'uuid': 'b24d6e86-8f3e-11e3-b7e8-52540066fee9',
                'virtual_state': 'AVAILABLE'}
            """

            vl = 4
            if first:
                vl = 2

            if self.verbose > vl:
                log.debug("Got Image volume from API:\n%s", pp(img))

            replicated = bool(img[key_replicated])
            vol_uuid = uuid.UUID(img[key_uuid])

            guid = None
            for replica in img[key_replicas]:
                hn = replica[key_storage_server]
                if sys.version_info[0] <= 2:
                    hn = hn.encode('utf-8')
                if hn == self.hostname:
                    guid = uuid.UUID(replica[key_guid])
                    break

            if not guid:
                log.debug("No valid GUID found for image volume:\n%s", pp(img))
                continue

            vol = {
                'guid': guid,
                'replicated': replicated,
            }
            api_volumes[vol_uuid] = vol

            if self.verbose > vl:
                log.debug("Transformed Image volume %r:\n%s", vol_uuid, pp(vol))

            if first:
                first = False

        log.debug("Retrieving image mappings from API ...")
        maps = None
        try:
            maps = self.api.vimage_maps(pstorage=self.hostname)
        except RestApiError as e:
            self.die(str(e))
        except Exception as e:
            self.die("%s: %s" % (e.__class__.__name__, e))

        first = True

        for mapping in maps:

            """
            {   'boot_order': 1,
                'creation_date': '2014-03-03T09:23:35.748',
                'dc_name': 'ldcb.tjasys.net',
                'image_guid': '600144f0-0001-7e84-f65a-a2b511e3ad7d',
                'image_legalentity': 12508,
                'image_name': 'GSP1RMCPRXFREO_DE_DVD.ISO',
                'image_size': 3271557120,
                'image_type': 'CDROM',
                'image_uuid': 'ada919ce-a284-11e3-b5f6-52540066fee9',
                'modification_date': '2014-03-03T09:45:16.915',
                'mount_state': 'DEALLOCATED',
                'mount_type': 'IDE',
                'mount_uuid': '0b778d45-b5ac-4be8-bd89-3b4de4e13491',
                'network_uuid': '8ca30b27-9300-9b8e-dc84-f0349a0498de',
                'order_nr': 1,
                'pserver_name': None,
                'pserver_uuid': None,
                'pstorage_name': 'storage108',
                'pstorage_uuid': '00000000-0000-0000-0000-002590A93640',
                'replicated': True,
                'size_mb': 3120,
                'vm_name': 'Win7Test',
                'vm_uuid': 'c1b53ee7-66a7-4dc9-8240-e50432438582'}
            """

            if mapping[key_pstorage_name] != self.hostname:
                continue

            pserver = mapping[key_pserver_name]
            if pserver is None:
                continue
            if pserver not in self.valid_pservers:
                log.debug("Image export to %r not considered.", pserver)
                continue

            vl = 4
            if first:
                vl = 2

            if self.verbose > vl:
                log.debug("Got Image mapping from API:\n%s", pp(mapping))

            if first:
                first = False

            vol_uuid = uuid.UUID(mapping[key_image_uuid])

            if vol_uuid not in api_volumes:
                log.error("No volume for mapping of %r found.", vol_uuid)
                continue

            guid = api_volumes[vol_uuid]['guid']
            scst_devname = crc64_digest(str(guid))
            if sys.version_info[0] <= 2:
                pserver = pserver.encode('utf-8')

            m = {
                'uuid': vol_uuid,
                'guid': guid,
                'scst_devname': scst_devname,
                'replicated': api_volumes[vol_uuid]['replicated'],
                'pserver': pserver,
                'checked': False,
            }
            self.image_exports.append(m)

            if self.verbose > vl:
                log.debug("Transformed storage mapping:\n%s", pp(m))

        log.debug("Finished retrieving image mappings from API, found %d mappings.",
                  len(self.image_exports))

    def get_existing_exports(self):
        """ Result of descovering - dict of dicts in the form:
                {   'devicename': '5ce99e968d67ded2',
                    'guid': UUID('600144f0-0001-8aa6-91a2-19f911e39d8f'),
                    'has_errors': False,
                    'luns': {   'pserver123': '26'},
                    'read_only': False,
                    'volume': '/dev/storage/0001-8aa6-91a2-19f911e39d8f'}

            Keys of the upper dict are the SCST devicenames.

        """

        self.existing_exports = {}
        first = True

        pb_lv_pattern = (r'^' + os.sep + os.path.join('dev', self.storage_vg) +
                         os.sep + r'((?:[0-9a-f]{4}-){3}[0-9a-f]{12})$')
        if self.verbose > 2:
            log.debug("Search pattern for ProfiBricks volumes: %r", pb_lv_pattern)
        pb_lv = re.compile(pb_lv_pattern)

        pattern = os.path.join(SCST_DEV_DIR, '*')
        log.debug("Searching for SCST devices in %r ...", pattern)
        dev_dirs = glob.glob(pattern)
        for dev_dir in dev_dirs:

            vl = 4
            if first:
                vl = 2

            filename_file = os.path.join(dev_dir, 'filename')
            handler_link = os.path.join(dev_dir, 'handler')
            has_errors = False
            read_only = False

            if not os.path.exists(filename_file):
                continue
            if not os.path.exists(handler_link):
                continue

            self.count['exported_devs'] += 1

            exported_dir = os.path.join(dev_dir, 'exported')
            luns = {}
            if os.path.isdir(exported_dir):
                exports = glob.glob(os.path.join(exported_dir, '*'))
                nr_exports = 0
                for export_link in exports:
                    nr_exports += 1
                    exp_name = os.path.basename(export_link)
                    link_target = os.readlink(export_link)
                    if os.path.isabs(link_target):
                        lun_dir = os.path.realpath(lun_dir)
                    else:
                        lun_dir = os.path.realpath(os.path.relpath(link_target,
                                                                   os.path.dirname(export_link)))
                    ini_group = os.path.basename(os.path.dirname(os.path.dirname(lun_dir)))
                    lun_nr = os.path.basename(lun_dir)
                    luns[ini_group] = {'id': lun_nr, 'checked': False}
                    self.count['exported_luns'] += 1

                # if nr_exports > 1:
                #    vl = 2

            devname = os.path.basename(dev_dir)
            export_filename = self.get_scst_export_filename(filename_file)
            if not export_filename:
                log.info("No devicename found for export %r.", devname)
                self.count['error'] += 1
                continue

            match = pb_lv.search(export_filename)
            if not match:
                if self.verbose > 2:
                    log.debug("Export %r for device %r is not a regular ProfitBricks volume.",
                              devname, export_filename)
                self.count['alien'] += 1
                continue
            short_guid = match.group(1)
            if short_guid == DUMMY_LV and devname == DUMMY_CRC:
                if self.verbose > 1:
                    log.debug("Found the exported notorious dummy device.")
                self.count['dummy'] += 1
                continue

            guid = '600144f0-' + short_guid
            digest = crc64_digest(guid)
            if not digest == devname:
                log.info(("Found mismatch between volume name %r and SCST "
                          "device name %r (should be %r)."), export_filename, devname, digest)
                self.count['error'] += 1
                continue

            fc_ph_id_expected = guid.replace('-', '')
            fc_ph_id_current = self.get_fc_ph_id(dev_dir)
            if fc_ph_id_expected != fc_ph_id_current:
                log.info("Export %r for device %r has wrong fc_ph_id %r.",
                         devname, export_filename, fc_ph_id_current)
                has_errors = True

            read_only = self.get_read_only(dev_dir)
            if read_only is None:
                has_errors = True

            export = {
                'devicename': devname,
                'volume': export_filename,
                'guid': uuid.UUID(guid),
                'read_only': read_only,
                'has_errors': has_errors,
                'luns': luns,
                'checked': False,
            }

            self.existing_exports[devname] = export
            if has_errors:
                self.count['error'] += 1

            if self.verbose > 2:
                log.debug("Found export %r.", devname)

            if self.verbose > vl:
                log.debug("Got existing export:\n%s", pp(export))

            if first:
                first = False

    def check_ini_groups(self):

        igroup_pattern = os.path.join(SCST_INI_GROUP_DIR, '*')
        if self.verbose > 3:
            log.debug("Get ini groups with pattern %r ...", igroup_pattern)
        for ini_group_dir in glob.glob(igroup_pattern):
            if not os.path.isdir(ini_group_dir):
                continue
            ini_group = os.path.basename(ini_group_dir)
            if self.verbose > 3:
                log.debug("Checking initiator group %r ...", ini_group)

            if ini_group not in self.valid_pservers:
                log.info("Initiator group %r is not a pserver from current cluster.", ini_group)
                self.count['alien'] += 1
                continue

            luns_dir = os.path.join(ini_group_dir, 'luns')
            luns_pattern = os.path.join(luns_dir, '*')
            nr_luns = 0
            has_lun_zero = False
            for lun_dir in glob.glob(luns_pattern):
                if not os.path.isdir(lun_dir):
                    continue
                nr_luns += 1
                lun = os.path.basename(lun_dir)
                if lun == '0':
                    has_lun_zero = True
            if nr_luns:
                if not has_lun_zero:
                    log.info("Initiator group %r has no LUN '0'.", ini_group)
                    self.count['error'] += 1
            else:
                log.info("Initiator group %r has no LUNs.", ini_group)
                self.count['error'] += 1

    def get_fc_ph_id(self, dev_dir):

        fc_ph_id_filename = os.path.join(dev_dir, 'fc_ph_id')
        if not os.path.exists(fc_ph_id_filename):
            log.error("File for pc_ph_id %r doesn't exists.", fc_ph_id_filename)
            return None

        if not os.path.isfile(fc_ph_id_filename):
            log.error("File for pc_ph_id %r is not a regular file.", fc_ph_id_filename)
            return None

        if not os.access(fc_ph_id_filename, os.R_OK):
            log.error("No read access for file for pc_ph_id %r.", fc_ph_id_filename)
            return None

        fc_ph_id = None
        fh = None
        try:
            fh = open(fc_ph_id_filename, 'r')
            lines = fh.readlines()
            if len(lines):
                fc_ph_id = lines[0].strip()
            else:
                log.error("No pc_ph_id found in %r.", fc_ph_id_filename)
        finally:
            if fh:
                fh.close()
                fh = None

        return fc_ph_id

    def get_read_only(self, dev_dir):

        read_only_filename = os.path.join(dev_dir, 'read_only')
        if not os.path.exists(read_only_filename):
            log.error("File for read_only %r doesn't exists.", read_only_filename)
            return None

        if not os.path.isfile(read_only_filename):
            log.error("File for read_only %r is not a regular file.", read_only_filename)
            return None

        if not os.access(read_only_filename, os.R_OK):
            log.error("No read access for file for read_only %r.", read_only_filename)
            return None

        read_only = None
        fh = None
        try:
            fh = open(read_only_filename, 'r')
            lines = fh.readlines()
            if len(lines):
                read_only = bool(int(lines[0].strip()))
            else:
                log.error("No read_only info found in %r.", read_only_filename)
        finally:
            if fh:
                fh.close()
                fh = None

        return read_only

    def get_scst_export_filename(self, filename_file):

        if not os.path.exists(filename_file):
            log.error("SCST export filename file %r doesn't exists.", filename_file)
            return None

        if not os.path.isfile(filename_file):
            log.error("SCST export filename file %r is not a regular file.", filename_file)
            return None

        if not os.access(filename_file, os.R_OK):
            log.error("No read access for SCST export filename file %r.", filename_file)
            return None

        export_filename = None
        fh = None
        try:
            fh = open(filename_file, 'r')
            lines = fh.readlines()
            if len(lines):
                export_filename = lines[0].strip()
            else:
                log.error("No devicename found in %r.", filename_file)
        finally:
            if fh:
                fh.close()
                fh = None

        return export_filename
