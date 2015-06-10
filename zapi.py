#!/usr/bin/python
#
# import needed modules.
#
import argparse
import os
import os.path
import distutils.util
import cmd
import traceback
import sys
from pyzabbix import ZabbixAPI
import zgcore.conf as config

# set default vars
try:
 defconf = os.getenv("HOME") + "/.zbx.conf"
except:
 pass

username = ""
password = ""
api = ""
noverify = ""

# Define commandline arguments
parser = argparse.ArgumentParser(formatter_class=argparse.RawDescriptionHelpFormatter,description='Interactive Zabbix API commandline client.', epilog="""
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
args = parser.parse_args()

# if configuration argument is set, test the config file
if args.config:
 if os.path.isfile(args.config) and os.access(args.config, os.R_OK):
  config.LoadConfig(args.config)

# if not set, try default config file
else:
 if os.path.isfile(defconf) and os.access(defconf, os.R_OK):
  config.LoadConfig(defconf)

username=config.username
password=config.password
api=config.api
noverify=config.noverify

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

class zinteractive(cmd.Cmd):
    """Simple command processor example."""
    
    prompt = 'zapi: '
    intro = 'Welcome to the interactive Zabbix API client.'

    def do_z(self, line):
        "Perform API call - See https://github.com/lukecyca/pyzabbix for syntax detail.\ne.g.: z host.get(filter={\"host\": \"Zabbix Server\"})"
        call = "zapi." + line
	try:
	  result=eval(call)
	  if result:
	   print(result)
	  else:
	   print("No data.")
        except:
          print("Error: API syntax incorrect?")
	  traceback.print_exc(file=sys.stdout)


    def do_exit(self, line):
        "Exit the API client."
        return True

if __name__ == '__main__':
    zinteractive().cmdloop()


# And we're done...
