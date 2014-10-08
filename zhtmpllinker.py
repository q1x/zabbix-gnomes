#!/usr/bin/python
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
from pyzabbix import ZabbixAPI

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


# set default vars
defconf = os.getenv("HOME") + "/.zbx.conf"
username = ""
password = ""
api = ""
noverify = ""

# Define commandline arguments
parser = argparse.ArgumentParser(formatter_class=argparse.RawDescriptionHelpFormatter,description='Tries to link Zabbix hosts to the specified templates. Hosts can be specified seperately or by hostgroups.', epilog="""
This program can use .ini style configuration files to retrieve the needed API connection information.
To use this type of storage, create a conf file (the default is $HOME/.zbx.conf) that contains at least the [Zabbix API] section and any of the other parameters:
       
 [Zabbix API]
 username=johndoe
 password=verysecretpassword
 api=https://zabbix.mycompany.com/path/to/zabbix/frontend/
 no_verify=true

""")

group = parser.add_mutually_exclusive_group(required=True)
group.add_argument('-H', '--hostnames' ,help='Hostname(s) to link to template(s) to', nargs='+')
group.add_argument('-G', '--hostgroups' ,help='Link all the hosts in the specified hostgroup(s) to the template(s)', nargs='+')
parser.add_argument('-t', '--templates', help='Template(s) to link the host(s) to', nargs='+', required=True)
parser.add_argument('-u', '--username', help='User for the Zabbix api')
parser.add_argument('-p', '--password', help='Password for the Zabbix api user')
parser.add_argument('-a', '--api', help='Zabbix API URL')
parser.add_argument('--no-verify', help='Disables certificate validation when using a secure connection',action='store_true') 
parser.add_argument('-c','--config', help='Config file location (defaults to $HOME/.zbx.conf)')
parser.add_argument('-n', '--numeric', help='Use numeric ids instead of names, applies to -t, -H and -G',action='store_true')
parser.add_argument('-e', '--extended', help='Extended output',action='store_true')

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

  # Now that we have resolved the hostgroup ids, we can make an API call to retrieve the member hosts
  hlookup=zapi.host.get(output=['hostid'],groupids=hgids)

elif args.hostnames:
  if args.numeric:
     # We are getting numeric host ID's, let put them in a list
     # (ignore any non digit items)
     hids=[s for s in args.hostnames if s.isdigit()]  
     hlookup = []
     for hid in hids:
       exists=zapi.host.exists(hostid=hid)
       if not exists:
          sys.exit("Error: Hostid "+hid+" does not exist")
       if not hlookup:
          hlookup = [{unicode('hostid'): unicode(hid)}]
       else:
          hlookup.append({unicode('hostid'): unicode(hid)})

  else:
     # We are using hostnames, let's resolve them to ids.
     # Get hosts via an API call
     hlookup = zapi.host.get(filter=({'host':args.hostnames}))  

else:
  #uhm... what were we supposed to do?
  sys.exit("Error: Nothing to do here")

if not hlookup:
 sys.exit("Error: No hosts found")

if args.numeric:
   # We are getting numeric template ID's, let put them in a list
   # (ignore any non digit items)
   tids=[s for s in args.templates if s.isdigit()]  
   tlookup=[]
   for tid in tids:
     exists=zapi.template.exists(hostid=tid)
     if not exists:
        sys.exit("Error: Templateid "+tid+" does not exist")
     if not tlookup:
        tlookup = [{unicode('templateid'): unicode(tid)}]
     else:
       tlookup.append({unicode('templateid'): unicode(tid)})

else:
   # We are using template names, let's resolve them to ids.
   # Get templates via an API call
   tlookup = zapi.template.get(filter=({'host':args.templates}))  

try:
 # Apply the linkage
 result=zapi.host.massadd(hosts=hlookup,templates=tlookup)
except:
 sys.exit("Error: Something went wrong while performing the update")

 # Print extended output
if args.extended:
  hosts=zapi.host.get(output='extend',hostids=result['hostids'])
  hostnames=""
  for host in range(len(hosts)):
      if not hostnames:
        hostnames = str(hosts[host]['host'])
      else:
        hostnames = hostnames + ", " + str(hosts[host]['host'])
  print("Link to templates (" + str(len(tlookup)) + ") applied to: " + hostnames)

# And we're done...
