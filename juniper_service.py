"""
Juniper Device SSH Service
==========================
Provides SSH connectivity to Juniper network devices for running CLI commands.
Supports both direct connection and connection via a jump host (bastion).
"""

import paramiko
from db.devices import get_device_by_id


def connect_to_device(device_ip, username, password):
    """
    Establish a direct SSH connection to a Juniper device.
    Returns a paramiko SSHClient instance for running commands.
    """
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect(hostname=device_ip, username=username, password=password)
    return client


def close_connection(client):
    """Close the SSH connection and release resources."""
    client.close()


def run_command(client, command):
    """
    Execute a CLI command on the connected device.
    Returns the combined stdout output as a string.
    """
    stdin, stdout, stderr = client.exec_command(command)
    return stdout.read().decode()


def connect_via_jump_host(
    jump_ip, jump_user, jump_pass,
    device_ip, device_user, device_pass
):
    """
    Connect to a device through a jump host (bastion). First SSHs into the jump
    host, then opens a direct-tcpip channel to the target device.
    Returns (jump_client, device_client) - close both when done.
    """
    # First connect to the jump host
    jump_client = paramiko.SSHClient()
    jump_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    jump_client.connect(
        hostname=jump_ip,
        username=jump_user,
        password=jump_pass
    )

    # Create SSH tunnel through jump host to target device
    transport = jump_client.get_transport()
    dest_addr = (device_ip, 22)
    local_addr = ('127.0.0.1', 0)

    channel = transport.open_channel(
        "direct-tcpip",
        dest_addr,
        local_addr
    )

    # Connect to target device using the tunnel as socket
    device_client = paramiko.SSHClient()
    device_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    device_client.connect(
        hostname=device_ip,
        username=device_user,
        password=device_pass,
        sock=channel
    )

    return jump_client, device_client


def get_system_info(client):
    """
    Get system information from the connected device.
    Returns a dictionary of system information.
    """
    result = run_command(client, "show system information")
    
    # Parse the output string to extract values
    hostname = "Unknown"
    model = "Unknown"
    version = "Unknown"
    
    for line in result.split('\n'):
        if 'Hostname:' in line or 'hostname:' in line:
            hostname = line.split(':', 1)[1].strip()
        elif 'Model:' in line or 'model:' in line:
            model = line.split(':', 1)[1].strip()
        elif 'Version:' in line or 'JUNOS' in line:
            version = line.split(':', 1)[1].strip() if ':' in line else line.strip()
    
    return {
        "hostname": hostname,
        "model": model,
        "version": version
    }


def close_jump_connection(jump_client, device_client):
    """Close both jump host and device connections in correct order."""
    if device_client:
        device_client.close()
    if jump_client:
        jump_client.close()
