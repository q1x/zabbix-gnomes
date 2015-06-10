import argparse
import 


def LoadArgs():
    
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers()  





epilog="""
       This program can use .ini style configuration files to retrieve the needed API connection information.
       To use this type of storage, create a conf file (the default is $HOME/.zbx.conf) that contains at least the [Zabbix API] section and any of the other parameters:
       
        [Zabbix API]
        username=johndoe
        password=verysecretpassword
        api=https://zabbix.mycompany.com/path/to/zabbix/frontend/
        no_verify=true

       """

