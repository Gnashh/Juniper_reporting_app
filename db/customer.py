"""
Customer Database Module
======================
CRUD operations for the customers table.
Supports jump host configuration and optional logo image storage.
"""

import mysql.connector
from db.connect_to_db import connect_to_db


def get_customers():
    """Fetch all customers; returns list of tuples."""
    conn = connect_to_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM customers")
    customers = cursor.fetchall()
    return customers

def get_customer_by_id(id):
    """Fetch a single customer by ID; returns dict or None."""
    conn = connect_to_db()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM customers WHERE id = %s", (id,))
    customer = cursor.fetchone()
    return customer

def create_customer(name, email, jump_host, jump_host_ip=None, jump_host_username=None, jump_host_password=None, image=None, device_type=None):
    """Insert a new customer; returns the new row id."""
    conn = connect_to_db()
    cursor = conn.cursor()
    
    # Convert image to binary if provided
    image_data = None
    if image is not None:
        image_data = image.read()
    
    cursor.execute(
        "INSERT INTO customers (name, email, jump_host, jump_host_ip, jump_host_username, jump_host_password, images, device_type) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)", 
        (name, email, jump_host, jump_host_ip, jump_host_username, jump_host_password, image_data, device_type)        
    )
    conn.commit()
    return cursor.lastrowid

def update_customer(id, name, email, jump_host, jump_host_ip, jump_host_username, jump_host_password, image=None, device_type=None):
    """Update customer; image is only updated if a new file is provided."""
    conn = connect_to_db()
    cursor = conn.cursor()
    
    # Only update image if a new one is provided
    if image is not None:
        image_data = image.read()
        cursor.execute(
            "UPDATE customers SET name = %s, email = %s, jump_host = %s, jump_host_ip = %s, jump_host_username = %s, jump_host_password = %s, images = %s, device_type = %s WHERE id = %s", 
            (name, email, jump_host, jump_host_ip, jump_host_username, jump_host_password, image_data, device_type, id)            
        )
    else:
        # Don't update image column if no new image provided
        cursor.execute(
            "UPDATE customers SET name = %s, email = %s, jump_host = %s, jump_host_ip = %s, jump_host_username = %s, jump_host_password = %s, device_type = %s WHERE id = %s", 
            (name, email, jump_host, jump_host_ip, jump_host_username, jump_host_password, device_type, id)            
        )
    
    conn.commit()
    return cursor.rowcount

def delete_customer(id):
    """Permanently delete a customer by ID."""
    conn = connect_to_db()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM customers WHERE id = %s", (id,))
    conn.commit()
    return cursor.rowcount


