#!/usr/bin/python

from __future__ import print_function

import re
import socket
import subprocess
import sys
import threading
import os
import textwrap
import argparse
from string import split

# install the newest version of dcmanager client
try:
    from dcmanagerclient.client import DEFAULT_API_URL
    from dcmanagerclient.client import RestApi
except ImportError:
    print("You need the dcmanagerclient installed!")
    sys.exit(7)

ON_POSIX = 'posix' in sys.builtin_module_names

version = "1.1.0-1"

appname = os.path.basename(sys.argv[0])
DEFAULT_TIMEOUT_API = 20


class ping6(threading.Thread):
    ping6list = []
    maxthreads = 30   # Increasing this number too much is a bad idea :)
    evnt = threading.Event()
    lck = threading.Lock()
    reached = {}
    notreached = {}
    failed = {}
    offline = {}

    def __init__(self, cnt, ip):
        threading.Thread.__init__(self)
        self.ping_address = ip["ping_address"]
        self.hostalias = ip["hostalias"]
        self.ipv4_address = ip["ipv4_address"]
        self.count = cnt

    def run(self):
        # catch every exception otherwise the __main__ program will hang forever
        try:
            devnull = open('/dev/null', 'w')
            try:
                subprocess.check_call(["ping6", "-c2", "-s", "0", "-w", "4",
                                       self.ping_address], stdout=devnull, stderr=devnull)
                # print(str(self.count) + " : [REACHED] " + self.hostalias)
                self.reached[self.hostalias] = 1
            except subprocess.CalledProcessError:
                # host is not pingable via ping6
                # try to ping its ipv4 address to see if the host is offline
                # print(str(self.count) + " : [IPv6 NOT REACHED] " + self.hostalias +
                #       " (return code: %s)" % e.returncode)
                try:
                    subprocess.check_call(["ping", "-c2", "-s", "0", "-w", "4", self.ipv4_address],
                                          stdout=devnull, stderr=devnull)
                    # print(str(self.count) + " : [IPv4 REACHED] " + self.ipv4_address)
                    self.notreached[self.hostalias] = 1
                except subprocess.CalledProcessError:
                    # print(str(self.count) + " : [IPv4 NOT REACHED] " + self.ipv4_address +
                    #       " (return code: %s)" % ee.returncode)
                    self.offline[self.hostalias] = 1
            devnull.close()

            ping6.lck.acquire()
            # print("  PING6: remove myself")
            ping6.ping6list.remove(self)
            # print("  PING6: used threads %d of %d" % (len(ping6.ping6list), ping6.maxthreads))

            # some debug code to force a exception since format() is used the wrong way
            # this is used to test the code around the exception handling adding elements to
            # self.failed

            # if self.count % 10 == 0:
            #     print("self.count (%d)" % self.count)
            #     print("  PING6: used threads {:d} of {:d}".format(len(ping6.ping6list),
            #                                                       ping6.maxthreads))

            if len(ping6.ping6list) == ping6.maxthreads - 1:
                # print("  PING6: set()")
                ping6.evnt.set()

            ping6.lck.release()
        except Exception:
            if (self.hostalias not in self.notreached and self.hostalias not in self.reached and
                    self.hostalias not in self.offline):
                # print("did not find %s in self.reached, self.notreached or self.offline" %
                #       self.hostalias)
                self.failed[self.hostalias] = 1
            # elif self.hostalias in (self.reached):
            #     print("found %s in self.reached" % self.hostalias)
            # elif self.hostalias in (self.offline):
            #     print("found %s in self.offline" % self.hostalias)
            # else:
            #     print("found %s in self.notreached" % self.hostalias)

            # free the ping6.evnt for the next requestor
            ping6.evnt.set()
            try:
                # free any existing lock for the next requestor
                ping6.lck.release()
            except threading.ThreadError:
                pass
                # print("there was no lock")

    def newthread(count, host):
        ping6.lck.acquire()
        pg6 = ping6(count, host)
        ping6.ping6list.append(pg6)
        ping6.lck.release()
        pg6.start()
    newthread = staticmethod(newthread)


