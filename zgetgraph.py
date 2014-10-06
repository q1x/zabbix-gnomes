#!/usr/bin/python
#
# import needed modules.
# pyzabbix is needed, see https://github.com/lukecyca/pyzabbix
#
# Pillow is also needed, see https://github.com/python-pillow/Pillow
#
#
import argparse
import ConfigParser
import os
import os.path
import distutils.util
import requests
import time
import sys
from cStringIO import StringIO
from PIL import Image
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
parser = argparse.ArgumentParser(formatter_class=argparse.RawDescriptionHelpFormatter,description='Downloads a graph from Zabbix frontend', epilog="""
This program can use .ini style configuration files to retrieve the needed API connection information.
To use this type of storage, create a conf file (the default is $HOME/.zbx.conf) that contains at least the [Zabbix API] section and any of the other parameters:
       
 [Zabbix API]
 username=johndoe
 password=verysecretpassword
 api=https://zabbix.mycompany.com/path/to/zabbix/frontend/
 no_verify=true

""")
parser.add_argument('graphid', help='The graph that we are going to download')
parser.add_argument('-f', '--filename', required=True, help='filename to save the graph to')
parser.add_argument('-u', '--username', help='User for the Zabbix api and frontend')
parser.add_argument('-p', '--password', help='Password for the Zabbix user')
parser.add_argument('-a', '--api', help='Zabbix URL')
parser.add_argument('--no-verify', help='Disables certificate validation when using a secure connection',action='store_true') 
parser.add_argument('-c','--config', help='Config file location (defaults to $HOME/.zbx.conf)')
parser.add_argument('-t', '--timeperiod', type=int, default=3600, help='Timeperiod for the graph in seconds (defaults to 3600)')
parser.add_argument('-s', '--starttime', type=int, help='Starting time for the graph in seconds from Unix Epoch')
parser.add_argument('-W', '--width', type=int, help='Width of the graph (defaults to the graph default)')
parser.add_argument('-H', '--height', type=int, help='Height of the graph (defaults to the graph default)')
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
graphid = args.graphid

# Find graph from API
graph = zapi.graph.get(output="extend", graphids=graphid)

if graph:
  #print(format(graph))
  # Set width and height
  if args.width:
    width = args.width
  else:
    width = graph[0]['width']
  if args.height:
    height = args.height
  else:
    height = graph[0]['height']

  # Select the right graph generator according to graph type
  # type 3 = Exploded graph
  if graph[0]['graphtype'] == "3":
    generator = "chart6.php"
  # type 2 = Pie graph
  elif graph[0]['graphtype'] == "2":
    generator = "chart6.php"
  # type 1 = Stacked graph
  elif graph[0]['graphtype'] == "1":
    generator = "chart2.php"
  # type 0 = Normal graph
  elif graph[0]['graphtype'] == "0":
    generator = "chart2.php"
  # catch-all in case someone invents a new type/generator
  else:
    generator = "chart2.php"

  # Set time period
  period = args.timeperiod

  # set the starting time for the graph
  if args.starttime:
    stime=args.starttime
  else:
     stime=time.time()-period

  # Set login URL for the Frontend (frontend access is needed, as we cannot retrieve graph images via the API)
  loginurl = api + "/index.php"
  # Data that needs to be posted to the Frontend to log in
  logindata = {'autologin' : '1', 'name' : username, 'password' : password, 'enter' : 'Sign in'}
  # We need to fool the frontend into thinking we are a real browser
  headers = {'User-Agent' : 'Mozilla/5.0 (Windows NT 5.1; rv:31.0) Gecko/20100101 Firefox/31.0', 'Content-type' : 'application/x-www-form-urlencoded'}

  # setup a session object so we can reuse session cookies
  session=requests.session()

  # Login to the frontend
  login=session.post(loginurl, params=logindata, headers=headers) 

  # See if we logged in successfully
  try:
    if session.cookies['zbx_sessionid']:

       # Build the request for the graph
       graphurl = api + "/" + generator + "?graphid=" + str(graphid) + "&period=" + str(period) + "&width=" + str(width) + "&height=" + str(height) + "&stime=" + str(stime)

       # get the graph
       graphreq = session.get(graphurl)

       # read the data as an image
       graphpng = Image.open(StringIO(graphreq.content))

       # and write it to file
       graphpng.save(args.filename)

  except:
       sys.exit("Error: Could not log in to retrieve graph")
else:
    sys.exit("Error: Could not find graphid "+ graphid)

# And we're done...
