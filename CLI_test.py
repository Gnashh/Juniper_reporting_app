from db.connect_to_db import connect_to_db
from db.customer import create_customer,get_customers,get_customer_by_id,update_customer,delete_customer
from db.devices import create_device,get_devices,get_device_by_id,update_device,delete_device,get_device_by_customer_id
from db.templates import create_template,get_templates,delete_template,get_template_by_id
from db.reports import create_report,get_reports,get_report_by_id,generate_pdf
from juniper_service import connect_to_device,close_connection,get_chassis_RE,get_chassis_hardware,get_chassis_fru,get_chassis_environment
import paramiko
import json


device = get_device_by_id(1)
client = connect_to_device(device["device_ip"], device["username"], device["password"])

print("CONNECTED TO DEVICE")

def execute_template(template_id):
    template = get_template_by_id(template_id)
    command = json.loads(template["command"])
    
    all_results = []
    overall_status = "Success"
    
    for i in command:
        if i == "show chassis routing-engine":
            result = get_chassis_RE(client)
        elif i == "show chassis fru":
            result = get_chassis_fru(client)
        elif i == "show chassis environment":
            result = get_chassis_environment(client)
        elif i == "show chassis hardware":
            result = get_chassis_hardware(client)
        else: 
            print("Command not found")
            continue
        
        if result == "":
            overall_status = "Failed"
        
        all_results.append(f"Command: {i}\n{result}\n{'='*88}\n")
    
    combined_result = "\n".join(all_results)
    device_id = device["id"]
    customer_id = device["customer_id"]
    
    return create_report(device_id, customer_id, template_id, combined_result, overall_status)
execute_template(1)
    
close_connection(client)


cli_output = get_report_by_id(3)["result"]
generate_pdf(5)


