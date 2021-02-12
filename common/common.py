import netmiko
from getpass import getpass
from netmiko import file_transfer
from netmiko.ssh_exception import NetMikoTimeoutException
from netmiko.ssh_exception import NetMikoAuthenticationException
from netmiko import SCPConn
from datetime import timedelta, datetime
import sys
import json
import os
import re
import pathlib
import requests
import subprocess
from time import sleep
from threading import Thread
import ipaddress
import sys
# from scapy.all import *



image_directory = '/opt/tools/storage/cisco-images/ios_Upgrade'
log_file = open('/var/log/cisco_upgrade.log', 'a+', buffering=1)

#
# def get_session(connection):
#     '''
#     Gets SSH session to connect to the device.
#     @args:
#         - connection: config to connect to the device
#     '''
#     session = netmiko.ConnectHandler(**connection)
#     return session

def set_boot(ssh_session, file, hostname):
    try:
        ssh_session.send_command('conf t', expect_string='#')
        bootcommand = f'boot system flash {file}'
        if 'cs' in hostname :
            bootcommand = f'boot system switch all flash:{file}'
        result = ssh_session.send_command(f'{bootcommand}', expect_string='#')
        ssh_session.send_command('end', expect_string='#')
        ssh_session.send_command('wr', expect_string='#')

    except Exception as e:
        log(f'{node} - set_boot() Error -> {str(e)}')
        print(f'{node} - exception set_boot : {e}')


def reload(ssh_session, node):
    try:
        ssh_session.send_command('reload',expect_string='')
        ssh_session.send_command('\n')

    except Exception as e:
        log(f'{node} - reload() Error -> {str(e)}')
        print(f'{node} - exception in reload : {e}')



def waiting_for_device(node, creds):
    try:
        while True:
            response = subprocess.check_output(["ping", "-c", "1", f"{node}"])
            if response != None:
                sleep(10)
                print(f'this is the response in waiting {response}\n')
                pre_post_reload_check(node, creds)
                break
            else:
                continue

    except Exception as e:
        log(f'{node} - waiting_for_device() --> {e}')
        print(f'{node} - waiting_for_device() --> {e}')


def pre_post_reload_check(node, creds):

    try:
        connection , cisco = find_type(node, creds)
        session = netmiko.ConnectHandler(**connection)
        # print(f'\nconnection in post_reload_check {connection} type is : {type(connection)} \n\n ')

        print(f'{node} - is up following are post checks: \n')
        if 'cs' in node:
            cmdlist = ['show ver | in .bin',
                        'show ip int brief',
                        'show boot',
                        'show switch']
        elif 'cr' in node:
            cmdlist = ['show ver | in .bin',
                        'show ip int brief',
                        'show bootvar']
        elif 'js' in node:
            cmdlist = ['show version | match Model',
                        'show version | match Junos:']

        for cmd in cmdlist:
            post_checks = session.send_command(cmd)
            print(f'\n {node} - \n ******{cmd}****** \n {post_checks}')
            log(f'\n {node} - \n ******{cmd}****** \n {post_checks}')

        # session.disconnect()

    except Exception as e:
        print(f'{node} - post_reload_check() --> {e}')



def find_type(node, creds):
    # for node in nodes:
    cisco = True
    connection = {}
    if 'js' in node:
        connection = {
            'device_type': 'juniper',
            'ip': node,
            'username': creds['username'],
            'password': creds['password'],
            'verbose': False
        }
        cisco = False
    elif 'cs' in node or 'cr' in node:
        connection = {
            'device_type': 'cisco_ios',
            'ip': node,
            'username': creds['username'],
            'password': creds['password'],
            'verbose': False
        }

    return connection, cisco


