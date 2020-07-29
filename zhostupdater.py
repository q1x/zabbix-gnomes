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
parser = argparse.ArgumentParser(formatter_class=argparse.RawDescriptionHelpFormatter,description='Updates properties of a Zabbix host.', epilog="""
This program can use .ini style configuration files to retrieve the needed API connection information.
To use this type of storage, create a conf file (the default is $HOME/.zbx.conf) that contains at least the [Zabbix API] section and any of the other parameters:

 [Zabbix API]
 username=johndoe
 password=verysecretpassword
 api=https://zabbix.mycompany.com/path/to/zabbix/frontend/
 no_verify=true

""")
group = parser.add_mutually_exclusive_group()
group2 = parser.add_mutually_exclusive_group()
group3 = parser.add_mutually_exclusive_group()
group4 = parser.add_mutually_exclusive_group()
parser.add_argument('host', help='Host to update in zabbix')
parser.add_argument('-u', '--username', help='User for the Zabbix api')
parser.add_argument('-p', '--password', help='Password for the Zabbix api user')
parser.add_argument('-a', '--api', help='Zabbix API URL')
parser.add_argument('--no-verify', help='Disables certificate validation when using a secure connection',action='store_true') 
parser.add_argument('-c','--config', help='Config file location (defaults to $HOME/.zbx.conf)')
parser.add_argument('-N', '--name', help='Update hostname')
parser.add_argument('-n', '--numeric', help='Provide a host ID instead of a name', action='store_true')
group.add_argument('-V', '--visible-name', help='Update visible name')
group.add_argument('-S', '--sync-names', help='Sets hostname and visible name to the name specified with -N',action='store_true')
parser.add_argument('-I', '--inventory', help='Update inventory fields. Specify each field as \'fieldname="value"\'.', nargs='+')
group2.add_argument('-M', '--macros', help='Update or add macros. Specify each field as \'"macro"="value"\'. Don\'t add {$...} characters, this script will handle that for you.', nargs='+')
group2.add_argument('-R', '--remove-macros', help='Remove macros. Don\'t add {$...} characters, this script will handle that for you.', nargs='+')
group3.add_argument('-E', '--enable', help='Set the host to \'Monitored\'',action='store_true')
group3.add_argument('-D', '--disable', help='Set the host to \'Not monitored\'',action='store_true')
group4.add_argument('-G', '--groups', help='Add host to hostgroups', nargs='+')
group4.add_argument('-r', '--remove-groups', help='Remove host from hostgroups', nargs='+')
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

# Find the host we are looking for
host_name = args.host

# setup call dict
call={}

if host_name: 
    if args.numeric:
        filterField = "hostid"
    else:
        filterField = "host"
    # Find matching hosts
    hosts = zapi.host.get(output="extend", selectGroups="extend", selectMacros="extend", filter={filterField:host_name}) 
    if hosts:
      # Basic API call params
      call["hostid"]=hosts[0]["hostid"]
      # Current raw list of macros for the host
      curmac=hosts[0]["macros"]
      # Current list of groups for the host
      curgrp=hosts[0]["groups"]


      # Set names if specified
      if args.name:
              call["host"]=args.name
              if args.sync_names:
                     call["name"]=args.name
      elif args.visible_name:
              call["name"]=args.visible_name
      elif args.sync_names:
              call["name"]=args.host

      # update inventory fields
      if args.inventory:
              zbxinv={}
              for field in args.inventory:
                      if '=' in field:
                              field=field.split('=')
                              zbxinv[field[0]]=field[1]
                      else:
                              sys.exit("Error: Inventory \""+ field + "\" is not valid")
              call["inventory"]=zbxinv 

      # update or add macros
      if args.macros:
              zbxmac=[]
              for field in args.macros:
                      if '=' in field:
                             # Create macro object with proper value
                             field=field.split('=')
                             if ':' in field[0]:
                                   # context-macro contains ':', only uppercase macro name
                                   name=unicode("{$" + field[0].split(':')[0].upper() + ':' + field[0].split(':')[1] + "}")
                             else:
                                   name=unicode("{$" + field[0].upper() + "}")
                             value=unicode(field[1])
                             macro={"macro":name,"value":value}
                             zbxmac.append(macro)
                      else:
                             sys.exit("Error: Macro \""+ field + "\" is not valid")

              # Itterate over the current macros and append them to the list, unless we just added an updated value
              for line in curmac:
                      name=line['macro']
                      value=line['value']
                      macro={"macro":name,"value":value}
                      if not any(check.get('macro', None) == name for check in zbxmac): 
                             zbxmac.append(macro)
      elif args.remove_macros:
              zbxmac=[]
              remmac=[]
              # Create a list of macros to be removed
              for field in args.remove_macros:
                      # find macro name
                      name=unicode("{$" + field.upper() + "}")
                      macro={"macro":name}
                      remmac.append(macro)

              # itterate over the current macros and append them to the list, unless the macro is listed in the macros to be removed
              for line in curmac:
                      name=line['macro']
                      value=line['value']
                      macro={"macro":name,"value":value}
                      if not any(check.get('macro', None) == name for check in remmac): 
                             zbxmac.append(macro)

      # Add macros to the API call if defined
      try:
              if zbxmac:
                      call["macros"]=zbxmac 
      except:
              pass

      # Set host status
      if args.enable:
              call["status"]=0
      elif args.disable:
              call["status"]=1


      # add or remove host groups
      if args.groups:
              zbxgrp=[]
              for field in args.groups:
                      getgroup=zapi.hostgroup.get(filter={'name':field})
                      if getgroup:
                              groupid=getgroup[0]['groupid']
                              group={u'name':unicode(field), u'groupid':groupid}
                              zbxgrp.append(group)
                      else:
                              sys.exit("Error: Could not find hostgroup \""+ field + "\"")

              # Itterate over the current groups and append them to the list, unless we just added an updated value
              for line in curgrp:
                      group={u"name":line['name'],u"groupid":line['groupid']}
                      if group not in zbxgrp: 
                             zbxgrp.append(group)

      elif args.remove_groups:
              zbxgrp=[]
              remgrp=[]
              # Create a list of groups to be removed
              for field in args.remove_groups:
                      name=unicode(field)
                      group={u'name':name}
                      remgrp.append(group)

              # itterate over the current groups and append them to the list, unless the group is listed in the groups to be removed
              for line in curgrp:
                      name=line['name']
                      groupid=line['groupid']
                      group={u"name":name,u"groupid":groupid}
                      if not any(check.get('name', None) == name for check in remgrp): 
                              zbxgrp.append(group)

      # Add groups to the API call if defined
      try:
    	     if zbxgrp:
                      call["groups"]=zbxgrp 
      except:
             pass

    else:
            sys.exit("Error: Could not find host \""+ host_name + "\"")

    # Perform API call
    try:
            result=zapi.host.update(**call)
    except:
            sys.exit("Error: Host \""+ host_name + "\" could not be updated")

    if result['hostids'][0] != hosts[0]["hostid"]:
            sys.exit("Error: Host \""+ host_name + "\" could not be updated")

else:
        sys.exit("Error: No hosts to find")
# And we're done...
