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
            time=datetime.utcfromtimestamp(int(timestamp)).strftime('%Y-%m-%d %H:%M:%S (UTC)')
            return time

# Zabbix severity mapper
def severitymap(level):
    level=int(level)
    if level<6:
            map=['Not Classified','Information','Warning','Average','High','Disaster']
            color=['white','white','yellow','yellow','red','red']
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

def get_terminal_size(fd=1):
    """
    Returns height and width of current terminal. First tries to get
    size via termios.TIOCGWINSZ, then from environment. Defaults to 25
    lines x 80 columns if both methods fail.

    :param fd: file descriptor (default: 1=stdout)
    """
    try:
        import fcntl, termios, struct
        hw = struct.unpack('hh', fcntl.ioctl(fd, termios.TIOCGWINSZ, '1234'))
    except:
        try:
            hw = (os.environ['LINES'], os.environ['COLUMNS'])
        except:  
            hw = (25, 80)

    return hw

def get_terminal_height(fd=1):
    """
    Returns height of terminal if it is a tty, 999 otherwise

    :param fd: file descriptor (default: 1=stdout)
    """
    if os.isatty(fd):
        height = get_terminal_size(fd)[0]
    else:
        height = 999
   
    return height

def get_terminal_width(fd=1):
    """
    Returns width of terminal if it is a tty, 999 otherwise

    :param fd: file descriptor (default: 1=stdout)
    """
    if os.isatty(fd):
        width = get_terminal_size(fd)[1]
    else:
        width = 999

    return width

def blockprint(prefix,message):
    preferredWidth=get_terminal_width()
    wrapper = textwrap.TextWrapper(initial_indent=prefix, width=preferredWidth,subsequent_indent=' '*len(prefix))
    print wrapper.fill(message)

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
parser = argparse.ArgumentParser(formatter_class=argparse.RawDescriptionHelpFormatter,description='Gets event details for Zabbix events. If the termcolor module is found, it is used to generate colored output.', epilog="""
This program can use .ini style configuration files to retrieve the needed API connection information.
To use this type of storage, create a conf file (the default is $HOME/.zbx.conf) that contains at least the [Zabbix API] section and any of the other parameters:
       
 [Zabbix API]
 username=johndoe
 password=verysecretpassword
 api=https://zabbix.mycompany.com/path/to/zabbix/frontend/
 no_verify=true

""")

parser.add_argument('eventids', help='Events to display details for', type=int, nargs='+')
parser.add_argument('-s', '--short', help='Display events in short format (one line per event)',action='store_true')
parser.add_argument('-A', '--acks', help='Display acknowledges (ignored when using short format)',action='store_true')
parser.add_argument('-L', '--alerts', help='Display alert actions (ignored when using short format)',action='store_true')
parser.add_argument('-C', '--comments', help='Display comments (ignored when using short format)',action='store_true')
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

eventids=args.eventids
call={'eventids': eventids,'sortfield': 'clock', 'sortorder': 'ASC', 'output': 'extend'}
if args.alerts:
   call["select_alerts"]='extend'
if args.acks:
   call["select_acknowledges"]='extend'

events=zapi.event.get(**call)
if events:
        triggerids=[event['objectid'] for event in events]
        triggers=zapi.trigger.get(triggerids=triggerids,output='extend',expandDescription=1,preservekeys=1,expandComment=1,selectHosts='extend')
        for event in events:
                eventid=event['eventid']
                time=timestr(event['clock'])
                state=statusmap(event['value'])
                acked=ackmap(event['acknowledged'])
                hostname="<Unknown Host>"
                trigger="<Unknown Trigger>"
                triggerid="<Unknown Triggerid>"
                severity="<Unknown Severity>"
                try:
                    hostname=triggers[event['objectid']]['hosts'][0]['host']
                    severity=severitymap(triggers[event['objectid']]['priority'])
                    trigger=triggers[event['objectid']]['description']
                    triggerid=event['objectid']
                except:
                    pass
                if args.short:
                    if acked==True:
                            acknowledged="Ack: Yes"
                    else:
                            acknowledged="Ack: No"
                    print "%s %s: %s [%s] %s [%s](%s|%s)" % (time, hostname, state, eventid, trigger, triggerid, severity, acknowledged)
                else:
                    if acked==True:
                        acknowledged='Acknowledged'
                    else:
                        acknowledged='Not Acknowledged'

                    print "== EVENT [%s] ==\n" % (eventid)
                    blockprint("  Status   : ",state)
                    blockprint("  Severity : ",severity)
                    blockprint("  Time     : ",time)
                    blockprint("  Host     : ",hostname)
                    blockprint("  Trigger  : ",trigger)
                    blockprint("  TriggerID: ",triggerid)
                    blockprint("  Ack'ed   : ",acknowledged)
                    print

                    if args.comments:
                        comments=triggers[event['objectid']]['comments']
                        if len(comments)==0:
                           comments="N/A"
                        blockprint("  Comments : ",comments)
                        print

                    if args.acks:
                        print "  -- Acknowledges --"
                        acks=event['acknowledges']
                        if len(acks)>0:
                                for ack in acks:
                                        print ack
                                        user=ack['name'] + " " + ack['surname'] + " (" + ack['alias'] + ")"
                                        blockprint("  Time     : ",timestr(ack['clock']))
                                        blockprint("  AckID    : ",ack['acknowledgeid'])
                                        blockprint("  User     : ",user)
                                        blockprint("  Message  : ",ack['message'])
                                                                
                                        print
                        else:
                                print "  N/A\n"

                    if args.alerts:
                        print "  -- Alert Actions --"
                        alerts=event['alerts']
                        if len(alerts)>0:
                                for alert in alerts:
                                        blockprint("  Step     : ",alert['esc_step'])
                                        blockprint("  Time     : ",timestr(alert['clock']))
                                        blockprint("  Type     : ",alerttypemap(alert['alerttype']))
                                        blockprint("  AlertID  : ",alert['alertid'])
                                        blockprint("  Status   : ",alertstatusmap(alert['status'],alert['alerttype']))
                                        if int(alert['alerttype'])==0:
                                               blockprint("  Sent to  : ",alert['sendto'])
                                               blockprint("  Subject  : ",alert['subject'])
                                               blockprint("  Message  : ",alert['message'])
                                        print
                        else:
                                print "  N/A\n"
else:
        sys.exit("Error: No events found.")
                        

# And we're done...
