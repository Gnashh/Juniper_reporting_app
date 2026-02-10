import mysql.connector    # import mysql.connector  
from db.connect_to_db import connect_to_db

def get_customers():
    conn = connect_to_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM customers")
    customers = cursor.fetchall()
    return customers

def get_customer_by_id(id):
    conn = connect_to_db()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM customers WHERE id = %s", (id,))
    customer = cursor.fetchone()
    return customer

def create_customer(name, email, jump_host, jump_host_ip=None, jump_host_username=None, jump_host_password=None, image=None):
    conn = connect_to_db()
    cursor = conn.cursor()
    
    # Convert image to binary if provided
    image_data = None
    if image is not None:
        image_data = image.read()
    
    cursor.execute(
        "INSERT INTO customers (name, email, jump_host, jump_host_ip, jump_host_username, jump_host_password, images) VALUES (%s, %s, %s, %s, %s, %s, %s)", 
        (name, email, jump_host, jump_host_ip, jump_host_username, jump_host_password, image_data)
    )
    conn.commit()
    return cursor.lastrowid

def update_customer(id, name, email, jump_host, jump_host_ip, jump_host_username, jump_host_password, image=None):
    conn = connect_to_db()
    cursor = conn.cursor()
    
    # Only update image if a new one is provided
    if image is not None:
        image_data = image.read()
        cursor.execute(
            "UPDATE customers SET name = %s, email = %s, jump_host = %s, jump_host_ip = %s, jump_host_username = %s, jump_host_password = %s, images = %s WHERE id = %s", 
            (name, email, jump_host, jump_host_ip, jump_host_username, jump_host_password, image_data, id)
        )
    else:
        # Don't update image column if no new image provided
        cursor.execute(
            "UPDATE customers SET name = %s, email = %s, jump_host = %s, jump_host_ip = %s, jump_host_username = %s, jump_host_password = %s WHERE id = %s", 
            (name, email, jump_host, jump_host_ip, jump_host_username, jump_host_password, id)
        )
    
    conn.commit()
    return cursor.rowcount

def delete_customer(id):
    conn = connect_to_db()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM customers WHERE id = %s", (id,))
    conn.commit()
    return cursor.rowcount


