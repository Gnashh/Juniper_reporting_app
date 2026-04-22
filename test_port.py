"""
Isolated Report Connection Test
================================
Runs the exact same connection + command flow as report_dialogs.py
but without Streamlit so the full error is visible immediately.

Fill in your values below and run:
    python test_report_flow.py
"""

import json
import traceback
from juniper_service import connect_via_jump_host, connect_to_device, run_command, close

# ---------------------------------------------------------------------------
# !! FILL THESE IN — copy exact values from your DB / UI !!
# ---------------------------------------------------------------------------

USE_JUMP      = True               # True if customer has jump host enabled

# Customer / jump host details
DEVICE_TYPE   = "Linux"          # jump host device type
JUMP_IP       = "192.168.33.60"
JUMP_USER     = "root"
JUMP_PASS     = "ipnet123"
JUMP_HOSTNAME = "linux_server"
JUMP_PORT     = 22                 # jump host port from customer record

# Target device details
TARGET_IP     = "192.168.77.111"
TARGET_USER   = "ipnet"
TARGET_PASS   = "ipnet123"
TARGET_PORT   = 2222
               # device port from device record

# Commands to test (copy from your template)
TEST_COMMANDS = [
    "show version",
    "show interfaces terse",
]

# ---------------------------------------------------------------------------

SEP = "=" * 60

print(SEP)
print("  CONNECTION DETAILS")
print(SEP)
print(f"  Use jump:    {USE_JUMP}")
if USE_JUMP:
    print(f"  Jump host:   {JUMP_IP}:{JUMP_PORT} ({DEVICE_TYPE})")
    print(f"  Jump user:   {JUMP_USER}")
    print(f"  Hostname:    {JUMP_HOSTNAME}")
print(f"  Target:      {TARGET_IP}:{TARGET_PORT}")
print(f"  Target user: {TARGET_USER}")
print()

# ---------------------------------------------------------------------------
# Step 1 — Connect
# ---------------------------------------------------------------------------
print(SEP)
print("  STEP 1 — Connecting")
print(SEP)

conn = None
try:
    if USE_JUMP:
        print(f"  Calling connect_via_jump_host(")
        print(f"      device_type  = {repr(DEVICE_TYPE)},")
        print(f"      jump_ip      = {repr(JUMP_IP)},")
        print(f"      jump_user    = {repr(JUMP_USER)},")
        print(f"      jump_hostname= {repr(JUMP_HOSTNAME)},")
        print(f"      target_ip    = {repr(TARGET_IP)},")
        print(f"      target_user  = {repr(TARGET_USER)},")
        print(f"      jump_port    = {JUMP_PORT},")
        print(f"      target_port  = {TARGET_PORT},")
        print(f"  )")
        conn = connect_via_jump_host(
            DEVICE_TYPE,
            JUMP_IP, JUMP_USER, JUMP_PASS, JUMP_HOSTNAME,
            TARGET_IP, TARGET_USER, TARGET_PASS,
            jump_port=JUMP_PORT,
            target_port=TARGET_PORT,
        )
    else:
        print(f"  Calling connect_to_device(")
        print(f"      target_ip   = {repr(TARGET_IP)},")
        print(f"      target_user = {repr(TARGET_USER)},")
        print(f"      target_port = {TARGET_PORT},")
        print(f"  )")
        conn = connect_to_device(
            TARGET_IP, TARGET_USER, TARGET_PASS,
            target_port=TARGET_PORT,
        )

    print(f"  ✓ Connected — mode: {conn['mode']}")

except ConnectionError as e:
    print(f"  ✗ ConnectionError: {e}")
    exit(1)
except Exception as e:
    print(f"  ✗ Unexpected error: {type(e).__name__}: {e}")
    print()
    traceback.print_exc()
    exit(1)

# ---------------------------------------------------------------------------
# Step 2 — Run commands
# ---------------------------------------------------------------------------
print()
print(SEP)
print("  STEP 2 — Running commands")
print(SEP)

for cmd in TEST_COMMANDS:
    print(f"\n  Command: {repr(cmd)}")
    try:
        result = run_command(conn, cmd)
        lines = result.splitlines()
        print(f"  ✓ Output ({len(lines)} lines) — first line: {repr(lines[0] if lines else '')}")
    except Exception as e:
        print(f"  ✗ Error running command: {type(e).__name__}: {e}")
        traceback.print_exc()

# ---------------------------------------------------------------------------
# Step 3 — Close
# ---------------------------------------------------------------------------
print()
print(SEP)
print("  STEP 3 — Closing connection")
print(SEP)

try:
    close(conn)
    print("  ✓ Closed cleanly")
except Exception as e:
    print(f"  ✗ Error closing: {type(e).__name__}: {e}")

print()
print(SEP)
print("  DONE — if all steps show ✓ the connection flow is working.")
print("  If any step shows ✗ paste the error above for diagnosis.")
print(SEP)