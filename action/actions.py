import netmiko
from getpass import getpass
from netmiko import file_transfer
from netmiko.ssh_exception import NetMikoTimeoutException
from netmiko.ssh_exception import NetMikoAuthenticationException
from netmiko import SCPConn
import string
from threading import Thread
import pathlib
from common import common
from threading import Thread

directory = pathlib.Path(__file__).parent.absolute()
mute = 'python3 /opt/nsgbin/nsg.py mute store_'
unmute = 'python3 /opt/nsgbin/nsg.py unmute store_'



def list_model(creds, nodes):
    '''
    Lists models of the device or at a particular site.
    @args:
        - creds: username and password
        - nodes: a list of devices
    '''
    try:
        print('Hostname \t Model')
        connection, cisco = common.find_type(nodes)
        node = connection['ip']
        if connection:
            ssh_session = netmiko.ConnectHandler(**connection)
            model = common.get_interface_by_model(ssh_session, cisco = cisco)
            print(f'{node} \t {model}')
            ssh_session.disconnect()

    except Exception as e:
        common.log(f'{node} - exception in list_model: {e}')
        print(f'{node} - exception in list_model : {e}')



def upload(creds, nodes, config, running_configs):
    '''
    Uploads IOS file(s) to the device or a particular site.
    @args:
        - creds: username and password
        - nodes: a list of devices
        - config: file with devices' models and images
    '''
    try:
        # print(f'Nodes i get {nodes}')
        for node in nodes :
            connection, cisco = common.find_type(node, creds)

            ##SAVE RUNING CONFIG
            print(f'node is : {node}')
            run_file = connection['ip'] + "-running-config.txt"
            print(f'\nSaving running config into file: {running_configs}/{run_file} \n')
            common.archive_run(connection, f'{running_configs}/{run_file}')
            common.log(f'{node} - Saving running config into file: {running_configs}/{run_file}')

            session = netmiko.ConnectHandler(**connection)
            if cisco == False:
                model = common.get_interface_by_model(session, cisco = cisco)
            else:
                model = common.get_interface_by_model(session, cisco = cisco)

            threads = []
            print(f'node just before the if condition {node}')
            if node != None:
                # print('the if Condition is failing')
                # ssh_session = netmiko.ConnectHandler(**connection)

                print(f'config under the upload {model}')
                if model in config:
                    th = Thread(target = common.upload_ios_file, args = (connection, config, model))
                    threads.append(th)
                else:
                    common.log(f'{node} - Please add {model} model to config.json ')
                    print(f'{node} - Please add {model} model to config.json')

            for th in threads:
                th.start()

            for th in threads:
                th.join()

    except Exception as e:
        common.log(f'{node} - exception : {e}')
        print(f'{node} - exception in upload under actions  : {e}')


def upgrade_ios(creds, nodes, config):
    '''
    upgrade_ios IOS file(s) to the device or a particular site.
    @args:
        - creds: username and password
        - nodes: a list of devices
        - config: file with devices' models and images
    '''

    try:
        print(nodes)
        for node in nodes:

            connection, cisco = common.find_type(node, creds)
            # node = connection['ip']
            # print(connection)

            session = netmiko.ConnectHandler(**connection)
            model = common.get_interface_by_model(session, cisco = cisco)
            image = config[model]['image']
            md5 = config[model]['md5']
            # print(md5)


            # is_device_up = common.waiting_for_device(node, creds)



            common.log(f'{node} - is upgrading to IOS : {image}')
            print(f'{node} - is upgrading to IOS : {image}')
            verify_md5 = common.verify_md5(session, image, md5, node)

            if verify_md5 == True:
                ##TODO: umcomment when ready to boot
                common.log(f'{node} - md5 validated Successfull..!')
                print(f'{node} - md5 validated Successfull..!')
                boot = input(f"\n{node} - proceed with changing boot ? (y/n): ")
                common.log(boot)
                # response = subprocess.check_output([f"{mute}, f'{node}'])
                # print(response)

                if boot == 'y':
                    common.set_boot(session, image, node)
                    if 'cs' in node:
                        bootvar = session.send_command('show boot')
                    else:
                        bootvar = session.send_command('show bootvar')
                    # print(bootvar)
                    print(f'{node} - Preforming pre checks ')
                    common.pre_post_reload_check(node, creds)

                    common.log(f'\n{node} - {bootvar}')
                    accept_reload = input("\n\nSuccess! - proceed with reload ? (y/n): ")
                    common.log(f'\n{node} - {accept_reload}')
                    if accept_reload == 'y':
                        try:
                            ##TODO: umcomment when ready to reload
                            print('Im reloading now\n ')
                            common.reload(session, node)
                            # is_device_up = common.waiting_for_device(node, creds)
                            # sleep(10)
                            common.waiting_for_device(node, creds)

                            print('reloading completed')



                        except Exception as e:
                            common.log(f'{node} - unable to reload {e} ...')
                            print(f'{node} - unable to reload {e} ... ')
                    else:
                        common.log(f'{node} - Aborting reload')
                        print(f'\n{node} - Aborting reload !!!\n\n')
            else:
                common.log(f'{node} - Error veryfiing md5 checksum on device, quitting !!!')
                print(f'\n\n{node} - Error veryfiing md5 checksum on device, quitting !!!\n\n')


            session.disconnect()

    except Exception as e:
        common.log(f'{node} - upgrade_ios() Error -> {str(e)}')
        print(f'{node} - exception in upgrade_ios : {e}')


def rollback(creds, nodes): #, img, hostname):
    '''
    Rollbacks to old image version on the device.
    @args:
        - img: old image from the config files we save.
        - hostname: hostname.
    '''
    # print(f'old images under rollback {img}')

    try:
        for node in nodes:
            connection, cisco = common.find_type(node, creds)
            session = netmiko.ConnectHandler(**connection)
            model = common.get_interface_by_model(session, cisco = cisco)
            # image = config[model]['image']

            print(f'Hostname i have {node}')
            image = config[model]['image']

            regex = image.split('-')[0]
            lines = session.send_command(f'dir | inc {regex}').split('\n')
            for line in lines:
                ## retrieving old image
                if image not in line:
                    img = re.findall(r'' + regex + '.*', line)[0]
                    print(f'Rollback to {img} for {hostname}')
                    ##TODO: umcomment when ready to
                    set_boot(session, img, hostname)
                    if 'cs' in node:
                        bootvar = session.send_command('show boot')
                    else:
                        bootvar = session.send_command('show bootvar')
                    print(bootvar)
                    reload_3 = input("\n\nSuccess! - proceed with reload ? (y/n) ... ")
                    if reload_3 == 'y':
                        try:
                            ##TODO: umcomment when ready to reload
                            # reload(session)
                            print("Reloading ... ")
                        except:
                           print("NOT Reloading ... ")
            # with open(f"/home/few7/device-ios-upgrade/run_conf/{node}-running-config.txt") as fo:
            #     for line in fo:
            #         # print(f'Im inside the while {line}')
            #         if img in line:
            #             ##UNCOMMENT ONES READY
            #             common.set_boot(session ,img, hostname)
            #             common.reload(session)
            #             ##COMMENT OUT LATER
            #             print(f' The line which has the image :{img} is {line}')

    except Exception as e:
        common.log(f'{node} - rollback() Error -> {str(e)}')
        print(f'{node} - Exception in rollback {e}')
