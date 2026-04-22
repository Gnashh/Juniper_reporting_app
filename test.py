"""
Debug Connection Test
=====================
Tests both direct and jump host connections with detailed logging.
Run this to diagnose connection issues before generating reports.
"""

import sys
import time
import traceback
from juniper_service import (
    connect_via_jump_host,
    run_command,
    close,
)

# =============================================================================
# CONFIGURATION - Update these with your actual values
# =============================================================================

# Customer/Jump Host Settings
CUSTOMER_CONFIG = {
    "device_type": "Linux",  # "Linux", "Juniper", "MikroTik"
    "jump_host": 1,  # 1 = use jump host, 0 = direct connection
    "jump_host_ip": "192.168.33.60",
    "jump_host_username": "root",
    "jump_host_password": "ipnet123",
    "jump_host_hostname": "Ubuntu",
    "target_port": "23",
}

# Target Device Settings
DEVICE_CONFIG = {
    "device_ip": "192.168.33.250",
    "username": "ipnet",
    "password": "ipnet123",
    "hostname": "target-device",
}

# Test Commands
TEST_COMMANDS = [
    "show version",
    "show interfaces terse",
    "show system uptime",
]

# =============================================================================
# Helper Functions
# =============================================================================

def print_banner(text):
    """Print a formatted banner"""
    print("\n" + "=" * 80)
    print(f"  {text}")
    print("=" * 80)


def print_section(text):
    """Print a section header"""
    print(f"\n--- {text} ---")


def print_result(label, value, indent=2):
    """Print a labeled result"""
    spaces = " " * indent
    print(f"{spaces}{label}: {value}")


def test_connection_info(connection):
    """Display connection information"""
    print_section("Connection Info")
    print_result("Mode", connection.get("mode"))
    print_result("Has Jump", connection.get("jump") is not None)
    print_result("Has Client", connection.get("client") is not None)
    print_result("Has Shell", connection.get("shell") is not None)


def test_command_execution(connection, commands):
    """Test executing multiple commands"""
    print_section("Command Execution Test")
    
    results = []
    for i, cmd in enumerate(commands, 1):
        print(f"\n  [{i}/{len(commands)}] Executing: {cmd}")
        try:
            start_time = time.time()
            output = run_command(connection, cmd)
            elapsed = time.time() - start_time
            
            print(f"      ✓ Success ({elapsed:.2f}s)")
            print(f"      Output length: {len(output)} chars")
            print(f"      First 100 chars: {repr(output[:100])}")
            
            results.append({
                "command": cmd,
                "status": "success",
                "output": output,
                "elapsed": elapsed,
            })
            
        except Exception as e:
            print(f"      ✗ Failed: {str(e)}")
            traceback.print_exc()
            results.append({
                "command": cmd,
                "status": "error",
                "error": str(e),
            })
    
    return results


def print_summary(results):
    """Print test summary"""
    print_banner("TEST SUMMARY")
    
    success_count = sum(1 for r in results if r["status"] == "success")
    error_count = len(results) - success_count
    
    print_result("Total Commands", len(results))
    print_result("Successful", success_count)
    print_result("Failed", error_count)
    
    if error_count > 0:
        print_section("Failed Commands")
        for r in results:
            if r["status"] == "error":
                print(f"  • {r['command']}")
                print(f"    Error: {r['error']}")


# =============================================================================
# Main Test Flow
# =============================================================================

def main():
    print_banner("CONNECTION DEBUG TEST")
    
    # Display configuration
    print_section("Configuration")
    print_result("Device Type", CUSTOMER_CONFIG["device_type"])
    print_result("Jump Host IP", CUSTOMER_CONFIG["jump_host_ip"])
    print_result("Target IP", DEVICE_CONFIG["device_ip"])
    print_result("Target Port", CUSTOMER_CONFIG["target_port"])
    
    connection = None
    results = []
    
    try:
        # Step 1: Connect
        print_banner("STEP 1: ESTABLISHING CONNECTION")
        
        target_port = int(CUSTOMER_CONFIG.get("target_port") or 22)
        
        print(f"  Connecting via jump host {CUSTOMER_CONFIG['jump_host_ip']}...")
        print(f"  Device type: {CUSTOMER_CONFIG['device_type']}")
        
        connection = connect_via_jump_host(
            CUSTOMER_CONFIG["device_type"],
            CUSTOMER_CONFIG["jump_host_ip"],
            CUSTOMER_CONFIG["jump_host_username"],
            CUSTOMER_CONFIG["jump_host_password"],
            CUSTOMER_CONFIG["jump_host_hostname"],
            DEVICE_CONFIG["device_ip"],
            DEVICE_CONFIG["username"],
            DEVICE_CONFIG["password"],
            target_port,
        )
        
        print("  ✓ Connection established")
        test_connection_info(connection)
        
        # Step 2: Execute commands
        print_banner("STEP 2: EXECUTING COMMANDS")
        results = test_command_execution(connection, TEST_COMMANDS)
        
        # Step 3: Close connection
        print_banner("STEP 3: CLOSING CONNECTION")
        close(connection)
        print("  ✓ Connection closed")
        
    except TimeoutError as e:
        print(f"\n  ✗ TIMEOUT ERROR: {str(e)}")
        print(f"  Cannot reach target - check network connectivity")
        
    except Exception as e:
        print(f"\n  ✗ ERROR: {str(e)}")
        print("\nFull traceback:")
        traceback.print_exc()
        
    finally:
        # Always try to close connection
        if connection:
            try:
                close(connection)
            except:
                pass
    
    # Print summary
    if results:
        print_summary(results)
    
    print_banner("TEST COMPLETE")


if __name__ == "__main__":
    main()