def show_rommon_version(connection):
    '''
    Shows ROMMON version.
    @args:
        - session: Netmiko session with the device
    '''
    try:
        session = netmiko.ConnectHandler(connection)
        cmdlist = ['show ver | in Software',
                    'show rom-monitor R0',
                    'show rom-monitor r0 | inc Version']
        # output = session.send_command(cmdlist)
        for cmd in cmdlist:
            post_checks = session.send_command(cmd)
            print('********** Im under show_rommon_version **********\n ')
            print(f'\n {node} - \n ******{cmd}****** \n {post_checks}')
            # log(f'\n {node} - \n ******{cmd}****** \n {post_checks}')
        # rommon_version = re.findall(r'[0-9]{2,3}.[0-9]{1,2}[(][0-9]r[/)]', output)
        return rommon_version[0]
    except Exception as e:
        return None



def archive_run(connection, filename):
    try:

        node = connection['ip']
        # print(f'im under archive_run: {connection}, {node}')
        ssh_session = netmiko.ConnectHandler(**connection) #get_session(connection)
        result = ssh_session.send_command("show run")
        file = open(filename,"w")
        file.write(result)
        file.close()
        ssh_session.disconnect()

    except Exception as e:
        log(f'{node} - archive_run() Error -> {str(e)}')
        print(f'{node} - exception in archive_run : {e}')


def verify_md5(session, file, md5, node):
    try:
        # node = connection['ip']
        # session = netmiko.ConnectHandler(**connection)
        result = session.send_command("verify /md5 flash:{} {}".format(file, md5))
        reg = re.compile(r'Verified')
        verify = reg.findall(result)
        if verify:
            # log(f'{node} - md5 Verification Successfull {verify[0]}')
            # print(f'{node} - md5 Verification Successfull {verify[0]}')
            result = True
        else:
            print(f'{node} - md5 Verification Failed {verify}')
            result = False

        # session.disconnect()

        return result

    except Exception as e:
        log(f'{node} - verify_md5() Error -> {str(e)}')
        print(f'{node} - exception in verify_md5 : {e}')



def verify_space(ssh_session, image):
    try:
        result = ssh_session.send_command("show flash:")
        reg = re.compile(r'(\d+)\sbytes\savailable')
        space = reg.findall(result)
        if len(space) == 0:
            reg = re.compile(r'(\d+)\sbytes\sfree')
            space = reg.findall(result)
        space = int(space[0])
        reg = re.compile(r'{}'.format(image))
        exist = reg.findall(result)
        file_size = os.path.getsize(f'{image_directory}/{image}')
        if space >= file_size:
            result = 'True'
        if space < file_size:
            result = 'False'
        if exist:
            exist = 'True'
        else:
            exist = 'False'
        return result, exist

    except Exception as e:
        log(f'verify_space() Error -> {str(e)}')
        print(f'exception in verify_space: {e}')


def progress(connection, image, flash_loc = ''):
    '''
    Prints transfer progress of a file in percentage
    @args:
        - connection: config to connect to a device
        - image: image file's name
    '''
    try:
        session = netmiko.ConnectHandler(**connection)
        file_size = os.path.getsize(f'{image_directory}/{image}')
        last_percent = 0
        hostname = connection['ip']
        print(f'{hostname} - {image}')
        while last_percent < 100:
            result = session.send_command(f"show flash{flash_loc}: | inc {image}")
            if result != '':
                if 'cr' in hostname:
                    current_size = int(result.split()[1])
                else:
                    current_size = int(result.split()[2])
                percent = (current_size * 100) // file_size

                ## file already exists
                if last_percent == 0 and percent == 100:
                    break
                if percent % 10 == 0 or percent >= 100:
                    last_percent = percent
                    if last_percent > 0:
                        log(f'{hostname} - Uploading to flash{flash_loc}: {last_percent}%')
                        print(f'{hostname} - Uploading to flash{flash_loc}: {last_percent}%')

            sleep(10)
        session.disconnect()

        if last_percent >= 100:
            send_update_to_slack(f'{hostname} - {image} is successfully uploaded in flash:{flash_loc}')

    except Exception as e:
        log(f'{hostname} - progress() Error -> {str(e)}')
        print(f'{hostname} - exception in progress : {e}')

