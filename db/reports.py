import mysql.connector
from db.connect_to_db import connect_to_db
from datetime import datetime
from fpdf import FPDF
from db.devices import get_device_by_id
from db.customer import get_customer_by_id
from db.templates import get_template_by_id



pdf = FPDF()

def create_report(device_id, customer_id, template_id, result):
    conn = connect_to_db()
    cursor = conn.cursor()
    cursor.execute("INSERT INTO reports (device_id, customer_id, template_id, result) VALUES (%s, %s, %s, %s)", 
                   (device_id, customer_id, template_id, result))
    conn.commit()
    return cursor.lastrowid

def get_reports():
    conn = connect_to_db()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM reports")
    reports = cursor.fetchall()
    return reports

def get_report_by_id(id):
    conn = connect_to_db()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM reports WHERE id = %s", (id,))
    reports = cursor.fetchone()
    return reports

def delete_report(id):
    conn = connect_to_db()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM reports WHERE id = %s", (id,))
    conn.commit()
    return cursor.rowcount
