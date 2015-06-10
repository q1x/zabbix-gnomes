#!/usr/bin/python
import os
import zgcore.args as args
import zgcore.conf as config

cfgfile = os.getenv("HOME") + "/.zbx.conf"
result=config.LoadConfig(cfgfile)


