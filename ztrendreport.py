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
import csv, codecs, cStringIO
import time
from datetime import datetime, date, timedelta
from pyzabbix import ZabbixAPI
from pprint import pprint

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

class UTF8Recoder:
    """
    Iterator that reads an encoded stream and reencodes the input to UTF-8
    """
    def __init__(self, f, encoding):
        self.reader = codecs.getreader(encoding)(f)

    def __iter__(self):
        return self

    def next(self):
        return self.reader.next().encode("utf-8")

class UnicodeReader:
    """
    A CSV reader which will iterate over lines in the CSV file "f",
    which is encoded in the given encoding.
    """

    def __init__(self, f, dialect=csv.excel, encoding="utf-8", **kwds):
        f = UTF8Recoder(f, encoding)
        self.reader = csv.reader(f, dialect=dialect, **kwds)

    def next(self):
        row = self.reader.next()
        return [unicode(s, "utf-8") for s in row]

    def __iter__(self):
        return self

class UnicodeWriter:
    """
    A CSV writer which will write rows to CSV file "f",
    which is encoded in the given encoding.
    """

    def __init__(self, f, dialect=csv.excel, encoding="utf-8", **kwds):
        # Redirect output to a queue
        self.queue = cStringIO.StringIO()
        self.writer = csv.writer(self.queue, dialect=dialect, **kwds)
        self.stream = f
        self.encoder = codecs.getincrementalencoder(encoding)()

    def writerow(self, row):
        self.writer.writerow([s.encode("utf-8") for s in row])
        # Fetch UTF-8 output from the queue ...
        data = self.queue.getvalue()
        data = data.decode("utf-8")
        # ... and reencode it into the target encoding
        data = self.encoder.encode(data)
        # write to the target stream
        self.stream.write(data)
        # empty queue
        self.queue.truncate(0)

    def writerows(self, rows):
        for row in rows:
            self.writerow(row)

def valid_date(s):
    try:
        return datetime.strptime(s, "%Y-%m-%d")
    except ValueError:
        msg = "Not a valid date: '{0}'.".format(s)
        raise argparse.ArgumentTypeError(msg)

# set default vars
defconf = os.getenv("HOME") + "/.zbx.conf"
username = ""
password = ""
api = ""
noverify = ""

# Define commandline arguments
parser = argparse.ArgumentParser(formatter_class=argparse.RawDescriptionHelpFormatter,description='Prints a CSV trend report for daily max, min or average values for the specified item key.', epilog="""
This program can use .ini style configuration files to retrieve the needed API connection information.
To use this type of storage, create a conf file (the default is $HOME/.zbx.conf) that contains at least the [Zabbix API] section and any of the other parameters:

 [Zabbix API]
 username=johndoe
 password=verysecretpassword
 api=https://zabbix.mycompany.com/path/to/zabbix/frontend/
 no_verify=true

""")

group = parser.add_mutually_exclusive_group(required=True)
group2 = parser.add_mutually_exclusive_group(required=True)
group.add_argument('-H', '--hostnames' ,help='Hostname(s) to find trend data for', nargs='+')
group.add_argument('-G', '--hostgroups' ,help='Find matching trend data for all hosts in these hostgroup(s)', nargs='+')
group.add_argument('--all-hosts', help='Find trend data for *ALL* hosts, use with caution',action='store_true')
parser.add_argument('-u', '--username', help='User for the Zabbix api')
parser.add_argument('-p', '--password', help='Password for the Zabbix api user')
parser.add_argument('-a', '--api', help='Zabbix API URL')
parser.add_argument('--no-verify', help='Disables certificate validation when nventory_mode using a secure connection',action='store_true')
parser.add_argument('-c','--config', help='Config file location (defaults to $HOME/.zbx.conf)')
parser.add_argument('-n', '--numeric', help='Use numeric ids instead of names, applies to -H and -G',action='store_true')
parser.add_argument('-k', '--key', help='Item key search string', required=True)
parser.add_argument('--start', help='Start date (mandatory) - format YYYY-MM-DD',type=valid_date,required=True)
parser.add_argument('--end', help='End date (optional) - format YYYY-MM-DD',type=valid_date,required=False)
group2.add_argument('--min', help='List minimal value per day',action='store_true')
group2.add_argument('--max', help='List maximal value per day',action='store_true')
group2.add_argument('--avg', help='List average value per day',action='store_true')
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
zapi.timeout=900
##################################
# Start actual API logic
##################################

