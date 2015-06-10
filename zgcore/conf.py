#
# Zabbix Gnomes Configuration File Handler
#

import argparse
import ConfigParser
import logging
import os
import sys

def LoadArgs():
    True

# LoadConfig will load the config from file and set global variables accordingly
# Returns True if file could be read, False otherwise
def LoadConfig(cfgfile):

    # We want to modify vars globally and define them beforehand
    # so that they are known in the namespace
    global api; api=None
    global delim; delim=None
    global header; header=None
    global noverify; noverify=None
    global password; password=None
    global username; username=None
    global wrap; wrap=None

    # Helper function to load a config file option
    # Will set the value to None if the option was not found
    def LoadVar(varname,section,bool=None):
        if bool:
           try:
              value=Config.getboolean(section,varname)
           except:
              value=None
        else:
           try:
              value=Config.get(section,varname)
           except:
              value=None
        return value

    # Initialize the ConfigParser
    Config=ConfigParser.ConfigParser()
    Config
 
    # Read the config if file is readable
    if os.path.isfile(cfgfile) and os.access(cfgfile, os.R_OK):
        Config.read(cfgfile)
        api=LoadVar('api','Zabbix API')
        delim=LoadVar('delim','Output')
        header=LoadVar('header','Output',bool=True)
        noverify=LoadVar('no_verify','Zabbix API',bool=True)
        password=LoadVar('password','Zabbix API')
        username=LoadVar('username','Zabbix API')
        wrap=LoadVar('wrap','Output')
	return True
    else:
        return False 
      
