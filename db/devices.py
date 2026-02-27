"""
Device Database Module
=====================
CRUD operations for network devices (routers, switches, firewalls).
Each device belongs to a customer and stores connection credentials.
"""

import mysql.connector
from db.customer import get_customer_by_id
from db.connect_to_db import connect_to_db


def get_devices():
    """Fetch all devices; returns list of tuples."""
    conn = connect_to_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM devices")
    devices = cursor.fetchall()
    return devices

def get_device_by_id(id):
    """Fetch a single device by ID; returns dict or None."""
    conn = connect_to_db()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM devices WHERE id = %s", (id,))
    devices = cursor.fetchone()
    return devices

def create_device(customer_id, serial_number, device_type, device_model, device_ip, username, password):
    """Insert a new device; validates customer exists. Returns new row id."""
    conn = connect_to_db()
    cursor = conn.cursor()
    customer = get_customer_by_id(customer_id)
    if customer is None:
        return print("Customer does not exist")
    else:
        cursor.execute("INSERT INTO devices (customer_id, serial_number, device_type, device_model, device_ip, username, password) VALUES (%s, %s, %s, %s, %s, %s, %s)", (customer_id, serial_number, device_type, device_model, device_ip, username, password))
        conn.commit()
        return cursor.lastrowid
        
def update_device(id, customer_id, serial_number, device_type, device_model, device_ip):
    """Update device metadata (credentials are not changed by update)."""
    conn = connect_to_db()
    cursor = conn.cursor()
    cursor.execute("UPDATE devices SET customer_id = %s, serial_number = %s, device_type = %s, device_model = %s, device_ip = %s WHERE id = %s", (customer_id, serial_number, device_type, device_model, device_ip, id))
    conn.commit()
    conn.close()
    return cursor.rowcount

def delete_device(id):
    """Permanently delete a device by ID."""
    conn = connect_to_db()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM devices WHERE id = %s", (id,))
    conn.commit()
    return cursor.rowcount

def get_devices_by_customer_id(customer_id):
    """Fetch all devices for a specific customer."""
    conn = connect_to_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM devices WHERE customer_id = %s", (customer_id,))
    devices = cursor.fetchall()
    return devices
