zabbix-gnomes
=============

A collection of various scripts to automate tasks with the Zabbix API. My main goal is to create a set of simple utilities that can be reused in shell scripts without using a lot of curl voodoo.

All of these tools can be invoked with `-h/--help` to get help.

### API tools:
- `zapi.py` -		Interactive Zabbix API client.

### History related:
- `zgethistory.py` -	Gets values from history for an itemid.

### Inv related:
- `zhinvswitcher.py` - 	Switches inv. mode on host(group)s.
- `zgetinventory.py` -  Prints host inventory in CSV format.
- `zhostupdater.py` - Updates host properties.

### Item related:
- `zhitemfinder.py` -	Finds items on a host.	
- `zgethistory.py` - 	Get item values from history (Trends are not supported!).

### Graph related:
- `zhgraphfinder.py` - 	Finds graphs configured on a Zabbix host.
- `zgetgraph.py` - 	Downloads a graph .PNG from the Zabbix frontend (needs user frontend access) and saves it.

### Group related:
- `zghostfinder.py` -	Finds member hosts in a hostgroup.

### Host related:
- `zhostfinder.py`  -   Finds hosts in Zabbix based on search string.
- `zhostupdater.py` -   Updates hosts properties.

### Proxy related:
- `zhproxyfinder.py` -	Finds configured proxy for a Zabbix host.

### Template related:
- `zhtmplfinder.py` - 	Finds linked templates for a Zabbix host.
- `zthostfinder.py` - 	Finds hosts that are linked to a template.
- `zthtmllinker.py` - 	Links host(group)s to a list of templates.
- `zthtmlunlink.py` - 	Unlinks host(group)s from a list of templates.

### Trigger related:
- `zhtrigfinder.py` -   Finds triggers on a host.
- `ztrigswitcher.py`-   Switches a trigger to enabled or discabled status.

### Macro related:
- `zhostupdater.py` - Updates host properties.

### Event related:
- `zeventfinder.py` - Finds events based on filters (includes a `tail -f` like mode).
- `zgetevent.py`   - Gets details for eventids, including ack's and alert actions.
- `zeventacker.py` - Acknowledges events based on eventids.

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

```
zabbix_sender -k $ITEMKEY -o $ITEMVALUE -s $HOSTNAME -z $(zhproxyfinder.py $HOSTNAME)
```

##### Using zhtmpllinker.py to link 3 templates to all the hosts in a hostgroup:

```
./zhtmpllinker.py -t "Template App Apache" "Template App MySQL" "Template OS Linux" -G "LAMP Servers"
```

##### Using zhtmplunlink.py to unlink a template from all the hosts in a hostgroup:

```
./zhtmplunlink.py -G "Webservers" -t "Template App MySQL"
```

#### Get the latest item value from history for the item with itemid 1001

```
./zgethistory.py 1001 -C 1
```

#### Get a list of item values with timestamps and unit from history for a period of 2hr from Jan 1st 2014 00:00hr

```
./zgethistory.py -s $(date --date 'jan 1 2014' +%s) -t 7200 -e 1030
```

#### Disable the 'Unavailable by ICMP' trigger on the host named 'Google DNS'

```
./ztrigswitcher.py -D $(./zhtrigfinder.py -s "Unavailable by ICMP" -n "Google DNS")
```

#### Count the number of active triggers on the host 'Webserver'

```
./zhtrigfinder.py -A "Webserver" | wc -l
```

##### Switch the inventory mode to manual for all the hosts in a hostgroup

```
./zhinvswitcher.py -G "Linux Servers" -m manual
```

##### Switch the inventory mode to automatic on all the hosts in Zabbix

```
./zhinvswitcher.py --all-hosts
```

##### Find all the hosts in the 'Customer A' hostgroup that match a name that starts with 'web'

```
./zghostfinder.py "Customer A" | grep -i '^web.*'
```

##### Print the last known value for the available memory in Bytes on the host 'Webserver' 
```
./zgethistory.py -C 1 $(./zhitemfinder.py -k 'vm.memory.size[available]' -n Webserver)
```

##### Perform a search for all monitored hosts matching the hostname string 'zabbix'
```
./zhostfinder.py -m -S zabbix
```

##### Output a CSV with hostid, hostname, OS, vendor and contact fields for all hosts in the 'Zabbix Servers' group
```
./zgetinventory.py -G "Zabbix Servers" -F "os" "vendor" "contact" > report.csv
```

##### Update the visible name of the host web001 to 'primary webserver'
```
./zhostupdater.py web001 -V 'primary webserver'
```