def parse_args():

    msg = """\
    This program will ping6 all pservers and gateways in the same cluster
    on both infiniband topologies to identify broken ib connectivity.

    """
    msg = textwrap.dedent(msg) % {'appname': appname}

    # Init the parser
    parser = argparse.ArgumentParser(
        prog=appname,
        description='detect broken infiniband connectivity',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=msg,
    )

    # Some general options
    parser.add_argument('--version', action='version', version=version)
    parser.add_argument('--auth-token', type=str,
                        help="extra ini-file storing the dcmanager auth token")

    msg = "define the dcmanager url (default: %s)" % (DEFAULT_API_URL)
    parser.add_argument('--url', type=str, help=msg)
    parser.add_argument(
        '--timeout', type=int, default=DEFAULT_TIMEOUT_API,
        help="Timeout in communication with the REST API (default: %(default)s seconds)"
    )
    parser.add_argument(
        '--ignore-dcmanager-host-states', dest='ignore_host_states',
        action='store_true', default=False,
        help="Continue despite of the pserver/gateway being marked down in the dcmanager"
    )

    try:
        args = parser.parse_args()
    except IOError as msg:
        parser.error(str(msg))

    return args


def pinghost(i, pinghost):
    ping6.lck.acquire()
    if len(ping6.ping6list) >= ping6.maxthreads:
        ping6.lck.release()
        # print("%s: maxthreads %d reached, waiting ..." % (pinghost[hostalias], ping6.maxthreads))

        # Set the signal handler and a 5-second alarm
        # signal.signal(signal.SIGALRM, ping6_evnt_wait_timeout)
        # signal.alarm(1)

        # This may hang indefinitely
        # ping6.evnt.wait()

        # signal.alarm(0)          # Disable the alarm

        # print("  .. ping6.evnt.clear() for %s" % (pinghost[hostalias]))
        ping6.evnt.clear()
        # print("  .. go")
    else:
        ping6.lck.release()
        # print("%s: go, current number of threads: %d" % (pinghost[hostalias],
        #                                                  len(ping6.ping6list)))
    ping6.newthread(i, pinghost)
    # ping6.newthread(i, pinghost.rstrip())
    i += 1
    return i


def get_bgp_neighbors():
    bgp_pattern = re.compile('^bgp\d+$')
    bgp_host_pattern = re.compile('\([A-Za-z0-9-.]+\)$')
    bgp_neighbors = {}
    devnull = open('/dev/null', 'w')
    # EXPECTED OUTPUT
    # tmoericke@pserver1719:~$ sudo birdc6 show protocols  |grep BGP| awk '{print $1}'
    # bgp1
    # bgp2
    # bgp3
    # bgp4
    cmd = subprocess.Popen("sudo birdc6 show protocols | grep BGP | awk '{print $1}'", shell=True,
                           stdout=subprocess.PIPE, stderr=devnull)
    for bgp in cmd.stdout:
        bgp = bgp.strip()
        if not bgp_pattern.match(bgp):
            # print("fail %s" % bgp)
            continue

        # print(bgp)

        # EXPECTED OUTPUT
        # tmoericke@pserver1719:~$ sudo birdc6 show protocols all bgp1 | \
        #                          egrep '(BGP state|Neighbor address|Neighbor ID|Description):'
        #   Description:    gateway-fc57:1:0:1:0:11:2:1 (gw1701)
        #   BGP state:          Established
        #     Neighbor address: fc57:1:0:1:0:11:2:1
        #     Neighbor ID:      10.1.171.249
        birdc6_command = "sudo birdc6 show protocols all %s" % bgp
        cmd2 = subprocess.Popen(
            "%s | egrep '(BGP state|Neighbor address|Neighbor ID|Description):'" % birdc6_command,
            shell=True, stdout=subprocess.PIPE, stderr=devnull
        )
        bgp_detail = {}
        for line in cmd2.stdout:
            # line = line.strip()
            elements = line.split(":", 1)
            field = elements[0].strip()
            value = elements[1].strip()
            bgp_detail[field] = value
        # pprint.pprint(bgp_detail)
        # print(bgp_detail["Description"])
        if "Description" in bgp_detail:
            m = bgp_host_pattern.search(bgp_detail["Description"])
            if m:
                bgp_hostname = m.group().strip("()")
            elif "Neighbor ID" in bgp_detail:
                try:
                    bgp_hostname = socket.gethostbyaddr(bgp_detail["Neighbor ID"])[0]
                    pattern = re.compile('.%s' % domain)
                    bgp_hostname = pattern.sub('', bgp_hostname)
                except socket.herror:
                    bgp_hostname = bgp_detail["Neighbor ID"]
            elif "Neighbor address" in bgp_detail:
                bgp_hostname = bgp_detail["Neighbor address"]
            else:
                print("UNKNOWN: Failed to extract hostname, ipv4 and ipv6 address "
                      "from command: '%s'" % birdc6_command)
                sys.exit(state['UNKNOWN'])

        bgp_neighbors[bgp_hostname] = {}
        for element in bgp_detail.keys():
            if element != "Description":
                bgp_neighbors[bgp_hostname][element] = bgp_detail[element]

    # pprint.pprint(bgp_neighbors)
    devnull.close()
    return bgp_neighbors


