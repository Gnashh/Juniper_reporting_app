import re
import socket
import time
import paramiko

PROXY_TUNNEL_SUPPORTED = {"Linux"}

CLI_PROMPTS   = ["#", ">", "$"]
SHELL_PROMPTS = ["%"]
ALL_PROMPTS   = CLI_PROMPTS + SHELL_PROMPTS

PROMPT_RE = re.compile(r'[\w\-\.@]+\s*[#>$]\s*$', re.MULTILINE)


# ---------------------------------------------------------------------------
# Port reachability check — runs before any SSH attempt so the user gets a
# clear human-readable error instead of a raw paramiko timeout exception.
# ---------------------------------------------------------------------------

def _check_port(host: str, port: int, label: str, timeout: int = 5) -> None:
    """
    Try opening a raw TCP socket to host:port.
    Raises ConnectionError with a descriptive message if it fails.
    label — human-readable name shown in the error e.g. 'jump host' or 'target device'
    """
    try:
        sock = socket.create_connection((host, port), timeout=timeout)
        sock.close()
    except socket.timeout:
        raise ConnectionError(
            f"Cannot reach {label} at {host}:{port} — connection timed out. "
            f"Possible causes: wrong IP, port {port} is not open, "
            f"or a firewall is blocking the connection."
        )
    except ConnectionRefusedError:
        raise ConnectionError(
            f"Cannot reach {label} at {host}:{port} — connection refused. "
            f"The host is reachable but port {port} is not listening. "
            f"Check that SSH is running on port {port} or use a different port."
        )
    except socket.gaierror as e:
        raise ConnectionError(
            f"Cannot resolve hostname for {label} '{host}' — {e}. "
            f"Check that the IP address or hostname is correct."
        )
    except OSError as e:
        raise ConnectionError(
            f"Cannot reach {label} at {host}:{port} — {e}."
        )


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _make_client():
    c = paramiko.SSHClient()
    c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    return c


def _read_until(shell, markers, timeout=20, stop_on_silence=False):
    output = ""
    deadline = time.time() + timeout
    last_recv = time.time()

    while time.time() < deadline:
        if shell.recv_ready():
            chunk = shell.recv(65535).decode(errors="replace")
            output += chunk
            last_recv = time.time()

            if "---(more)---" in chunk or "-- (more)" in chunk:
                shell.send(" ")

            if any(m in output for m in markers):
                break
        else:
            if stop_on_silence and output and (time.time() - last_recv > 1):
                break
            time.sleep(0.1)

    return output


def _drain(shell):
    time.sleep(0.3)
    while shell.recv_ready():
        shell.recv(65535)


def _send(shell, cmd, markers, timeout=20):
    _drain(shell)
    shell.send(cmd + "\n")
    return _read_until(shell, markers, timeout)


def _get_prompt_hostname(output):
    matches = PROMPT_RE.findall(output)
    if not matches:
        return None

    last = matches[-1].strip()
    host = re.sub(r'[#>$]\s*$', '', last).strip()

    if '@' in host:
        host = host.split('@')[-1]

    return host.lower()


def _wait_for_target(shell, jump_hostname):
    jump = jump_hostname.split(".")[0].lower()

    for _ in range(5):
        _drain(shell)
        shell.send("\n")

        out = _read_until(shell, ALL_PROMPTS, stop_on_silence=True)
        host = _get_prompt_hostname(out)

        if not host:
            time.sleep(1)
            continue

        if jump and (host == jump or jump in host):
            time.sleep(1)
            continue

        return True

    return False


def _build_ssh(device_type, user, ip, target_port):
    """Build the SSH command issued from inside the jump host CLI toward the target."""
    if device_type == "Linux":
        return (
            f"ssh -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null "
            f"-p {target_port} {user}@{ip}"
        )

    if device_type == "Juniper":
        return f"ssh {user}@{ip}"


# ---------------------------------------------------------------------------
# Strategy A — Proxy Tunnel (Linux jump hosts only)
# ---------------------------------------------------------------------------

def _connect_proxy(jump_ip, jump_user, jump_pass, jump_port,
                   target_ip, target_user, target_pass, target_port):
    # Check both ports are reachable before attempting SSH
    _check_port(jump_ip, jump_port, "jump host")
    _check_port(target_ip, target_port, "target device")

    jump = _make_client()
    try:
        jump.connect(
            jump_ip, username=jump_user, password=jump_pass,
            port=jump_port,
            look_for_keys=False, allow_agent=False, timeout=30,
        )
    except paramiko.AuthenticationException:
        raise ConnectionError(
            f"Authentication failed for jump host {jump_ip}:{jump_port} — "
            f"check username and password."
        )

    tunnel = jump.get_transport().open_channel(
        "direct-tcpip",
        (target_ip, target_port),
        ("127.0.0.1", 0),
    )

    dev = _make_client()
    try:
        dev.connect(
            target_ip, username=target_user, password=target_pass,
            port=target_port, sock=tunnel,
            look_for_keys=False, allow_agent=False, timeout=30,
        )
    except paramiko.AuthenticationException:
        jump.close()
        raise ConnectionError(
            f"Authentication failed for target device {target_ip}:{target_port} — "
            f"check username and password."
        )

    return {"mode": "proxy", "jump": jump, "client": dev}


# ---------------------------------------------------------------------------
# Strategy B — Shell Tunnel (Juniper / MikroTik jump hosts)
# ---------------------------------------------------------------------------