# Figure out which days to parse
datelist = []
if args.end:
    datedelta = args.end - args.start
    for day in range(datedelta.days + 1):
        datelist.append(args.start + timedelta(days=day))
else:
    datelist.append(args.start)

periodstart = datetime(year=datelist[0].year,
                    month=datelist[0].month,
                    day=datelist[0].day,
                    hour=0,
                    minute=0,
                    second=0).strftime("%s")
periodend = datetime(year=datelist[-1].year,
                    month=datelist[-1].month,
                    day=datelist[-1].day,
                    hour=0,
                    minute=0,
                    second=0).strftime("%s")


if args.all_hosts:
       # Make a list of all hosts
       hlookup = zapi.host.get()
else:
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
    hlookup=zapi.host.get(output=['hostid'],monitored_hosts=True,groupids=hgids)

  elif args.hostnames:
    if args.numeric:
       # We are getting numeric host ID's, let put them in a list
       # (ignore any non digit items)
       hids=[s for s in args.hostnames if s.isdigit()]
       hlookup=zapi.host.get(output=['hostid'],hostids=hids)

    else:
       # We are using hostnames, let's resolve them to ids.
       # Get hosts via an API call

       hlookup=zapi.host.get(output=['hostid'],monitored_hosts=True,filter=({'host':args.hostnames}))

  else:
     #uhm... what were we supposed to do?
     sys.exit("Error: Nothing to do here")

if not hlookup:
     sys.exit("Error: No hosts found")


# Convert hlookup to a usable parameter for item.get
hostids = []
for dict in hlookup:
    for key, value in dict.iteritems():
        hostids.append(value)

# Find items and their parent hosts based on the key
items = zapi.item.get(hostids=hostids,output=['itemid','value_type','units'],search={'key_':args.key}, monitored=True, selectHosts=['name','host'])
if items:
    # Sort on hostname
    items = sorted(items, key=lambda k: k['hosts'][0]['name'])
    if args.max:
        findvals = 'value_max'
    elif args.min:
        findvals = 'value_min'
    elif args.avg:
        findvals = 'value_avg'

    header=['name','host'] # CSV header
    for day in datelist:
        header.append(day.strftime("%Y-%m-%d")) # append each day

    # Output the result in CSV format on stdout
    output = UnicodeWriter(sys.stdout, delimiter=',', quotechar='"', quoting=csv.QUOTE_ALL)
    output.writerow(header)

    for item in items:
        row = [item['hosts'][0]['name'],item['hosts'][0]['host']]
        trends = None
        trends = zapi.trend.get(itemids=item['itemid'],output=['clock',findvals],time_from=periodstart,time_till=periodend)
        for day in datelist:
            endval = ""
            vals = []
            daystart = datetime(year=day.year,
                                month=day.month,
                                day=day.day,
                                hour=0,
                                minute=0,
                                second=0).strftime("%s")
            dayend = datetime(year=day.year,
                              month=day.month,
                              day=day.day,
                              hour=23,
                              minute=59,
                              second=5).strftime("%s")
            if trends:
                for trend in (trend for trend in trends if trend['clock'] >= daystart and trend['clock'] <= dayend): # Filter values per day
                    if int(item['value_type']) == 0: # floats
                        vals.append(float(trend[findvals]))
                    elif int(item['value_type']) == 3: # ints
                        vals.append(int(trend[findvals]))
                if args.max and vals:
                    endval = max(vals)
                elif args.min and vals:
                    endval = min(vals)
                elif args.avg and vals:
                    if int(item['value_type']) == 0: # floats
                        endval = float(sum(vals) / max(len(vals), 1))
                    elif int(item['value_type']) == 3: # ints
                        endval = int(sum(vals) / max(len(vals), 1))
            row.append(str(endval))
        output.writerow(row)
    sys.stdout.close()

else:
    sys.exit("Error: no matching items found.")
