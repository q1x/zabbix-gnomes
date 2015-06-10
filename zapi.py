#!/usr/bin/python
#
# import needed modules.
#
import cmd
import zgcore 

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