def upload_ios_file(connection, config, model):
    '''
    Uploads the actual file to the network device
    @args:
        - connection - connection config to connect to the device
        - model: device's model
        - config: file with devices' models and images
    '''
    try:
        # print(f'the config has {config}')
        image = config[model]['image']
        md5 = config[model]['md5']
        node = connection['ip']
        session = netmiko.ConnectHandler(**connection)
        log(f'{node} - Verifying if sufficient space available')
        print(f'\n{node} - Verifying if sufficient space available on')


        ver = verify_space(session, f'{image}')
        stacks = get_stacks(session)

        if ver[0] == 'True' and ver[1] == 'False':
            log(f'{node} - sufficient space..! - proceeding to upload {image} ')
            print(f"\n{node} -  sufficient space..! - proceeding to upload {image} ")
            log(f'{node} - Uploading file :... {image} ')
            print(f'\n{node} - Uploading file :... {image} ')

            #TODO: umcomment when ready to upload
            transfer_fle = Thread(target = transfer_file, args = (connection, f'{image_directory}/{image}', image, ))
            progress_show = Thread(target = progress, args = (connection, f'{image}', ))

            #TODO: for testing only, comment this when ready to run
            # transfer_fle = Thread(target = transfer_file, args = (connection, 'upload_test.txt', 'upload_test.txt', ))#.start()
            # progress_show = Thread(target = progress, args = (connection, 'upload_test.txt', ))#.start()


            ## STARTING Thread
            transfer_fle.start()
            progress_show.start()
            ## ENDING Thread
            transfer_fle.join()
            progress_show.join()

            ## veryfing md5 (we dont need this, we have the md5sum in config.json)
            # md5 = check_md5(f'{image_directory}/{image}')
            log(f'{node} - Verifying md5 checksum on device ... ')
            print(f'\n{node} - Verifying md5 checksum on device ...\n\n')

            v_md5 = verify_md5(connection, image, md5)
            # v_md5 = verify_md5(session, 'upload_test.txt', md5)
            # print(v_md5)

        elif ver[0] == 'False' and ver[1] == 'False':
            log(f'{node} - Not enough free space on device ...')
            print(f'\n{node} - Not enough free space on device ...\n')


        elif ver[1] == 'True':
            send_update_to_slack(f'{node} - already has {image}')
            # print(f'\n\nFile already uploaded on device ... {node} \n\n ')


        log(f'{node} - successfully uploaded file: {image}')
        print(f'\n{node} - successfully uploaded file: {image}')

        if stacks is not None:
            log(f'{node} - Copying {image} to other switch in the stack...')
            print(f'\n{node} - Copying {image} to other switch in the stack...\n')

            threads = []
            for i in range(3, len(stacks)):
                th = Thread(target = copy_flash, args = (connection, f'{image}', i - 1, ))
                progress_show = Thread(target = progress, args = (connection, f'{image}', str(i - 1)))
                threads.append(th)
                threads.append(progress_show)

            for th in threads:
                th.start()

            for th in threads:
                th.join()

        # session.disconnect()
    except Exception as e:
        log(f'{node} - upload_ios_file() Error -> {str(e)}')
        print(f'{node} - exception in upload_ios_file : {e}')

def send_update_to_slack(message):
    '''
    Sends upload status to a Slack's channel.
    @args:
        - hostname: message to send to Slack
    '''

    message_block = {
    	"attachments": [
    		{
    			"color": "#f2c744",
    			"blocks": [
    				{
    					"type": "header",
    					"text": {
    						"type": "plain_text",
    						"text": "IOS Upload Status",
    						"emoji": True
    					}
    				},
                    {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"{message}"
                    }
                }
    			]
    		}
    	]
    }

    try:
        resp = requests.post('https://hooks.slack.com/services<#ADD THE WEBHOOK HERE#>', verify = False, headers = {'Content-Type': 'application/json'}, data = json.dumps(message_block))
        if resp.status_code == 200:
            log(f"Successfully sent to Slack!")
            print('Sent to Slack!')
    except Exception as e:
        log(f'send_update_to_slack() Error -> {str(e)}')
        print('send_update_to_slack error -> ' + str(e))


