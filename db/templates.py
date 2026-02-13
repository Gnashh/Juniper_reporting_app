import mysql.connector
from db.connect_to_db import connect_to_db
import json
from db.customer import get_customer_by_id


def create_template(name, description, command, customer_id, jump_host, general_desc):
    conn = connect_to_db()
    cursor = conn.cursor()
    cursor.execute("INSERT INTO command_templates (name, description, command, customer_id, jump_host, general_desc) VALUES (%s, %s, %s, %s, %s, %s)", 
                   (name, json.dumps(description), json.dumps(command), customer_id, jump_host, general_desc))
    conn.commit()
    template_id = cursor.lastrowid
    conn.close()
    return template_id

def get_templates_by_customer_id(customer_id):
    conn = connect_to_db()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM command_templates WHERE customer_id = %s", (customer_id,))

    templates = cursor.fetchall()
    conn.close()
    
    parsed_templates = []
    for template in templates:
        parsed_templates.append({
            'id': template['id'],
            'name': template['name'],
            'description': json.loads(template['description']) if isinstance(template['description'], str) else template['description'],
            'command': json.loads(template['command']) if isinstance(template['command'], str) else template['command'],
            'customer_id': template['customer_id'],
            'created_at': template['created_at'],
            'jump_host': template['jump_host'],
            'general_desc': template['general_desc']
        })
    
    return parsed_templates

def delete_template(id):
    conn = connect_to_db()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM command_templates WHERE id = %s", (id,))
    conn.commit()
    conn.close()
    return cursor.rowcount

def get_template_by_id(id):
    conn = connect_to_db()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM command_templates WHERE id = %s", (id,))
    template = cursor.fetchone()
    conn.close()
    return template

def update_template(id, name, description, command, customer_id, jump_host, general_desc):
    conn = connect_to_db()
    cursor = conn.cursor()
    cursor.execute("UPDATE command_templates SET name = %s, description = %s, command = %s, customer_id = %s, jump_host = %s, general_desc = %s WHERE id = %s", 
                   (name, json.dumps(description), json.dumps(command), customer_id, jump_host, general_desc, id))
    conn.commit()
    conn.close()
    return cursor.rowcount


