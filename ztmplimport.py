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
from xml.etree import ElementTree as ET
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

def PrintError(error):
    if args.continue_on_error:
	sys.stderr.write(error + '\n')
    else:
        sys.exit(error)

# set default vars
defconf = os.getenv("HOME") + "/.zbx.conf"
username = ""
password = ""
api = ""
noverify = ""

# Define commandline arguments
parser = argparse.ArgumentParser(formatter_class=argparse.RawDescriptionHelpFormatter,description='Imports Zabbix templates from XML files. Default behaviour is to add missing elements and update any existing elements. Optionally elements that are missing from the XML file can be removed from existing template(s) as well.', epilog="""
This program can use .ini style configuration files to retrieve the needed API connection information.
To use this type of storage, create a conf file (the default is $HOME/.zbx.conf) that contains at least the [Zabbix API] section and any of the other parameters:
       
 [Zabbix API]
 username=johndoe
 password=verysecretpassword
 api=https://zabbix.mycompany.com/path/to/zabbix/frontend/
 no_verify=true

""")
parser.add_argument('-u', '--username', help='User for the Zabbix api')
parser.add_argument('-p', '--password', help='Password for the Zabbix api user')
parser.add_argument('-a', '--api', help='Zabbix API URL')
parser.add_argument('--no-verify', help='Disables certificate validation when using a secure connection',action='store_true') 
parser.add_argument('-c','--config', help='Config file location (defaults to $HOME/.zbx.conf)')
parser.add_argument('-v', '--verbose', help='Enables verbose output.',action='store_true') 
parser.add_argument('-T', '--templates', help='List of XML template files to import.',required=True, nargs="+")
parser.add_argument('-D', '--delete-missing', help='If a template already exists in Zabbix, any missing elements from the .XML will be removed from Zabbix as well.',action='store_true')
parser.add_argument('-U', '--update', help='If a template already exists in Zabbix, update any changes in template elements.',action='store_true')
parser.add_argument('-C', '--continue-on-error', help='Continue on error, use with caution.',action='store_true')

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

# We need the API version to know if valuemap importing is supported
zversion=zapi.apiinfo.version()

# set import modes
create=True
if args.update:
   update=True
else:
   update=False

if args.delete_missing:
   delete=True
else:
   delete=False

# set import rules, see https://www.zabbix.com/documentation/3.0/manual/api/reference/configuration/import
rules={}
rules['templates']={'createMissing': create, 'updateExisting':update}
rules['applications']={'createMissing': create, 'deleteMissing': delete}
rules['discoveryRules']={'createMissing': create, 'updateExisting': update, 'deleteMissing': delete}
rules['graphs']={'createMissing': create, 'updateExisting':update, 'deleteMissing': delete}
rules['groups']={'createMissing': create}
rules['items']={'createMissing': create, 'updateExisting':update, 'deleteMissing': delete}
rules['templateLinkage']={'createMissing': create}
rules['templateScreens']={'createMissing': create, 'updateExisting':update, 'deleteMissing': delete}
rules['triggers']={'createMissing': create, 'updateExisting':update, 'deleteMissing': delete}
# Valuemap imports are a Zabbix 3.x.x feature
if zversion.startswith('3.'):
    rules['valueMaps']={'createMissing':create, 'updateExisting':update}

# Parse file list 
for template in args.templates:
    Continue=True
    if Continue:
        try:
            # open file for reading
            with file(template) as f:
             	xml = f.read()
            	f.close()
    	except:
            # If the file can't be opened, exit with error
    	    error="Error: Something went wrong when trying to read the file" + template
	    PrintError(error)
            Continue=False

    if Continue:
    	try:
            # verify if the file is a valid XML        
            tree = ET.fromstring(xml)
    	except:
            # If the file can't isn't a valid XML, exit with error
            error="Error: XML is not valid in " + template
            PrintError(error)
	    Continue=False

    if Continue:
        try:
            # Everything looks good, let's try to import
            result=zapi.configuration.Import(format="xml",rules=rules, source=xml)
            if args.verbose:
                print("Succesfully imported " + template)
        except:
            # Something went wrong with the API call or import
            error="Error: Something went wrong while importing " + template + "\n" + str(sys.exc_info()[1][0])
	    PrintError(error)
            Continue=False

# And we're done...
