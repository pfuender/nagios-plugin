#!/usr/bin/python

from __future__ import print_function
import signal,sys,os,re,time,threading,subprocess
import json
import pprint
import socket
from string import split
from urllib2 import Request, urlopen, URLError, HTTPError


#############################################
############# BEGIN class ping6 #############
class ping6(threading.Thread):
    ping6list = []
    maxthreads = 30   # Increasing this number too much is a bad idea :)
    evnt = threading.Event()
    lck = threading.Lock()
    reached = {}
    notreached = {}
    failed = {}
    offline = {}
 
    def __init__(self,cnt,ip):
        threading.Thread.__init__(self);
        self.ping_address = ip["ping_address"]
        self.hostalias = ip["hostalias"]
        self.ipv4_address = ip["ipv4_address"]
        self.count = cnt

    def run(self):
        ## catch every exception otherwise the __main__ program will hang forever
        try:
            devnull = open('/dev/null', 'w')
            try:
                proc = subprocess.check_call(["ping6", "-c2", "-s", "0", "-w", "4", self.ping_address],stdout=devnull, stderr=devnull)
                #print(str(self.count)+" : [REACHED] "+self.hostalias)
                self.reached[self.hostalias] = 1
            except subprocess.CalledProcessError as e:
                ## host is not pingable via ping6
                ## try to ping its ipv4 address to see if the host is offline
                #print(str(self.count)+" : [IPv6 NOT REACHED] "+self.hostalias+" (return code: %s)" % (e.returncode))
                try:
                    proc = subprocess.check_call(["ping", "-c2", "-s", "0", "-w", "4", self.ipv4_address],stdout=devnull, stderr=devnull)
                    #print(str(self.count)+" : [IPv4 REACHED] "+self.ipv4_address)
                    self.notreached[self.hostalias] = 1
                except subprocess.CalledProcessError as ee:
                    #print(str(self.count)+" : [IPv4 NOT REACHED] "+self.ipv4_address+" (return code: %s)" % (ee.returncode))
                    self.offline[self.hostalias] = 1
            devnull.close()

            ping6.lck.acquire()
            #print("  PING6: remove myself")
            ping6.ping6list.remove(self)
            #print("  PING6: used threads %d of %d" % (len(ping6.ping6list), ping6.maxthreads))

            ### some debug code to force a exception since format() is used the wrong way
            ### this is used to test the code around the exception handling adding elements to self.failed
            #if self.count % 10 == 0:
            #    print("self.count (%d)" % self.count)
            #    print("  PING6: used threads {:d} of {:d}".format(len(ping6.ping6list), ping6.maxthreads))

            if len(ping6.ping6list) == ping6.maxthreads-1:
                #print("  PING6: set()")
                ping6.evnt.set()
          
            ping6.lck.release()
        except Exception, e:
            if self.hostalias not in self.notreached and self.hostalias not in self.reached and self.hostalias not in self.offline:
                #print("did not find %s in self.reached, self.notreached or self.offline" % (self.hostalias))
                self.failed[self.hostalias] = 1
            #elif self.hostalias in (self.reached):
            #    print("found %s in self.reached" % (self.hostalias))
            #elif self.hostalias in (self.offline):
            #    print("found %s in self.offline" % (self.hostalias))
            #else:
            #    print("found %s in self.notreached" % (self.hostalias))

            # free the ping6.evnt for the next requestor
            ping6.evnt.set()
            try:
                # free any existing lock for the next requestor
                ping6.lck.release()  
            except ThreadError, te:
                dummy = 0
                #print("there was no lock")

    def newthread(count,hst):
        ping6.lck.acquire()
        pg6 = ping6(count,hst)
        ping6.ping6list.append(pg6)
        ping6.lck.release()
        pg6.start()
    newthread = staticmethod(newthread)
############# END class ping6 ###############
#############################################

def pinghost(i,pinghost):
    ping6.lck.acquire()
    if len(ping6.ping6list) >= ping6.maxthreads:
        ping6.lck.release()
        #print("%s: maxthreads %d reached, waiting ..." % (pinghost[hostalias], ping6.maxthreads))

        # Set the signal handler and a 5-second alarm
        #signal.signal(signal.SIGALRM, ping6_evnt_wait_timeout)
        #signal.alarm(1)

        # This may hang indefinitely
        #ping6.evnt.wait()

        #signal.alarm(0)          # Disable the alarm

        #print("  .. ping6.evnt.clear() for %s" % (pinghost[hostalias]))
        ping6.evnt.clear()
        #print("  .. go")
    else:
        ping6.lck.release()
        #print("%s: go, current number of threads: %d" % (pinghost[hostalias],len(ping6.ping6list)))
    ping6.newthread(i,pinghost)
    #ping6.newthread(i,pinghost.rstrip())
    i += 1
    return i

