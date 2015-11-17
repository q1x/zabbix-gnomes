#!/usr/bin/env python
#
# import needed modules.
# pyzabbix is needed, see https://github.com/lukecyca/pyzabbix
#
import argparse
import ConfigParser
import os
import os.path
import distutils.util
import cmd
import traceback
import sys
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
parser = argparse.ArgumentParser(formatter_class=argparse.RawDescriptionHelpFormatter,description='Deletes Zabbix hostgroups.', epilog="""
This program can use .ini style configuration files to retrieve the needed API connection information.
To use this type of storage, create a conf file (the default is $HOME/.zbx.conf) that contains at least the [Zabbix API] section and any of the other parameters:
       
 [Zabbix API]
 username=johndoe
 password=verysecretpassword
 api=https://zabbix.mycompany.com/path/to/zabbix/frontend/
 no_verify=true

""")
parser.add_argument('hostgroup',help='List of hostgroups to delete',nargs='+')
parser.add_argument('-N', '--non-empty',help='Also delete non-empty groups',action='store_true')
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
 print("Error: API User not set")
 exit()

if not password:
 print("Error: API Password not set")
 exit()
 
if not api:
 print("Error: API URL is not set")
 exit()

# Setup Zabbix API connection
zapi = ZabbixAPI(api)

if noverify is True:
 zapi.session.verify = False

# Login to the Zabbix API
print("Logging in on '" + api + "' with user '" + username +"'.")
zapi.login(username, password)

##################################
# Start actual API logic
##################################
groupids=[]

# find groupids for the hostgroup names
search=zapi.hostgroup.get(selectHosts='count', filter={'name': args.hostgroup})
if search:
        for group in search:
            # Only delete empty groups
            if group['hosts']==0:
                    groupids.append(group['groupid'])
            # Unless specified otherwise        
            elif args.non_empty:
                    groupids.append(group['groupid'])

if len(groupids)>0:
        #somehow passing a list doesn't work, looping over the groupids as a workaround
        for groupid in groupids:
            result=zapi.hostgroup.delete(groupid)
else:
        sys.exit("Error: No hostgroups to delete")

# And we're done...