##### Enable the host web001, apply the macro {$APACHEPROC} and update the 'Sofware Application A' inv field
```
./zhostupdater.py web001 -E -M apacheproc=15 -I software_app_a="Apache"
```

### Find all PROBLEM events during the last hour for the the hosts in the group 'Linux Servers' (Limited to 100 events)
```
./zeventfinder.py -P -t 3600 -G 'Linux Servers' 
```

### Acknowledge 3 events with the message "Power outage"
```
./zeventacker.py -m "Power outage" 6578 6689 6590
```

### Print details on 3 events including trigger comments, actions and acknowledgements 
```
./zgetevent.py -ACL 6578 6689 6590 
```

### Acknowledge all PROBLEM events in the last 15 minutes for the hosts in the 'Linux Serves' group
```
./zeventacker.py -m 'Foobar with Fabric :-(' $(./zeventfinder.py -i -P -t 900 -G 'Linux servers') 
```

### Follow Zabbix trigger events for all hosts
```
./zeventfinder.py -L 10 --all-hosts -f
```

##### Using the zapi.py API client to test Zabbix API calls:

```
Logging in on 'https://zabbix.example.com/' with user 'Admin'.
Welcome to the interactive Zabbix API client.
zapi: z host.get(filter={"host": "Zabbix Server"})
[{u'hostid': u'1001'}]
zapi: 
```

## List of inventory fields
Please see the Zabbix manual for your version of Zabbix for the latest list of supported fields, these are only here for your convience.


|Property 		|Description|
|-----------------------|-----------| 	
|alias 			|Alias.|
|asset_tag 		|Asset tag.|
|chassis 		|Chassis.|
|contact 		|Contact person.|
|contract_number 	|Contract number.|
|date_hw_decomm 	|HW decommissioning date.|
|date_hw_expiry 	|HW maintenance expiry date.|
|date_hw_install 	|HW installation date.|
|date_hw_purchase 	|HW purchase date.|
|deployment_status 	|Deployment status.|
|hardware 		|Hardware.|
|hardware_full 		|Detailed hardware.|
|host_netmask 		|Host subnet mask.|
|host_networks 		|Host networks.|
|host_router 		|Host router.|
|hw_arch 		|HW architecture.|
|installer_name 	|Installer name.|
|location 		|Location.|
|location_lat 		|Location latitude.|
|location_lon 		|Location longitude.|
|macaddress_a 		|MAC address A.|
|macaddress_b 		|MAC address B.|
|model 			|Model.|
|name 			|Name.|
|notes 			|Notes.|
|oob_ip 		|OOB IP address.|
|oob_netmask 		|OOB host subnet mask.|
|oob_router 		|OOB router.|
|os 			|OS name.|
|os_full 		|Detailed OS name.|
|os_short 		|Short OS name.|
|poc_1_cell 		|Primary POC mobile number.|
|poc_1_email 		|Primary email.|
|poc_1_name 		|Primary POC name.|
|poc_1_notes 		|Primary POC notes.|
|poc_1_phone_a 		|Primary POC phone A.|
|poc_1_phone_b 		|Primary POC phone B.|
|poc_1_screen  	  	|Primary POC screen name.|
|poc_2_cell    	  	|Secondary POC mobile number.|
|poc_2_email   	  	|Secondary POC email.|
|poc_2_name    	  	|Secondary POC name.|
|poc_2_notes   	  	|Secondary POC notes.|
|poc_2_phone_a 		|Secondary POC phone A.|
|poc_2_phone_b 		|Secondary POC phone B.|
|poc_2_screen  	  	|Secondary POC screen name.|
|serialno_a    	  	|Serial number A.|
|serialno_b    	  	|Serial number B.|
|site_address_a	 	|Site address A.|
|site_address_b	 	|Site address B.|
|site_address_c	 	|Site address C.|
|site_city     	  	|Site city.|
|site_country  	  	|Site country.|
|site_notes    	  	|Site notes.|
|site_rack     	  	|Site rack location.|
|site_state    	  	|Site state.|
|site_zip      	  	|Site ZIP/postal code.|
|software      	  	|Software.|
|software_app_a	 	|Software application A.|
|software_app_b	 	|Software application B.|
|software_app_c	 	|Software application C.|
|software_app_d	 	|Software application D.|
|software_app_e	 	|Software application E.|
|software_full 		|Software details.|
|tag 			|Tag.|
|type 			|Type.|
|type_full 		|Type details.|
|url_a 			|URL A.|
|url_b 			|URL B.|
|url_c 			|URL C.|
|vendor 		|Vendor.|  


