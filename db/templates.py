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


def create_template(name, description, command, customer_id, general_desc, premade_report, manual_summary_desc=None, manual_summary_table=None, company_logo=None):
    """Insert a template; description and command are JSON arrays. Returns new row id."""
    conn = connect_to_db()
    cursor = conn.cursor()
    cursor.execute(
        """INSERT INTO command_templates 
           (name, description, command, customer_id, general_desc, premade_report, manual_summary_desc, manual_summary_table, company_logo) 
           VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)""", 
        (name, json.dumps(description), json.dumps(command), customer_id, general_desc, premade_report, manual_summary_desc, json.dumps(manual_summary_table) if manual_summary_table else None, company_logo)
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
            'premade_report': template['premade_report'],
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
    
    if template:
        # Parse JSON fields
        template['command'] = json.loads(template['command']) if isinstance(template['command'], str) else template['command']
        template['description'] = json.loads(template['description']) if isinstance(template['description'], str) else template['description']
        template['manual_summary_table'] = json.loads(template['manual_summary_table']) if isinstance(template['manual_summary_table'], str) else template['manual_summary_table']
    
    return template

import json

def update_template(
    id,
    name,
    description,
    command,
    customer_id,
    general_desc,
    update_time,
    manual_summary_desc=None,
    manual_summary_table=None,
    premade_report=None,
    company_logo=None
):

    conn = connect_to_db()
    cursor = conn.cursor()

    # Ensure JSON fields are serialized safely
    description_json = json.dumps(description) if not isinstance(description, str) else description
    command_json = json.dumps(command) if not isinstance(command, str) else command

    manual_summary_json = None
    if manual_summary_table:
        if isinstance(manual_summary_table, str):
            # Already a JSON string
            manual_summary_json = manual_summary_table
        elif isinstance(manual_summary_table, list):
            # It's a list, need to serialize
            try:
                manual_summary_json = json.dumps(manual_summary_table)
            except TypeError:
                # Clean bytes if they exist
                cleaned = []
                for row in manual_summary_table:
                    if isinstance(row, dict):
                        cleaned_row = {
                            k: (v.decode("utf-8", "ignore") if isinstance(v, (bytes, bytearray)) else v)
                            for k, v in row.items()
                        }
                        cleaned.append(cleaned_row)
                    else:
                        # Skip non-dict items
                        pass
                manual_summary_json = json.dumps(cleaned)

    cursor.execute(
        """
        UPDATE command_templates
        SET name = %s,
            description = %s,
            command = %s,
            customer_id = %s,
            general_desc = %s,
            update_time = %s,
            manual_summary_desc = %s,
            manual_summary_table = %s,
            premade_report = %s,
            company_logo = %s
        WHERE id = %s
        """,
        (
            name,
            description_json,
            command_json,
            customer_id,
            general_desc,
            update_time,
            manual_summary_desc,
            manual_summary_json,
            premade_report,
            company_logo,
            id,
        ),
    )

    conn.commit()
    rows = cursor.rowcount

    cursor.close()
    conn.close()

    return rows