### TODO: get also hosts that are down and handle them correctly
def get_serverlist(type):
    ## TODO: storages are not included yet
    url='https://dcmanager.pb.local:443/dc/api/' + type + '/'
    token="604a3b5f6db67e5a3a48650313ddfb2e8bcf211b"
    
    req = Request(url, None, {'Authorization': "Token " + token})
    try:
        response = urlopen(req)
    except HTTPError as e:
        print('UNKNOWN: The server couldn\'t fulfill the request. Error code: ', e.code)
        sys.exit(state['UNKNOWN'])
    except URLError as e:
        print('UNKNOWN: Failed to reach dcmanager api. Reason: ', e.reason)
        sys.exit(state['UNKNOWN'])
    return json.loads(response.read())

def get_bgp_neighbors():
    bgp_pattern = re.compile('^bgp\d+$')
    bgp_host_pattern = re.compile('\([A-Za-z0-9-.]+\)$')
    bgp_neighbors = {}
    devnull = open('/dev/null', 'w')
    ## EXPECTED OUTPUT
    ## tmoericke@pserver1719:~$ sudo birdc6 show protocols  |grep BGP| awk '{print $1}'
    ## bgp1
    ## bgp2
    ## bgp3
    ## bgp4
    cmd = subprocess.Popen("sudo birdc6 show protocols  |grep BGP| awk '{print $1}'", shell=True, stdout=subprocess.PIPE, stderr=devnull)
    for bgp in cmd.stdout:
        bgp = bgp.strip()
        if not bgp_pattern.match(bgp):
            #print("fail %s" % bgp)
            continue

        #print(bgp)

        ## EXPECTED OUTPUT
        ## tmoericke@pserver1719:~$ sudo birdc6 show protocols all bgp1 |egrep '(BGP state|Neighbor address|Neighbor ID|Description):'
        ##   Description:    gateway-fc57:1:0:1:0:11:2:1 (gw1701)
        ##   BGP state:          Established
        ##     Neighbor address: fc57:1:0:1:0:11:2:1
        ##     Neighbor ID:      10.1.171.249
        birdc6_command = "sudo birdc6 show protocols all %s" % bgp
        cmd2 = subprocess.Popen("%s |egrep '(BGP state|Neighbor address|Neighbor ID|Description):'" % birdc6_command, shell=True, stdout=subprocess.PIPE, stderr=devnull)
        bgp_detail = {}
        for line in cmd2.stdout:
            #line = line.strip()
            elements = line.split(":",1)
            field = elements[0].strip()
            value = elements[1].strip()
            bgp_detail[field] = value
        #pprint.pprint(bgp_detail)
        #print(bgp_detail["Description"])
        if "Description" in bgp_detail:
            m = bgp_host_pattern.search(bgp_detail["Description"])
            if m:
                bgp_hostname = m.group().strip("()")
            elif "Neighbor ID" in bgp_detail:
                try:
                    bgp_hostname = socket.gethostbyaddr(bgp_detail["Neighbor ID"])[0]
                    pattern = re.compile('.%s' % domain)
                    bgp_hostname = pattern.sub('',bgp_hostname)
                except socket.herror as e:
                    bgp_hostname = bgp_detail["Neighbor ID"]
            elif "Neighbor address" in bgp_detail:
                bgp_hostname = bgp_detail["Neighbor address"]
            else:
                print("UNKNOWN: Failed to extract hostname, ipv4 and ipv6 address from command: '%s'" % birdc6_command)
                sys.exit(state['UNKNOWN'])

        bgp_neighbors[bgp_hostname] = {}
        for element in bgp_detail.keys():
            if element != "Description":
                bgp_neighbors[bgp_hostname][element] = bgp_detail[element]
            
    ###pprint.pprint(bgp_neighbors)
    devnull.close()
    return bgp_neighbors


## TODO: replace static progname with some basename methode on ARG[0]
progname = "check_IPoIB.py"

state = {"OK": 0, "WARNING": 1, "CRITICAL": 2, "UNKNOWN": 3}

fqdn = socket.getfqdn(socket.gethostname())
(hostname,domain) = split(fqdn,'.',1)
del fqdn

pservers = get_serverlist("pservers")
gateways = get_serverlist("pgateways")
bgp_neighbors = get_bgp_neighbors()

pattern = re.compile('\d+$')
hosttype = pattern.sub('',hostname)
#print("type: %s" % hosttype)
if hosttype == "pserver":
    serverlist = pservers
elif hosttype == "gw":
    serverlist = gateways
else:
    print("UNKNOWN: hosttype '%s' is not supported currently" % (hosttype))
    sys.exit(state['UNKNOWN'])


cluster = ""
for ps in serverlist:
    if ps["name"] == hostname :
        if ps["up"] == False:
            print("OK: host %s is marked as down in dcmanager" % hostname);
            sys.exit(state['OK'])
        else:
            cluster = ps["cluster"]
            break

del serverlist

if cluster == "":
    print("UNKNOWN: %s is not part of any cluster in dcmanager result set" % (hostname))
    sys.exit(state['UNKNOWN'])

dcmanager_offline = []
n = 0
for ps in pservers:
    if ps["cluster"] == cluster :
        if ps["up"] == False:
            dcmanager_offline.append(ps["name"])
            continue
        for i in range(2):
            fqdn = '%s-ib%i.%s' % (ps["name"], i, domain)
            ping_host = {}
            ping_host["ping_address"] = fqdn
            ping_host["hostalias"] = fqdn
            #ping_host["hostalias"] = '%s-ib%i' % (ps["name"], i)
            ping_host["ipv4_address"] = ps["ip"]
            n = pinghost(n,ping_host)


