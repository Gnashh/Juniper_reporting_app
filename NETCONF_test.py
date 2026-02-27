from ncclient import manager
import paramiko

def connect_netconf(device_ip, username, password):
    mgr = manager.connect(
        host=device_ip,
        port=830,
        username=username,
        password=password,
        hostkey_verify=False,
        device_params={'name': 'junos'},
        allow_agent=False,
        look_for_keys=False
    )
    return mgr

def close_connection(mgr):
    mgr.close_session()

def get_system_info(mgr):
    return mgr.rpc.get_system_information()

def run_cli_netconf(mgr, command):
    return mgr.command(command)

def connect_netconf_via_jump_host(jump_ip, jump_user, jump_pass, device_ip, device_user, device_pass):
    jump_client = paramiko.SSHClient()
    jump_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    jump_client.connect(
        hostname=jump_ip,
        username=jump_user,
        password=jump_pass
    )

    transport= jump_client.get_transport()
    channel = transport.open.channel(
    "direct-tcpip",
    (device_ip, 830),
    ('127.0.0.1', 0)
    )

    mgr = manager.connect(
        host=device_ip,
        port=830,
        username=device_user,
        password=device_pass,
        sock=channel,
        hostkey_verify=False,
        device_params={'name': 'junos'},
        allow_agent=False,
        look_for_keys=False,
    )

    return jump_client, mgr