if __name__ == '__main__':
    args = parse_args()

    state = {"OK": 0, "WARNING": 1, "CRITICAL": 2, "UNKNOWN": 3}

    fqdn = socket.getfqdn(socket.gethostname())
    (hostname, domain) = split(fqdn, '.', 1)
    del fqdn

    url = args.url
    efile = args.auth_token
    timeout = args.timeout

    pattern = re.compile('^(pserver|gw|ps)(\d+[a-z]-)?\d+$')
    if not pattern.match(hostname):
        print("UNKNOWN: only pservers and gateways are supported")
        sys.exit(state['UNKNOWN'])

    api = RestApi.from_config(extra_config_file=efile, api_url=url, timeout=timeout)

    # fetch the cluster name of current hostname
    response = dict()
    try:
        response = api.pservers(name=hostname)
    except Exception as e:
        print("UNKNOWN: failed to fetch cluster name from dcmanager api for host %s: %s" %
              (hostname, str(e)))
        sys.exit(state['UNKNOWN'])

    if len(response) == 1 and 'cluster' in response[0]:
        cluster = response[0]['cluster']
    else:
        print("UNKNOWN: dcmanager api response for host %s does not contain "
              "any 'cluster' attribute" % hostname)
        sys.exit(state['UNKNOWN'])

    if 'state' not in response[0]:
        print("UNKNOWN: dcmanager api response for host %s does not contain "
              "any 'state' attribute" % hostname)
        sys.exit(state['UNKNOWN'])

    if not args.ignore_host_states and response[0]['state'] != 'UP':
        print("OK: host %s is not marked as 'UP' in dcmanager" % hostname)
        sys.exit(state['OK'])

    # fetch all pservers in this cluster
    try:
        pservers = api.pservers(cluster=cluster)
    except Exception as e:
        print("UNKNOWN: failed to fetch pservers from cluster %s from "
              "dcmanager api: %s" % (cluster, str(e)))
        sys.exit(state['UNKNOWN'])

    # fetch all pateways in this cluster
    try:
        gateways = api.pgateways(cluster=cluster)
    except Exception as e:
        print("UNKNOWN: failed to fetch gateways from cluster %s from dcmanager api: %s" %
              (cluster, str(e)))
        sys.exit(state['UNKNOWN'])

    # fetch bgp neighbors
    bgp_neighbors = get_bgp_neighbors()

    # check pservers in this cluster
    dcmanager_offline = []
    n = 0
    for ps in pservers:
        if not args.ignore_host_states and ps["state"] != 'UP':
            dcmanager_offline.append(ps["name"])
            continue
        for i in range(2):
            fqdn = '%s-ib%i.%s' % (ps["name"], i, domain)
            ping_host = {}
            ping_host["ping_address"] = fqdn
            ping_host["hostalias"] = fqdn
            # ping_host["hostalias"] = '%s-ib%i' % (ps["name"], i)
            ping_host["ipv4_address"] = ps["ip"]
            n = pinghost(n, ping_host)

    bgp_no_neighbor = []
    bgp_no_link = []
    bgp_ipv4_mismatch = []
    bgp_no_ipv6_address = []
    bgp_no_ipv4_address = []

    # check pgateways in this cluster
    for ps in gateways:
        if not args.ignore_host_states and ps["state"] != 'UP':
            dcmanager_offline.append(ps["name"])
            continue
        ping_hostname = ps["name"]
        if ping_hostname not in bgp_neighbors:
            if ps["ip_addr"] in bgp_neighbors:
                ping_hostname = ps["ip_addr"]
            else:
                bgp_no_neighbor.append(ps["name"])
                continue

        if "Neighbor address" not in bgp_neighbors[ping_hostname]:
            bgp_no_ipv6_address.append(ping_hostname)
            continue

        # run ping
        ping_host = {}
        ping_host["ping_address"] = bgp_neighbors[ping_hostname]["Neighbor address"]
        ping_host["hostalias"] = ping_hostname
        ping_host["ipv4_address"] = ps["ip_addr"]
        n = pinghost(n, ping_host)

        if ping_hostname not in ping6.offline:
            if ("BGP state" not in bgp_neighbors[ping_hostname] or
                    bgp_neighbors[ping_hostname]["BGP state"] != "Established"):
                bgp_no_link.append(ping_hostname)

            if "Neighbor ID" not in bgp_neighbors[ping_hostname]:
                bgp_no_ipv4_address.append(ping_hostname)
            elif bgp_neighbors[ping_hostname]["Neighbor ID"] != ps["ip_addr"]:
                bgp_ipv4_mismatch.append(ping_hostname)

    while True:
        num_threads = len(ping6.ping6list)
        # print(num_threads)
        if num_threads == 0:
            break

    # print("Total Host Scanned : %d" % n)
    # print("not reachable      : %s" % (', '.join(ping6.notreached)))

    pattern = re.compile('.%s' % domain)
    # print("INFO: reached: %d, notreached: %d, failed: %d" %
    #       (len(ping6.reached), len(ping6.notreached), len(ping6.failed)))
    msg = []
    n += len(dcmanager_offline)
    cur_state = "OK"
    if len(ping6.notreached) > 0:
        msg.append("%d/%d hosts are not reachable (%s)" %
                   (len(ping6.notreached), n,
                    pattern.sub('', ', '.join(sorted(ping6.notreached.keys())))))
    if len(ping6.failed) > 0:
        msg.append("failed check for %d/%d hosts (%s)" %
                   (len(ping6.failed), n, pattern.sub('', ', '.join(sorted(ping6.failed.keys())))))
    # TODO: enable this line as soon as the gateways in cluster 1-4 are reinstalled and
    #       are visible by all pservers
    # if len(bgp_no_neighbor) > 0:
    #    msg.append("%d hosts not found in bird setup (%s)" %
    #               (len(bgp_no_neighbor),pattern.sub('',', '.join(sorted(bgp_no_neighbor)))))
    if len(bgp_no_link) > 0:
        msg.append("%d/%d hosts in bird setup have no established BGP state (%s)" %
                   (len(bgp_no_link), len(bgp_neighbors),
                    pattern.sub('', ', '.join(sorted(bgp_no_link)))))
    if len(bgp_no_ipv4_address) > 0:
        msg.append("%d/%d hosts have no IPv4 address in bird setup (%s)" %
                   (len(bgp_no_ipv4_address), len(bgp_neighbors),
                    pattern.sub('', ', '.join(sorted(bgp_no_ipv4_address)))))
    if len(bgp_ipv4_mismatch) > 0:
        msg.append("IPv4 address differs for %d/%d hosts between bird setup and dcmanager (%s)" %
                   (len(bgp_ipv4_mismatch), len(bgp_neighbors),
                    pattern.sub('', ', '.join(sorted(bgp_ipv4_mismatch)))))
    if len(bgp_no_ipv6_address) > 0:
        msg.append("%d/%d hosts in bird setup have no IPv6 address (%s)" %
                   (len(bgp_no_ipv6_address), len(bgp_neighbors),
                    pattern.sub('', ', '.join(sorted(bgp_no_ipv6_address)))))

    if len(msg):
        cur_state = "CRITICAL"
    elif len(ping6.reached) > 0:
        msg.append("%d/%d hosts in cluster %s are reachable (%s)" %
                   (len(ping6.reached), n, cluster,
                    pattern.sub('', ', '.join(sorted(ping6.reached.keys())))))

    info = []

    if len(dcmanager_offline) > 0:
        info.append("%d/%d hosts are down in dcmanager (%s)" %
                    (len(dcmanager_offline), n,
                     pattern.sub('', ', '.join(sorted(dcmanager_offline)))))
    if len(ping6.offline) > 0:
        info.append("%d/%d hosts are offline (%s)" %
                    (len(ping6.offline), n,
                     pattern.sub('', ', '.join(sorted(ping6.offline.keys())))))
    # TODO: remove the next 2 lines (regarding bgp_no_neighbor) as soon as the gateways
    #       in cluster 1-4 are reinstalled and are visible by all pservers
    if len(bgp_no_neighbor) > 0:
        info.append("%d hosts not found in bird setup (%s)" %
                    (len(bgp_no_neighbor), pattern.sub('', ', '.join(sorted(bgp_no_neighbor)))))
    # TODO: end

    str = "%s: " % (cur_state) + ', '.join(msg)
    if len(info):
        str += ", INFO: " + ', '.join(info)

    print(str)
    sys.exit(state[cur_state])

# vim: ts=4 sw=4 et filetype=python
