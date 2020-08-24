#!/usr/bin/env python3
import yaml, jinja2, time, logging, threading, os
from netmiko import Netmiko

def createFolder(directory):
    try:
        if not os.path.exists(directory):
            os.makedirs(directory)
    except OSError:
        print ('Error: Creating directory. ' +  directory)

def setup_logging():
    try:
        d8 = time.strftime("%Y-%m-%d-%M")
        # Logging for all Netmiko commands (SSH) Creates a new file. If file exists, it appends new content.
        # Sets up Folder | ignores if already present.
        createFolder('Logging')
        # Start Log
        mikoLog = ('Logging/NetmikoLog-'+ (d8)+ '.txt')
        open(mikoLog, 'a+')
        logging.basicConfig(filename=mikoLog, level=logging.DEBUG)
        logging.getLogger("netmiko")
    except Exception as e:
        print(f'Issue with Logging, {e}')

def confgen(yfile, jfile):
    with open(jfile, 'r+') as j:
        jfile = j.read()
        template = jinja2.Template(jfile)
        return template.render(yfile)

def yaml_read(yfile):
        with open(yfile, 'r+') as f:
            read_yaml = yaml.load(f, Loader=yaml.FullLoader) 
            return read_yaml
            
def main():
    # Start logging process:
    setup_logging()
    # YEAR MONTH DAY MINUTE
    d8 = time.strftime("%Y-%m-%d-%M")

    yaml_file = 'service-vars.yml'
    jinja_template = 'vpls-template.j2'
    # ----------------------
    read_yaml = yaml_read(yaml_file)

    # # Take imported YAML dictionary and start multi-threaded configuration generation.
    # # You could condense all yaml files into one if you wanted.

    for hosts, vars in read_yaml.items():
        # Add host to vars dictionary
        host = {'host': hosts}

        vars.update(host)

        cfg_list = confgen(read_yaml[hosts], jinja_template)

        conn = Netmiko(host=vars['HOST_IP'], device_type='alcatel_sros',
        username="admin", password="admin", response_return=None)

        vvalidate = conn.send_command('show service service-using | match '+ str(vars['SERVICE_ID']))

        if str(vars['SERVICE_ID']) in vvalidate:
            conn.disconnect()
            print(vars['host']+' Already contains this Service ID. Skipping this Node..')
        else:
            cust = conn.send_command('show service customer '+ str(vars['CUSTOMER']))
            if 'No Matching Entries' in cust:
                cust_create = (f'/configure service customer '+ str(vars['CUSTOMER'])+' name '+ vars['CUST_DESC'].upper()+' create')
                conn.send_command_timing(cust_create,cmd_verify=False)
                # Create VPLS Service.
                output = conn.send_config_set(cfg_list,cmd_verify=False)
                if 'MINOR' in output:
                    print('Error, please review Netmiko Logs.')
                else:
                    # Display results
                    print('-' * 80)
                    print('\nConfiguration applied on ' + vars['host'] + ': \n\n' + output)
                    print('-' * 80)
                    conn.disconnect()

            else:
                # # Create VPLS Service.
                output = conn.send_config_set(cfg_list,cmd_verify=False)
                if 'MINOR' in output:
                    print('Error, please review Netmiko Logs.')
                else:
                    # Display results
                    print('-' * 80)
                    print('\nConfiguration applied on ' + vars['host'] + ': \n\n' + output)
                    print('-' * 80)

                    # # Probably a good idea
                    conn.disconnect()

        # Capture PWD -This should be the base of where the program lives.
        PWD = os.getcwd()

        # Setup ConfigZ -
        createFolder('Configurations')

        # Change to the correct folder by hostname. -
        os.chdir('Configurations')

        # Organize the new configuration files. -
        createFolder(vars['host'])

        # Change to the correct folder by hostname. -
        os.chdir(vars['host'])

        # Open a new text file and save the configuration.
        # 'host' is extracted from the yaml file. 
        # This should be the system name.

        y = open(vars['host']+'-cfg-change-'+ (d8) +'.txt','w')
        y.write(cfg_list)

        # Return to the correct directory and re-run code for each NODE.
        os.chdir(PWD)
    # ----------------------

main()