def _connect_shell(device_type, jump_ip, jump_user, jump_pass, jump_port,
                   jump_hostname, target_ip, target_user, target_pass, target_port):
    # Check jump host port before attempting SSH
    # Target reachability is checked indirectly via CLI output from the jump host
    _check_port(jump_ip, jump_port, "jump host")

    jump = _make_client()
    try:
        jump.connect(
            jump_ip, username=jump_user, password=jump_pass,
            port=jump_port,
            look_for_keys=False, allow_agent=False, timeout=30,
        )
    except paramiko.AuthenticationException:
        raise ConnectionError(
            f"Authentication failed for jump host {jump_ip}:{jump_port} — "
            f"check username and password."
        )

    shell = jump.invoke_shell()
    _read_until(shell, CLI_PROMPTS)

    cmd = _build_ssh(device_type, target_user, target_ip, target_port)
    out = _send(shell, cmd, ["yes/no", "assword", "refused", "unreachable", "timed out"] + CLI_PROMPTS)

    # Detect target-side errors reported in the jump host CLI output
    out_lower = out.lower()
    if "syntax error" in out_lower:
        jump.close()
        raise ConnectionError(
            f"SSH command syntax error on jump host — device type '{device_type}' "
            f"may not support the SSH command format used."
        )
    if "connection refused" in out_lower:
        jump.close()
        raise ConnectionError(
            f"Target device {target_ip}:{target_port} refused the connection — "
            f"port {target_port} is not open or SSH is not running on that port."
        )
    if "no route to host" in out_lower or "unreachable" in out_lower:
        jump.close()
        raise ConnectionError(
            f"Target device {target_ip} is unreachable from the jump host — "
            f"check routing or that the IP address is correct."
        )
    if "timed out" in out_lower:
        jump.close()
        raise ConnectionError(
            f"Connection to target device {target_ip}:{target_port} timed out — "
            f"a firewall may be blocking port {target_port}."
        )

    if "yes/no" in out:
        out = _send(shell, "yes", ["assword"] + CLI_PROMPTS)

    if "assword" in out:
        shell.send(target_pass + "\n")
        time.sleep(2)

    if not _wait_for_target(shell, jump_hostname):
        jump.close()
        raise ConnectionError(
            f"Connected to jump host {jump_ip} but could not confirm landing on "
            f"target device {target_ip}. Common causes: wrong target credentials, "
            f"target unreachable, or jump_host_hostname '{jump_hostname}' does not "
            f"match the actual prompt hostname."
        )

    if device_type == "Juniper":
        _send(shell, "set cli screen-length 0", CLI_PROMPTS)

    return {"mode": "shell", "jump": jump, "shell": shell}


# ---------------------------------------------------------------------------
# Direct connection (no jump host)
# ---------------------------------------------------------------------------

def connect_to_device(target_ip, target_user, target_pass, target_port=22):
    _check_port(target_ip, target_port, "target device")

    dev = _make_client()
    try:
        dev.connect(
            target_ip, username=target_user, password=target_pass,
            port=target_port,
            look_for_keys=False, allow_agent=False, timeout=30,
        )
    except paramiko.AuthenticationException:
        raise ConnectionError(
            f"Authentication failed for {target_ip}:{target_port} — "
            f"check username and password."
        )

    shell = dev.invoke_shell()
    _read_until(shell, CLI_PROMPTS)
    _send(shell, "set cli screen-length 0", CLI_PROMPTS)

    return {"mode": "direct", "client": dev, "shell": shell}


# ---------------------------------------------------------------------------
# Unified jump host interface
# ---------------------------------------------------------------------------

def connect_via_jump_host(device_type, jump_ip, jump_user, jump_pass, jump_hostname,
                          target_ip, target_user, target_pass,
                          jump_port=22, target_port=22):
    """
    Auto-select proxy tunnel (Linux) or shell tunnel (Juniper/MikroTik).

    Args:
        device_type:   Jump host OS — "Linux", "Juniper", "MikroTik"
        jump_ip:       Jump host IP
        jump_user:     Jump host SSH username
        jump_pass:     Jump host SSH password
        jump_hostname: Jump host hostname as it appears in its CLI prompt
        target_ip:     Target device IP
        target_user:   Target device SSH username
        target_pass:   Target device SSH password
        jump_port:     Port to reach the jump host on (default 22)
        target_port:   Port to reach the target device on (default 22)
    """
    if device_type in PROXY_TUNNEL_SUPPORTED:
        return _connect_proxy(
            jump_ip, jump_user, jump_pass, jump_port,
            target_ip, target_user, target_pass, target_port,
        )

    return _connect_shell(
        device_type, jump_ip, jump_user, jump_pass, jump_port,
        jump_hostname, target_ip, target_user, target_pass, target_port,
    )


# ---------------------------------------------------------------------------
# Run command
# ---------------------------------------------------------------------------

def run_command(conn, cmd):
    if conn["mode"] == "proxy":
        stdin, stdout, stderr = conn["client"].exec_command(cmd)
        return stdout.read().decode()

    shell = conn["shell"]
    _drain(shell)

    shell.send(cmd + "\n")
    out = _read_until(shell, CLI_PROMPTS, stop_on_silence=True)

    lines = out.splitlines()

    if lines and cmd in lines[0]:
        lines = lines[1:]

    if lines and lines[-1].strip().endswith(tuple(CLI_PROMPTS)):
        lines = lines[:-1]

    return "\n".join(lines).strip()


# ---------------------------------------------------------------------------
# Close connection
# ---------------------------------------------------------------------------

def close(conn):
    try:
        if conn["mode"] == "proxy":
            conn["client"].close()
            conn["jump"].close()
        elif conn["mode"] == "direct":
            conn["client"].close()
        else:
            conn["shell"].send("exit\n")
            time.sleep(0.5)
            conn["shell"].close()
            conn["jump"].close()
    except Exception:
        pass
