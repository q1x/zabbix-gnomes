#!/usr/bin/env python
#
# import needed modules.
# pyzabbix is needed, see https://github.com/lukecyca/pyzabbix
#
import argparse
import ConfigParser
import os
import os.path
import sys
import distutils.util
import textwrap
import time
from pyzabbix import ZabbixAPI
from datetime import datetime

# define config helper function
def ConfigSectionMap(section):
    dict1 = {}
    options = Config.options(section)
    for option in options:
 	try:
		dict1[option] = Config.get(section, option)
		if dict1[option] == -1:
			DebugPrint("skip: %s" % option)
	except:
		print("exception on %s!" % option)
		dict1[option] = None
    return dict1

# conversion of timestamp
def timestr(timestamp):
    if timestamp.isdigit:
            timestring=datetime.utcfromtimestamp(int(timestamp)).strftime('%Y-%m-%d %H:%M:%S (UTC)')
            return timestring

# Zabbix severity mapper
def severitymap(level):
    level=int(level)    
    if level<6:
            map=['Not Classified','Information','Warning','Average','High','Disaster']
            color=[None,None,'yellow','yellow','red','red']
            try: 
                from termcolor import colored
                return colored(map[level],color[level])
            except:
                return map[level]

# Zabbix trigger status mapper
def statusmap(status):
    status=int(status)    
    if status<2:
            map=['OK','PROBLEM']
            color=['green','red']
            try:
                from termcolor import colored
                return colored(map[status],color[status])
            except:
                return map[status]

# Zabbix acknowledge status mapper
def ackmap(acknowledged):
    acknowledged=int(acknowledged)    
    if acknowledged<2:
            return bool(acknowledged)

# Zabbix Alert type mapper
def alerttypemap(atype):
    atype=int(atype)    
    if atype<2:
            map=['Message','Remote Command']
            return map[atype]
  
# Zabbix alert status mapper
def alertstatusmap(status,atype=0):
    status=int(status)
    atype=int(atype)    
    if atype==0:
            map=['Not sent','Sent', 'Failed to sent']
    elif atype==1:        
            map=['Run','Not run']
    return map[status]

# set default vars
try:
 defconf = os.getenv("HOME") + "/.zbx.conf"
except:
 defconf = None
username = ""
password = ""
api = ""
noverify = ""

# Define commandline arguments
parser = argparse.ArgumentParser(formatter_class=argparse.RawDescriptionHelpFormatter,description='Finds Zabbix events and prints them in a syslog like format. If the termcolor module is found, it is used to generate colored output.', epilog="""
This program can use .ini style configuration files to retrieve the needed API connection information.
To use this type of storage, create a conf file (the default is $HOME/.zbx.conf) that contains at least the [Zabbix API] section and any of the other parameters:
       
 [Zabbix API]
 username=johndoe
 password=verysecretpassword
 api=https://zabbix.mycompany.com/path/to/zabbix/frontend/
 no_verify=true

""")
group = parser.add_mutually_exclusive_group(required=True)
group2 = parser.add_mutually_exclusive_group(required=False)
group3 = parser.add_mutually_exclusive_group(required=False)
group.add_argument('-H', '--hostnames' ,help='Hostname(s) to find events for', nargs='+')
group.add_argument('-G', '--hostgroups' ,help='Hostgroup(s) to find events for', nargs='+')
group.add_argument('-T', '--triggerids' ,help='Triggerid(s) to find events for', type=int, nargs='+')
group.add_argument('--all-hosts', help='Find events for all hosts',action='store_true')
parser.add_argument('-n', '--numeric', help='Use numeric ids instead of names, applies to -H and -G',action='store_true')
parser.add_argument('-L', '--limit', help='Limit the number of returned lines, default is 100. Set to 0 to disable.',default=100,type=int)
group2.add_argument('-P', '--problem', help='Only show PROBLEM events', action='store_true')
group2.add_argument('-O', '--ok', help='Only show OK events', action='store_true')
parser.add_argument('-A', '--ack', help='Only show Acknowledged events', action='store_true')
parser.add_argument('-t', '--time-period', help='Timeperiod in seconds, default is one week. Set to 0 to disable.', type=int, default=604800)
group3.add_argument('-s', '--start-time', help='Unix timestamp to search from', type=int)
group3.add_argument('-f', '--follow', help='Follow events as they occur', action='store_true')
parser.add_argument('-i', '--ids', help='Output only eventids',action='store_true')
parser.add_argument('-u', '--username', help='User for the Zabbix api')
parser.add_argument('-p', '--password', help='Password for the Zabbix api user')
parser.add_argument('-a', '--api', help='Zabbix API URL')
parser.add_argument('--no-verify', help='Disables certificate validation when using a secure connection',action='store_true') 
parser.add_argument('-c','--config', help='Config file location (defaults to $HOME/.zbx.conf)')

args = parser.parse_args()

# load config module
Config = ConfigParser.ConfigParser()
Config

# if configuration argument is set, test the config file
if args.config:
 if os.path.isfile(args.config) and os.access(args.config, os.R_OK):
  Config.read(args.config)

# if not set, try default config file
else:
 if os.path.isfile(defconf) and os.access(defconf, os.R_OK):
  Config.read(defconf)

