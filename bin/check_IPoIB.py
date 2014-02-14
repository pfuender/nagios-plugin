#!/usr/bin/python

from __future__ import print_function
import signal,sys,os,re,time,threading,subprocess
import json
from socket import getfqdn, gethostname, getaddrinfo, AF_INET6, SOCK_RAW
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
   
    def __init__(self,cnt,ip):
        threading.Thread.__init__(self);
        self.ip = ip
        #self.status = -1
        self.count = cnt

    def run(self):
        ## catch every exception otherwise the __main__ program will hang forever
        try:
            devnull = open('/dev/null', 'w')
            try:
                proc = subprocess.check_call(["ping6", "-c2", "-s", "0", "-w", "4", self.ip],stdout=devnull, stderr=devnull)
                #print(str(self.count)+" : [REACHED] "+self.ip)
                self.reached[self.ip] = 1
            except subprocess.CalledProcessError as e:
                #print(str(self.count)+" : [NOT REACHED] "+self.ip+" (return code: %s)" % (e.returncode))
                self.notreached[self.ip] = 1
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
            #else:
                #print("  PING6: skipped set() + clear()")
          
            ping6.lck.release()
        except Exception, e:
            if self.ip not in self.notreached and self.ip not in self.reached:
                #print("did not find %s in self.reached or self.notreached" % (self.ip))
                self.failed[self.ip] = 1
            #elif self.ip in (self.reached):
            #    print("found %s in self.reached" % (self.ip))
            #else:
            #    print("found %s in self.notreached" % (self.ip))

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


#def ping6_evnt_wait_timeout(signum, frame):
#    print('UNKNOWN: timeout for ping6.evnt.wait() for host %s' % (fqdn))
#    sys.exit(state['UNKNOWN'])

## TODO: replace static progname with some basename methode on ARG[0]
progname = "check_IPoIB.py"

state = {"OK": 0, "WARNING": 1, "CRITICAL": 2, "UNKNOWN": 3}

#verbose = 0
#type = ""

#def print_usage():
#    print "Usage: ${PROGNAME} -t|--type <server type> [-v|--verbose]"
#
#def print_help():
#    print "\n"
#    print_usage()
#    print "\n"
#    print "    -v                         enable verbose output\n"
#    print "\n"
#    exit(state['OK'])
#
#def print_verbose(str):
#    if verbose == 1:
#        print str

# do the work
#exit = state['UNKNOWN']

## TODO: pservers and storages need also to include gateways.
##       Add a loop here or handle gateways in a special way.
url='https://dcmanager.pb.local:443/dc/api/pservers/?up=true'
token="604a3b5f6db67e5a3a48650313ddfb2e8bcf211b"
fqdn = getfqdn(gethostname())
(hostname,domain) = split(fqdn,'.',1)

req = Request(url, None, {'Authorization': "Token " + token})
try:
    response = urlopen(req)
except HTTPError as e:
    print('UNKNOWN: The server couldn\'t fulfill the request. Error code: ', e.code)
    sys.exit(state['UNKNOWN'])
except URLError as e:
    print('UNKNOWN: Failed to reach dcmanager api. Reason: ', e.reason)
    sys.exit(state['UNKNOWN'])

j = json.loads(response.read())
cluster = ""
for ps in j:
    if ps["name"] == hostname :
        cluster = ps["cluster"]
        break

if cluster == "":
    print("UNKNOWN: %s is not part of any cluster in dcmanager result set" % (hostname))
    sys.exit(state['UNKNOWN'])

n = 0
for ps in j:
    if ps["cluster"] == cluster :
        for i in range(2):
            fqdn = '%s-ib%i.%s' % (ps["name"], i, domain)
            ping6.lck.acquire()
            if len(ping6.ping6list) >= ping6.maxthreads:
                ping6.lck.release()
                #print("%s: maxthreads %d reached, waiting ..." % (fqdn, ping6.maxthreads))

                # Set the signal handler and a 5-second alarm
                #signal.signal(signal.SIGALRM, ping6_evnt_wait_timeout)
                #signal.alarm(1)

                # This may hang indefinitely
                #ping6.evnt.wait()

                #signal.alarm(0)          # Disable the alarm

                #print("  .. ping6.evnt.clear() for %s" % (fqdn))
                ping6.evnt.clear()
                #print("  .. go")
            else:
                ping6.lck.release()
                #print("%s: go, current number of threads: %d" % (fqdn,len(ping6.ping6list)))
            ping6.newthread(n,fqdn.rstrip())
            n += 1


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
if len(ping6.notreached) > 0:
    msg.append("%d of %d hosts are not reachable (%s)" % (len(ping6.notreached),n,pattern.sub('',', '.join(sorted(ping6.notreached.keys())))))
if len(ping6.failed) > 0:
    msg.append("failed check for %d of %d hosts (%s)" % (len(ping6.failed),n,pattern.sub('',', '.join(sorted(ping6.failed.keys())))))
if len(msg):
    print("CRITICAL: " + ', '.join(msg))
    sys.exit(state['CRITICAL'])
else:
    print("OK: all hosts in cluster %s reachable (%s)" % (cluster,pattern.sub('',', '.join(sorted(ping6.reached.keys())))))
    sys.exit(state['OK'])

# vim: ts=4 sw=4 et filetype=python
