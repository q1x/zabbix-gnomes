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
parser = argparse.ArgumentParser(formatter_class=argparse.RawDescriptionHelpFormatter,description='Tries to find triggers configured for the specified Zabbix host.', epilog="""
This program can use .ini style configuration files to retrieve the needed API connection information.
To use this type of storage, create a conf file (the default is $HOME/.zbx.conf) that contains at least the [Zabbix API] section and any of the other parameters:
       
 [Zabbix API]
 username=johndoe
 password=verysecretpassword
 api=https://zabbix.mycompany.com/path/to/zabbix/frontend/
 no_verify=true

""")
parser.add_argument('hostname', help='Hostname to find the configured triggers on')
parser.add_argument('-u', '--username', help='User for the Zabbix api')
parser.add_argument('-p', '--password', help='Password for the Zabbix api user')
parser.add_argument('-a', '--api', help='Zabbix API URL')
parser.add_argument('--no-verify', help='Disables certificate validation when using a secure connection',action='store_true') 
parser.add_argument('-c','--config', help='Config file location (defaults to $HOME/.zbx.conf)')
parser.add_argument('-n', '--numeric', help='Return numeric templateids instead of template names',action='store_true')
parser.add_argument('-e', '--extended', help='Returns triggerid, trigger value, trigger status, trigger state, trigger severity and trigger description separated by ":". See https://www.zabbix.com/documentation/2.2/manual/api/reference/trigger/object for more information.',action='store_true')
parser.add_argument('-s', '--search', help='Show only triggers with a description containing this search string')
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

# set the hostname we are looking for
host_name = args.hostname

hosts = zapi.host.get(output="extend", filter={"host": host_name})

if hosts:
   # Find linked templates
   if args.search:
      triggers = zapi.trigger.get(filter={'host':host_name},output='extend',search={'description':args.search},expandExpression=1,expandDescription=1)
   else:
      triggers = zapi.trigger.get(filter={'host':host_name},output='extend',expandExpression=1,expandDescription=1)

   if triggers:
      if args.extended:
         # print ids and descriptions
	 for trigger in triggers:
	   print(format(trigger["triggerid"])+":"+format(trigger["value"])+":"+format(trigger["status"])+":"+format(trigger["state"])+":"+format(trigger["priority"])+":"+format(trigger["description"]))
      else:
        if args.numeric:
           # print ids
	   for trigger in triggers:
	     print(format(trigger["triggerid"]))
        else:
           # print descriptions
	   for trigger in triggers:
	     print(format(trigger["description"]))
   else:
       sys.exit("Error: No triggers configured on "+ host_name)
else:
   sys.exit("Error: Could not find host "+ host_name)

# And we're done...