bgp_no_neighbor = []
bgp_no_link = []
bgp_ipv4_mismatch = []
bgp_no_ipv6_address = []
bgp_no_ipv4_address = []

for ps in gateways:
    if ps["cluster"] == cluster :
        if ps["up"] == False:
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

        ## run ping
        ping_host = {}
        ping_host["ping_address"] = bgp_neighbors[ping_hostname]["Neighbor address"]
        ping_host["hostalias"] = ping_hostname
        ping_host["ipv4_address"] = ps["ip_addr"]
        n = pinghost(n,ping_host)

        if "BGP state" not in bgp_neighbors[ping_hostname] or bgp_neighbors[ping_hostname]["BGP state"] != "Established":
            bgp_no_link.append(ping_hostname)

        if "Neighbor ID" not in bgp_neighbors[ping_hostname]:
            bgp_no_ipv4_address.append(ping_hostname)
        elif bgp_neighbors[ping_hostname]["Neighbor ID"] != ps["ip_addr"]:
            bgp_ipv4_mismatch.append(ping_hostname)


while 1:
    num_threads = len(ping6.ping6list)
    #print(num_threads)
    if num_threads == 0:
        break

#print("Total Host Scanned : %d" % n)
#print("not reachable      : %s" % (', '.join(ping6.notreached)))


pattern = re.compile('.%s' % domain)
##print("INFO: reached: %d, notreached: %d, failed: %d" % (len(ping6.reached),len(ping6.notreached),len(ping6.failed)))
msg = []
n += len(dcmanager_offline)
cur_state = "OK"
if len(ping6.notreached) > 0:
    msg.append("%d/%d hosts are not reachable (%s)" % (len(ping6.notreached),n,pattern.sub('',', '.join(sorted(ping6.notreached.keys())))))
if len(ping6.failed) > 0:
    msg.append("failed check for %d/%d hosts (%s)" % (len(ping6.failed),n,pattern.sub('',', '.join(sorted(ping6.failed.keys())))))
### TODO: enable this line as soon as the gateways in cluster 1-4 are reinstalled and are visible by all pservers
#if len(bgp_no_neighbor) > 0:
#    msg.append("%d hosts not found in bird setup (%s)" % (len(bgp_no_neighbor),pattern.sub('',', '.join(sorted(bgp_no_neighbor)))))
if len(bgp_no_link) > 0:
    msg.append("%d/%d hosts in bird setup have no established BGP state (%s)" % (len(bgp_no_link),len(bgp_neighbors),pattern.sub('',', '.join(sorted(bgp_no_link)))))
if len(bgp_no_ipv4_address) > 0:
    msg.append("%d/%d hosts have no IPv4 address in bird setup (%s)" % (len(bgp_no_ipv4_address),len(bgp_neighbors),pattern.sub('',', '.join(sorted(bgp_no_ipv4_address)))))
if len(bgp_ipv4_mismatch) > 0:
    msg.append("IPv4 address differs for %d/%d hosts between bird setup and dcmanager (%s)" % (len(bgp_ipv4_mismatch),len(bgp_neighbors),pattern.sub('',', '.join(sorted(bgp_ipv4_mismatch)))))
if len(bgp_no_ipv6_address) > 0:
    msg.append("%d/%d hosts in bird setup have no IPv6 address (%s)" % (len(bgp_no_ipv6_address),len(bgp_neighbors),pattern.sub('',', '.join(sorted(bgp_no_ipv6_address)))))

if len(msg):
    cur_state = "CRITICAL"
elif len(ping6.reached) > 0:
    msg.append("%d/%d hosts in cluster %s are reachable (%s)" % (len(ping6.reached),n,cluster,pattern.sub('',', '.join(sorted(ping6.reached.keys())))))

print("%s: " % (cur_state) + ', '.join(msg))

msg = []
if len(dcmanager_offline) > 0:
    msg.append("%d/%d hosts in cluster %s are down in dcmanager (%s)" % (len(dcmanager_offline),n,cluster,pattern.sub('',', '.join(sorted(dcmanager_offline)))))
if len(ping6.offline) > 0:
    msg.append("%d/%d hosts in cluster %s are offline (%s)" % (len(ping6.offline),n,cluster,pattern.sub('',', '.join(sorted(ping6.offline.keys())))))
### TODO: remove the next 2 lines (regarding bgp_no_neighbor) as soon as the gateways in cluster 1-4 are reinstalled and are visible by all pservers
if len(bgp_no_neighbor) > 0:
    msg.append("%d hosts not found in bird setup (%s)" % (len(bgp_no_neighbor),pattern.sub('',', '.join(sorted(bgp_no_neighbor)))))
### TODO: end

print(", INFO: " % (cur_state) + ', '.join(msg))
sys.exit(state[cur_state])

# vim: ts=4 sw=4 et filetype=python
