zabbix-gnomes
=============

A collection of various scripts to automate tasks with the Zabbix API. My main goal is to create a set of simple utilities that can be reused in shell scripts without using a lot of curl voodoo.


API tools:
----------
- zapi.py -		Interactive Zabbix API client.

Graph related:
--------------
- zhgraphfinder.py - 	Finds graphs configured on a Zabbix host
- zgetgraph.py - 	Downloads a graph .PNG from the Zabbix frontend and saves it.

Proxy related:
--------------
- zproxyfinder.py -	Finds configured proxy for a Zabbix host

Template related:
-----------------
- zhtmplfinder.py - 	Finds linked templates for a Zabbix host
- zthostfinder.py - 	Finds hosts that are linked to a template


Configuration
-------------
These programs can use .ini style configuration files to retrieve the needed API connection information.
To use this type of storage, create a conf file (the default is $HOME/.zbx.conf) that contains at least the [Zabbix API] section and any of the other parameters:

```
[Zabbix API]
username=johndoe
password=verysecretpassword
api=https://zabbix.mycompany.com/path/to/zabbix/frontend/
no_verify=true
```

Setting `no_verify` to `true` will disable TLS/SSL certificate verification when using https.

The scripts will need the pyzabbix module, to install:

`pip install pyzabbix`


For working with graphs (`zgetgraph.py` specifically) install Pillow (a fork of PIL):

`pip install pillow`


Usage examples
--------------

##### Save a 1 month 'CPU load' graph starting on the 1st of January 2014 for the host server.example.com as ~/jan.png:

`graphid=$(./zhgraphfinder.py -e server.example.com | grep 'CPU load' | cut -d ':' -f 1) ./zgetgraph.py -s $(date --date 'jan 1 2014' +%s) -t 2678400 -f ~/jan.png $graphid`

Take note that this requires GNU `date`. 

##### Using zproxyfinder.py to use the proper Zabbix proxy in a zabbix_sender script.

`zabbix_sender -k $ITEMKEY -o $ITEMVALUE -s $HOSTNAME -z $(zproxyfinder.py $HOSTNAME)`


##### Using the zapi.py API client to test Zabbix API calls:

```
Logging in on 'https://zabbix.example.com/' with user 'Admin'.
Welcome to the interactive Zabbix API client.
zapi: z host.get(filter={"host": "Zabbix Server"})
[{u'hostid': u'1001'}]
zapi: 
```


