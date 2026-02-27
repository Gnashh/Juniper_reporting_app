"""
Template Database Module
=======================
CRUD operations for command templates.
Templates store lists of Juniper CLI commands (JSON) with descriptions.
"""

import mysql.connector
from db.connect_to_db import connect_to_db
import json
from db.customer import get_customer_by_id
from datetime import datetime


def create_template(name, description, command, customer_id, general_desc, manual_summary_desc=None, manual_summary_table=None):
    """Insert a template; description and command are JSON arrays. Returns new row id."""
    conn = connect_to_db()
    cursor = conn.cursor()
    cursor.execute(
        """INSERT INTO command_templates 
           (name, description, command, customer_id, general_desc, manual_summary_desc, manual_summary_table) 
           VALUES (%s, %s, %s, %s, %s, %s, %s)""", 
        (name, json.dumps(description), json.dumps(command), customer_id, general_desc, manual_summary_desc, json.dumps(manual_summary_table) if manual_summary_table else None)
    )
    conn.commit()
    template_id = cursor.lastrowid
    conn.close()
    return template_id

def get_templates_by_customer_id(customer_id):
    """Fetch all templates for a customer; parses JSON fields into Python lists."""
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
            'general_desc': template['general_desc'],
            'update_time': template['update_time'],
            'manual_summary_desc': template['manual_summary_desc'],
            'manual_summary_table': json.loads(template['manual_summary_table']) if isinstance(template['manual_summary_table'], str) else template['manual_summary_table'],
        })
    
    return parsed_templates

def delete_template(id):
    """Permanently delete a template by ID."""
    conn = connect_to_db()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM command_templates WHERE id = %s", (id,))
    conn.commit()
    conn.close()
    return cursor.rowcount

def get_template_by_id(id):
    """Fetch a single template by ID; returns dict or None."""
    conn = connect_to_db()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM command_templates WHERE id = %s", (id,))
    template = cursor.fetchone()
    conn.close()
    return template

def update_template(id, name, description, command, customer_id, general_desc, update_time, manual_summary_desc=None, manual_summary_table=None):
    """Update a template; description and command must be Python lists (serialized to JSON)."""
    conn = connect_to_db()
    cursor = conn.cursor()
    cursor.execute("UPDATE command_templates SET name = %s, description = %s, command = %s, customer_id = %s, general_desc = %s, update_time = %s, manual_summary_desc = %s, manual_summary_table = %s WHERE id = %s", 
                   (name, json.dumps(description), json.dumps(command), customer_id, general_desc, update_time, manual_summary_desc, json.dumps(manual_summary_table) if manual_summary_table else None, id))
    conn.commit()
    conn.close()
    return cursor.rowcount


