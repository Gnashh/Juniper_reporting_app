import paramiko
from db.devices import get_device_by_id

def connect_to_device(device_ip, username, password):
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect(hostname=device_ip, username=username, password=password)
    return client

def close_connection(client):
    client.close()

def run_command(client, command):
    stdin, stdout, stderr = client.exec_command(command)
    return stdout.read().decode()

import paramiko

def connect_via_jump_host(
    jump_ip, jump_user, jump_pass,
    device_ip, device_user, device_pass
):
    jump_client = paramiko.SSHClient()
    jump_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    jump_client.connect(
        hostname=jump_ip,
        username=jump_user,
        password=jump_pass
    )

    transport = jump_client.get_transport()
    dest_addr = (device_ip, 22)
    local_addr = ('127.0.0.1', 0)

    channel = transport.open_channel(
        "direct-tcpip",
        dest_addr,
        local_addr
    )

    device_client = paramiko.SSHClient()
    device_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    device_client.connect(
        hostname=device_ip,
        username=device_user,
        password=device_pass,
        sock=channel
    )

    return jump_client, device_client