# try to load available settings from config file
try:
 username=ConfigSectionMap("Zabbix API")['username']
 password=ConfigSectionMap("Zabbix API")['password']
 api=ConfigSectionMap("Zabbix API")['api']
 noverify=bool(distutils.util.strtobool(ConfigSectionMap("Zabbix API")["no_verify"]))
except:
 pass

# override settings if they are provided as arguments
if args.username:
 username = args.username

if args.password:
 password = args.password

if args.api:
 api = args.api

if args.no_verify:
 noverify = args.no_verify

# test for needed params
if not username:
 sys.exit("Error: API User not set")

if not password:
 sys.exit("Error: API Password not set")
 
if not api:
 sys.exit("Error: API URL is not set")

# Setup Zabbix API connection
zapi = ZabbixAPI(api)

if noverify is True:
 zapi.session.verify = False

# Login to the Zabbix API
zapi.login(username, password)

##################################
# Start actual API logic
##################################

# Base API call
call={'sortfield': 'clock', 'sortorder': 'DESC', 'output': 'extend', 'source': 0}

if args.limit!=0:
        call['limit']=args.limit

if args.ids:
        call['output']='eventid'
else:
        call['output']='extend'
        call['selectHosts']='extend'
        call['selectRelatedObject']='extend'

if args.problem:
        call['value']=1
elif args.ok:
        call['value']=0

if args.ack:
        call['acknowledged']=True

if args.start_time:
        call['time_from']=args.start_time

if args.time_period!=0:
        if args.start_time:
            call['time_till']=args.start_time+args.time_period
        else:
            call['time_from']=int(time.time())-args.time_period


if args.hostgroups:
    if args.numeric:
       # We are getting numeric hostgroup ID's, let put them in a list
       # (ignore any non digit items)
       hgids=[s for s in args.hostgroups if s.isdigit()]
       for hgid in hgids:
         exists=zapi.hostgroup.exists(groupid=hgid)
         if not exists:
            sys.exit("Error: Hostgroupid "+hgid+" does not exist")

    else:
       # We are using hostgroup names, let's resolve them to ids.
       # First, get the named hostgroups via an API call
       hglookup = zapi.hostgroup.get(filter=({'name':args.hostgroups}))

       # hgids will hold the numeric hostgroup ids
       hgids = []
       for hg in range(len(hglookup)):
          # Create the list of hostgroup ids
          hgids.append(int(hglookup[hg]['groupid']))

    if len(hgids)>0:
        call['groupids']=hgids
    else:
        sys.exit("Error: No hostgroups found")

elif args.hostnames:
    if args.numeric:
       # We are getting numeric host ID's, let put them in a list
       # (ignore any non digit items)
       hids=[s for s in args.hostnames if s.isdigit()]
       for hid in hids:
         exists=zapi.host.exists(hostid=hid)
         if not exists:
            sys.exit("Error: Hostid "+hid+" does not exist")

    else:
       # We are using hostnames, let's resolve them to ids.
       # Get hosts via an API call
       hlookup=zapi.host.get(output='hostid',filter=({'host':args.hostnames}))
       hids = []
       for h in range(len(hlookup)):
          # Create the list of hostgroup ids
          hids.append(int(hglookup[h]['hostid']))

    if len(hids)>0:
        call['hostids']=hids
    else:
        sys.exit("Error: No hosts found")

elif args.triggerids:
    tids=[s for s in args.triggerids]
    if len(tids)>0:
        call['objectids']=tids
    else:
        sys.exit("Error: No triggers found")

try:
    while True: 
        events=zapi.event.get(**call)
        if events:
                if args.ids:
                        for event in sorted(events):
                            eventid=event['eventid']    
                            print(eventid)            
                else:
                    triggerids=[event['objectid'] for event in events]
                    triggers=zapi.trigger.get(triggerids=triggerids,output='extend',expandData=1,expandDescription=1,preservekeys=1,expandComment=1)
                    for event in sorted(events):
                        eventid=event['eventid']
                        etime=timestr(event['clock'])
                        hostname="<Unknown Host>"
                        trigger="<Unknown Trigger>"
                        triggerid="<Unknown Triggerid>"
                        severity="<Unknown Severity>"
                        try:
                            hostname=triggers[event['objectid']]['host']
                            trigger=triggers[event['objectid']]['description']
                            severity=severitymap(triggers[event['objectid']]['priority'])
                            triggerid=event['objectid']
                        except:
                            pass
                        state=statusmap(event['value'])
                        acked=ackmap(event['acknowledged'])
                        if acked==True:
                              acknowledged="Ack: Yes"
                        else:
                              acknowledged="Ack: No"
                        print "%s %s: %s [%s] %s [%s](%s|%s)" % (etime, hostname, state, eventid, trigger, triggerid, severity, acknowledged)
                        if args.follow:
                                sys.stdout.flush()
        if not args.follow and not events:
                sys.exit("Error: No events found.")
    
        if not args.follow:
                break
        call['eventid_from']=int(eventid)+1
        try:
                del call['time_till']
        except:
                pass
        time.sleep(5)
        
except KeyboardInterrupt:
    pass

# And we're done...
