"""
Report Database Module
======================
CRUD operations for reports.
Reports store JSON result of command executions (device + template).
"""

import mysql.connector
from db.connect_to_db import connect_to_db
from datetime import datetime
from fpdf import FPDF
from db.devices import get_device_by_id
from db.customer import get_customer_by_id
from db.templates import get_template_by_id
import json


pdf = FPDF()


def create_report(device_id, customer_id, template_id, results, ai_summary):
    """Insert a new report; results (list of dicts) is serialized to JSON."""
    conn = connect_to_db()
    cursor = conn.cursor()
    # Convert results to JSON string
    results_json = json.dumps(results)
    
    cursor.execute("""
        INSERT INTO reports (device_id, customer_id, template_id, result, aisummary)
        VALUES (%s, %s, %s, %s, %s)
    """, (device_id, customer_id, template_id, results_json, ai_summary))
    
    conn.commit()
    conn.close()

def get_reports():
    """Fetch all reports; returns list of dicts."""
    conn = connect_to_db()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM reports")
    reports = cursor.fetchall()
    return reports

def get_report_by_id(id):
    """Fetch a single report by ID; returns dict or None."""
    conn = connect_to_db()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM reports WHERE id = %s", (id,))
    reports = cursor.fetchone()
    return reports

def delete_report(id):
    """Permanently delete a report by ID."""
    conn = connect_to_db()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM reports WHERE id = %s", (id,))
    conn.commit()
    return cursor.rowcount