def get_stacks(ssh_session):
    '''
    Gets a list of switches from the stack.
    @args:
        - ssh_session: ssh session to connect to device
    '''
    try:
        stacks = ssh_session.send_command('show switch | in \d')
        if 'invalid' in stacks.lower():
            return None
        return stacks.split('\n')
    except Exception as e:
        log(f'get_stacks() Error -> {str(e)}')
        print(f'exception in get_stacks : {e}')
        return None



def copy_flash(connection, image, switch_num):
    '''
    Gets a list of switches from the stack.
    @args:
        - connection: configuration to connect to the device.
        - image: image name of IOS.
        - switch_num: switch number.
    '''
    try:
        print(f'Copying {image} to switch {switch_num}...')
        session = netmiko.ConnectHandler(**connection)
        result = session.send_command(f"show flash{switch_num}: | inc {image}")
        if result == '':
            copy_to_flash = session.send_command(f'copy flash:/{image} flash{switch_num}:', expect_string = r'Destination filename')
            copy_to_flash += session.send_command('\n', expect_string = r'#', delay_factor=6)
        else:
            send_update_to_slack(f'{image} already exists on flash{switch_num}:')
            log(f'{image} already exists on flash{switch_num}:')
            print(f'{image} already exists on flash{switch_num}:')

        session.disconnect()

    except Exception as e:
        log(f'copy_flash() Error -> {str(e)}')
        print(f'exception in copy_flash : {e}')



def transfer_file(connection, source_file, dest_file):
    '''
    Transfers a file to a device
    @args:
        - connection - config to connect to a device
        - source_file - source location of the file
        - dest_file - name of the file on the device
    '''
    try:

        session = netmiko.ConnectHandler(**connection)
        session.enable()
        file_system = 'bootflash:'
        if 'cs' in connection['ip']:
            file_system = 'flash:'

        if 'cr' in node:
            show_rommon_version(connection)

        my_transfer = file_transfer(
            session,
            source_file = f'{source_file}',
            dest_file = f'{dest_file}',
            file_system = f'{file_system}'
        )

        session.disconnect()


    except Exception as e:
        log(f'transfer_file() Error -> {str(e)}')
        print(f'exception in transfer_file : {e}')



def get_interface_by_model(ssh_session, cisco = True):
    '''
    Gets interface's standard by model type.
    @args:
        - session: Netmiko session with the device
        - cisco: true for cisco device, false for juniper's
    '''
    try:
        # ssh_session = netmiko.ConnectHandler(**connection)
        if cisco:
            model = ssh_session.send_command('show version | inc /K9')
            if model:
                model = model.split()[1]
                return 'cisco ' + model.split('/')[0]
            else:
                model = ssh_session.send_command('show version | inc Model number')
                model = model.split('\n')[0].split()[3]
                return 'cisco ' + model
        else:
            model = ssh_session.send_command('show version | match Model')
            model = model.split('\n')[0].replace('Model: ', '')
            return 'juniper ' + model
        # ssh_session.disconnect()
    except Exception as e:
        # print(f'Here is the exception : {e}')
        return None


def log(*message):
    '''
    Writes messages to log file.
    '''
    global log_file
    line = datetime.today().strftime('%Y-%m-%d %H:%M:%S - ') + ' | '.join(map(str,message)) + '\n'
    log_file.write(line)

def instruction():
    print('usage: cisco_upgrade [-h] {upgrade,upload} ...\n\n')
    print('positional arguments:')
    print('\t{upgrade,upload} ')
    print('\t  upgrade             Use this to upgrade the IOS image on the device')
    print('\t  upload              Use this to uploading the IOS file on to the device')
    print('\t  list-model          Use this to view the device hostname and the Model')
    # print('\t  delete              Use this to remove old IOS files from the device')
    # print('\t  rollback            Use this to rollback to old IOS image on the device')
    print('\t optional arguments:')
    print('\t-h, --help            show this help message and exit')
    exit(1)
