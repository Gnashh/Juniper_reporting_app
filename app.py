import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

import streamlit as st
from streamlit_option_menu import option_menu
import re
import json
import base64
import pandas as pd
from db.connect_to_db import connect_to_db
from db.customer import create_customer, get_customers, get_customer_by_id, update_customer, delete_customer
from db.devices import create_device, get_devices, get_device_by_id, get_devices_by_customer_id, delete_device, update_device
from db.templates import get_template_by_id, create_template, delete_template, get_templates_by_customer_id, update_template
from db.reports import get_report_by_id, create_report, delete_report
from juniper_service import connect_to_device, close_connection, run_command, connect_via_jump_host
from gen_PDF import generate_pdf
from PIL import Image


# -----------------------------
# Page config
# -----------------------------
st.set_page_config(
    page_title="Internship",
    page_icon=":bar_chart:",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.title("Simple Reporting App")

# -----------------------------
# Sidebar menu
# -----------------------------
with st.sidebar:
    selected = option_menu(
        menu_title="MAIN MENU",
        options=[
            "Customer Details",
            "Device Details",
            "Template Details",
            "Report Details and Generate Report"
        ]
    )

# -----------------------------
# Customer Dialogs
# -----------------------------
@st.dialog("Add New Customer")
def add_customer_dialog():
    # Jump host selection OUTSIDE form for dynamic updates
    jump_host = st.radio("Jump Host?", ["No", "Yes"], index=0, key="add_customer_jump_host")
    
    with st.form("add_customer_form", clear_on_submit=True):
        name = st.text_input("Name")
        email = st.text_input("Email")
        image = st.file_uploader("Upload Image, optional, 1x1 recommended", type=["jpg", "jpeg", "png"])
        
        # Conditionally show jump host fields based on selection
        if jump_host == "Yes":
            jump_host_ip = st.text_input("Jump Host IP")
            jump_host_username = st.text_input("Jump Host Username")
            jump_host_password = st.text_input("Jump Host Password", type="password")
        else:
            jump_host_ip = None
            jump_host_username = None
            jump_host_password = None
        
        col1, col2 = st.columns(2)
        with col1:
            cancel_btn = st.form_submit_button("❌ Cancel", use_container_width=True)
        with col2:
            submit_btn = st.form_submit_button("✅ Submit", use_container_width=True)
    
    if cancel_btn:
        st.session_state.show_add_customer = False
        st.rerun()
    
    if not submit_btn:
        return

    # Validation
    if not name or not email:
        st.error("Please fill all required fields")
        return
    if not re.match(r"[^@]+@[^@]+\.[^@]+", email):
        st.error("Please enter a valid email address")
        return
    
    # Validate jump host fields if jump host is enabled
    if jump_host == "Yes":
        if not jump_host_ip or not jump_host_username or not jump_host_password:
            st.error("Please fill all jump host fields")
            return
    
    # Normalize value for DB (convert to integer: 1 for Yes, 0 for No)
    jump_host_value = 1 if jump_host == "Yes" else 0

    # Database insert
    try:
        create_customer(name, email, jump_host_value, jump_host_ip, jump_host_username, jump_host_password, image)
        st.success("Customer added successfully")
        st.session_state.show_add_customer = False
        st.rerun()
    except Exception as e:
        st.error(f"Failed to add customer: {str(e)}")


@st.dialog("Confirm Delete")
def delete_customer_dialog(customer_ids):
    st.warning(f"⚠️ Are you sure you want to delete {len(customer_ids)} customer(s)?")
    st.caption("This action cannot be undone.")
    
    col1, col2 = st.columns(2)
    with col1:
        if st.button("❌ Cancel", key="cancel_delete"):
            st.session_state.show_delete_customer = False
            st.rerun()
    
    with col2:
        if st.button("✅ Yes, Delete", key="confirm_delete"):
            try:
                for cust_id in customer_ids:
                    delete_customer(cust_id)
                st.success(f"Deleted {len(customer_ids)} customer(s)")
                st.session_state.show_delete_customer = False
                st.rerun()
            except Exception as e:
                st.error(f"Failed to delete customers: {str(e)}")


@st.dialog("Update Customer(s)")
def update_customer_dialog(selected_customers):
    """
    Fixed dialog that handles updating multiple customers at once.
    Each customer gets its own form fields.
    """
    st.write(f"Updating {len(selected_customers)} customer(s)")
    
    # Store form data in session state to preserve across reruns
    if "update_forms_data" not in st.session_state:
        st.session_state.update_forms_data = {}
    
    with st.form("update_customers_form", clear_on_submit=False):
        updated_data = []
        
        # Create form fields for each selected customer
        for idx, (_, customer) in enumerate(selected_customers.iterrows()):
            customer_id = customer["Customer ID"]
            
            # Fetch full customer data from database to get jump host fields
            from db.customer import get_customer_by_id
            full_customer = get_customer_by_id(customer_id)
            
            st.markdown(f"### Customer ID: {customer_id}")
            
            # Pre-fill with existing values
            name = st.text_input(
                "Name",
                value=customer["Customer Name"],
                key=f"name_{customer_id}"
            )
            email = st.text_input(
                "Email",
                value=customer["Email"],
                key=f"email_{customer_id}"
            )
            
            image = st.file_uploader("Upload Image, optional, 1x1 recommended", type=["jpg", "jpeg", "png"], key=f"image_{customer_id}")

            # Convert jump_host to proper case for selectbox
            current_jump_host = customer["Jump Host"]
            if isinstance(current_jump_host, str):
                jump_host_default = "Yes" if current_jump_host.lower() == "yes" else "No"
            else:
                jump_host_default = "No"
                
            jump_host = st.radio(
                "Jump Host?",
                ["No", "Yes"],
                index=1 if jump_host_default == "Yes" else 0,
                key=f"jump_host_{customer_id}"
            )
            if jump_host == "Yes":
                jump_host_ip = st.text_input(
                    "Jump Host IP", 
                    value=full_customer.get("jump_host_ip") or "",
                    key=f"jump_host_ip_{customer_id}"
                )
                jump_host_username = st.text_input(
                    "Jump Host Username", 
                    value=full_customer.get("jump_host_username") or "",
                    key=f"jump_host_username_{customer_id}"
                )
                jump_host_password = st.text_input(
                    "Jump Host Password", 
                    value=full_customer.get("jump_host_password") or "",
                    type="password",
                    key=f"jump_host_password_{customer_id}"
                )
            else:
                # Keep existing values even when jump host is No
                jump_host_ip = full_customer.get("jump_host_ip")
                jump_host_username = full_customer.get("jump_host_username")
                jump_host_password = full_customer.get("jump_host_password")
            
            updated_data.append({
                "id": customer_id,
                "name": name,
                "email": email,
                "image": image,
                "jump_host": jump_host,
                "jump_host_ip": jump_host_ip,
                "jump_host_username": jump_host_username,
                "jump_host_password": jump_host_password
            })
            
            if idx < len(selected_customers) - 1:
                st.divider()
        
        # Form buttons
        col1, col2 = st.columns(2)
        with col1:
            cancel_btn = st.form_submit_button("❌ Cancel", use_container_width=True)
        with col2:
            submit_btn = st.form_submit_button("✅ Update All", use_container_width=True)
        
        if cancel_btn:
            st.session_state.show_update_customer = False
            if "update_forms_data" in st.session_state:
                del st.session_state.update_forms_data
            st.rerun()
        
        if submit_btn:
            # Validate all entries
            all_valid = True
            for data in updated_data:
                if not data["name"] or not data["email"]:
                    st.error(f"Customer ID {data['id']}: Please fill all required fields")
                    all_valid = False
                elif not re.match(r"[^@]+@[^@]+\.[^@]+", data["email"]):
                    st.error(f"Customer ID {data['id']}: Please enter a valid email address")
                    all_valid = False
            
            if all_valid:
                # Update all customers
                success_count = 0
                for data in updated_data:
                    try:
                        jump_host_value = 1 if data["jump_host"] == "Yes" else 0
                        update_customer(data["id"], data["name"], data["email"], jump_host_value, data["jump_host_ip"], data["jump_host_username"], data["jump_host_password"], data["image"])
                        success_count += 1
                    except Exception as e:
                        st.error(f"Failed to update Customer ID {data['id']}: {str(e)}")
                
                if success_count > 0:
                    st.success(f"Successfully updated {success_count} customer(s)")
                
                st.session_state.show_update_customer = False
                if "update_forms_data" in st.session_state:
                    del st.session_state.update_forms_data
                st.rerun()

# -----------------------------
# Device Dialogs
# -----------------------------
@st.dialog("Add New Device")
def add_device_dialog():
    with st.form("add_device_form", clear_on_submit=True):
        # Get customers
        customers_data = get_customers()
        customers_df = pd.DataFrame(customers_data, columns=["id", "name", "email", "created_at", "jump_host", "jump_host_ip", "jump_host_username", "jump_host_password"])
        
        # Create name -> id mapping
        customer_options = {row['name']: row['id'] for _, row in customers_df.iterrows()}
        
        selected_customer_name = st.selectbox("Customer", list(customer_options.keys()))
        customer_id = customer_options[selected_customer_name]
        
        serial_number = st.text_input("Serial Number")
        device_type = st.selectbox("Device Type", ["Router", "Switch", "Firewall"])
        device_model = st.text_input("Device Model")
        device_ip = st.text_input("Device IP")
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        
        # Add Cancel and Submit buttons
        col1, col2 = st.columns(2)
        with col1:
            cancel_btn = st.form_submit_button("❌ Cancel", use_container_width=True)
        with col2:
            submit_btn = st.form_submit_button("✅ Submit", use_container_width=True)
    
    if cancel_btn:
        st.session_state.show_add_device = False
        st.rerun()
    
    if not submit_btn:
        return

    # Validation
    if not selected_customer_name or not serial_number or not device_type or not device_model or not device_ip or not username or not password:
        st.error("Please fill all required fields")
        return
    
    # Database insert with customer_id
    try:
        create_device(customer_id, serial_number, device_type, device_model, device_ip, username, password)
        st.success("Device added successfully")
        st.session_state.show_add_device = False
        st.rerun()
    except Exception as e:
        st.error(f"Failed to add device: {str(e)}")

@st.dialog("Confirm Delete Devices")
def delete_device_dialog(device_ids):
    st.warning(f"⚠️ Are you sure you want to delete {len(device_ids)} device(s)?")
    st.caption("This action cannot be undone.")
    
    col1, col2 = st.columns(2)
    with col1:
        if st.button("❌ Cancel", key="cancel_delete_device"):
            st.session_state.show_delete_device = False
            st.rerun()
    
    with col2:
        if st.button("✅ Yes, Delete", key="confirm_delete_device"):
            try:
                for device_id in device_ids:
                    delete_device(device_id)
                st.success(f"Deleted {len(device_ids)} device(s)")
                st.session_state.show_delete_device = False
                st.rerun()
            except Exception as e:
                st.error(f"Failed to delete devices: {str(e)}")


@st.dialog("Update Device(s)")
def update_device_dialog(selected_devices):
    """Update multiple devices at once"""
    st.write(f"Updating {len(selected_devices)} device(s)")
    
    if "update_forms_data" not in st.session_state:
        st.session_state.update_forms_data = {}
    
    with st.form("update_devices_form", clear_on_submit=False):
        updated_data = []
        
        # Get customers for dropdown
        customers_data = get_customers()
        customers_df = pd.DataFrame(customers_data, columns=["id", "name", "email", "created_at", "jump_host", "jump_host_ip", "jump_host_username", "jump_host_password"])
        customer_options = {row['name']: row['id'] for _, row in customers_df.iterrows()}
        customer_names = list(customer_options.keys())
        
        for idx, (_, device) in enumerate(selected_devices.iterrows()):
            device_id = device["Device ID"]
            
            st.markdown(f"### Device ID: {device_id}")
            
            # Customer dropdown
            current_customer = device.get("Customer Name", "")
            customer_index = customer_names.index(current_customer) if current_customer in customer_names else 0
            
            selected_customer = st.selectbox(
                "Customer",
                customer_names,
                index=customer_index,
                key=f"customer_{device_id}"
            )
            customer_id = customer_options[selected_customer]
            
            serial_number = st.text_input(
                "Serial Number",
                value=device["Serial Number"],
                key=f"serial_{device_id}"
            )
            
            device_type = st.selectbox(
                "Device Type",
                ["Router", "Switch", "Firewall"],
                index=["Router", "Switch", "Firewall"].index(device["Device Type"]) if device["Device Type"] in ["Router", "Switch", "Firewall"] else 0,
                key=f"type_{device_id}"
            )
            
            device_model = st.text_input(
                "Device Model",
                value=device["Device Model"],
                key=f"model_{device_id}"
            )
            
            device_ip = st.text_input(
                "Device IP",
                value=device["Device IP"],
                key=f"ip_{device_id}"
            )
            
            updated_data.append({
                "id": device_id,
                "customer_id": customer_id,
                "serial_number": serial_number,
                "device_type": device_type,
                "device_model": device_model,
                "device_ip": device_ip
            })
            
            if idx < len(selected_devices) - 1:
                st.divider()
        
        col1, col2 = st.columns(2)
        with col1:
            cancel_btn = st.form_submit_button("❌ Cancel", use_container_width=True)
        with col2:
            submit_btn = st.form_submit_button("✅ Update All", use_container_width=True)
        
        if cancel_btn:
            st.session_state.show_update_device = False
            if "update_forms_data" in st.session_state:
                del st.session_state.update_forms_data
            st.rerun()
        
        if submit_btn:
            all_valid = True
            for data in updated_data:
                if not data["serial_number"] or not data["device_model"] or not data["device_ip"]:
                    st.error(f"Device ID {data['id']}: Please fill all required fields")
                    all_valid = False
            
            if all_valid:
                success_count = 0
                for data in updated_data:
                    try:
                        update_device(data["id"], data["customer_id"], data["serial_number"], 
                                    data["device_type"], data["device_model"], data["device_ip"])
                        success_count += 1
                    except Exception as e:
                        st.error(f"Failed to update Device ID {data['id']}: {str(e)}")
                
                if success_count > 0:
                    st.success(f"Successfully updated {success_count} device(s)")
                
                st.session_state.show_update_device = False
                if "update_forms_data" in st.session_state:
                    del st.session_state.update_forms_data
                st.rerun()

# -----------------------------
# Template Dialogs
# -----------------------------
@st.dialog("Add New Template")
def add_template_dialog():

    # Jump host selection OUTSIDE form for dynamic updates
    jump_host = st.radio("Jump Host?", ["No", "Yes"], index=0, key="add_template_jump_host")

    # Get and filter customers OUTSIDE form
    customers_data = get_customers()
    customers_df = pd.DataFrame(customers_data, columns=["id", "name", "email",  "jump_host", "created_at", "jump_host_ip", "jump_host_username", "jump_host_password", "images"])
    
    # Filter customers based on jump_host selection
    if jump_host == "Yes":
        filtered_customers = customers_df[customers_df['jump_host'] == 1]
    else:
        filtered_customers = customers_df  # Show ALL customers when "No" is selected
    
    if filtered_customers.empty:
        st.warning(f"No customers found with jump host = {jump_host}")
        st.info("Please create a customer with the appropriate jump host setting first, or change the jump host selection above.")
        if st.button("Close"):
            st.session_state.show_add_template = False
            st.rerun()
        return
    
    # Customer selection OUTSIDE form so it can trigger updates
    customer_options = {row['name']: row['id'] for _, row in filtered_customers.iterrows()}
    selected_customer_name = st.selectbox("Customer", list(customer_options.keys()), key="template_customer_select")
    customer_id = customer_options[selected_customer_name]

    # Form for template details
    with st.form("add_template_form", clear_on_submit=True):
        
        name = st.text_input("Template Name")
        description = st.text_area("Description")
        
        # Predefined commands
        predefined_commands = [
            "show version",
            "show chassis routing-engine",
            "show chassis hardware",
            "show chassis environment",
            "show system uptime",
            "show interfaces terse",
            "show system alarms",
            "show chassis alarms"
        ]

        command = st.multiselect("Predefined Commands", predefined_commands)
        
        # Custom commands
        st.markdown("**Add custom commands (ONE PER LINE AS SHOWN BELOW):**")
        custom_commands_text = st.text_area("Custom Commands", placeholder="show version\nshow interfaces\nshow route")

        # Combine all commands
        final_commands = command.copy()
        if custom_commands_text:
            custom_list = [cmd.strip() for cmd in custom_commands_text.split('\n') if cmd.strip()]
            final_commands.extend(custom_list)
        
        # Show all selected commands
        if final_commands:
            st.success(f"Total commands: {len(final_commands)}")
            with st.expander("View all commands"):
                for idx, cmd in enumerate(final_commands, 1):
                    st.write(f"{idx}. {cmd}")
        
        col1, col2 = st.columns(2)
        with col1:
            cancel_btn = st.form_submit_button("❌ Cancel", use_container_width=True)
        with col2:
            submit_btn = st.form_submit_button("✅ Submit", use_container_width=True)
    
    if cancel_btn:
        st.session_state.show_add_template = False
        st.rerun()
    
    if not submit_btn:
        return

    # Validation for template details form
    if not name or not description or not final_commands:
        st.error("Please fill all required fields and add at least one command")
        return
    
    jump_host_bool = True if jump_host == "Yes" else False
    
    try:
        create_template(name, description, final_commands, customer_id, jump_host_bool)
        st.success("Template added successfully")
        st.session_state.show_add_template = False
        st.rerun()
    except Exception as e:
        st.error(f"Failed to add template: {str(e)}")


@st.dialog("Confirm Delete Template")
def delete_template_dialog(template_ids):
    st.warning(f"⚠️ Are you sure you want to delete {len(template_ids)} template(s)?")
    st.caption("This action cannot be undone.")
    
    col1, col2 = st.columns(2)
    with col1:
        if st.button("❌ Cancel", key="cancel_delete_template"):
            st.session_state.show_delete_template = False
            st.rerun()
    
    with col2:
        if st.button("✅ Yes, Delete", key="confirm_delete_template"):
            try:
                for template_id in template_ids:
                    delete_template(template_id)
                st.success(f"Deleted {len(template_ids)} template(s)")
                st.session_state.show_delete_template = False
                st.rerun()
            except Exception as e:
                st.error(f"Failed to delete templates: {str(e)}")


@st.dialog("Update Template(s)")
def update_template_dialog(selected_templates):
    """Update multiple templates at once"""
    st.write(f"Updating {len(selected_templates)} template(s)")
    
    if "update_forms_data" not in st.session_state:
        st.session_state.update_forms_data = {}
    
    with st.form("update_templates_form", clear_on_submit=False):
        updated_data = []
        
        # Get customers for dropdown
        customers_data = get_customers()
        customers_df = pd.DataFrame(customers_data, columns=["id", "name", "email", "created_at", "jump_host", "jump_host_ip", "jump_host_username", "jump_host_password"])
        customer_options = {row['name']: row['id'] for _, row in customers_df.iterrows()}
        customer_names = list(customer_options.keys())
        
        for idx, (_, template) in enumerate(selected_templates.iterrows()):
            template_id = template["Template ID"]
            
            st.markdown(f"### Template ID: {template_id}")
            
            # Customer dropdown
            current_customer = template.get("Customer Name", "")
            customer_index = customer_names.index(current_customer) if current_customer in customer_names else 0
            
            selected_customer = st.selectbox(
                "Customer",
                customer_names,
                index=customer_index,
                key=f"customer_{template_id}"
            )
            customer_id = customer_options[selected_customer]
            
            name = st.text_input(
                "Template Name",
                value=template["Name"],
                key=f"name_{template_id}"
            )
            
            description = st.text_area(
                "Description",
                value=template["Description"],
                key=f"desc_{template_id}"
            )
            
            command = st.text_area(
                "Command (JSON format)",
                value=template.get("Command", ""),
                key=f"cmd_{template_id}"
            )
            
            updated_data.append({
                "id": template_id,
                "customer_id": customer_id,
                "name": name,
                "description": description,
                "command": command
            })
            
            if idx < len(selected_templates) - 1:
                st.divider()
        
        col1, col2 = st.columns(2)
        with col1:
            cancel_btn = st.form_submit_button("❌ Cancel", use_container_width=True)
        with col2:
            submit_btn = st.form_submit_button("✅ Update All", use_container_width=True)
        
        if cancel_btn:
            st.session_state.show_update_template = False
            if "update_forms_data" in st.session_state:
                del st.session_state.update_forms_data
            st.rerun()
        
        if submit_btn:
            all_valid = True
            for data in updated_data:
                if not data["name"] or not data["description"] or not data["command"]:
                    st.error(f"Template ID {data['id']}: Please fill all required fields")
                    all_valid = False
            
            if all_valid:
                success_count = 0
                for data in updated_data:
                    try:
                        update_template(data["id"], data["name"], data["description"], data["command"], data["customer_id"])
                        success_count += 1
                    except Exception as e:
                        st.error(f"Failed to update Template ID {data['id']}: {str(e)}")
                
                if success_count > 0:
                    st.success(f"Successfully updated {success_count} template(s)")
                
                st.session_state.show_update_template = False
                if "update_forms_data" in st.session_state:
                    del st.session_state.update_forms_data
                st.rerun()

# -----------------------------
# Report Dialogs
# -----------------------------

@st.dialog("Create New Report")
def create_report_dialog():
    # Get customers first
    customers_data = get_customers()
    customers_df = pd.DataFrame(customers_data, columns=["id", "name", "email", "jump_host", "created_at", "jump_host_ip", "jump_host_username", "jump_host_password", "images"])
    
    if customers_df.empty:
        st.error("No customers found. Please create a customer first.")
        if st.button("Close"):
            st.session_state.show_create_report = False
            st.rerun()
        return
    
    customer_options = {row['name']: row['id'] for _, row in customers_df.iterrows()}
    
    # Customer selection OUTSIDE the form so it can trigger updates
    selected_customer_name = st.selectbox("Customer", list(customer_options.keys()), key="report_customer_select")
    customer_id = customer_options[selected_customer_name]
    
    # Get templates for selected customer
    templates_data = get_templates_by_customer_id(customer_id)
    
    # Get devices for selected customer
    devices_data = get_devices_by_customer_id(customer_id)
    
    # Check if customer has templates
    if not templates_data:
        st.warning(f"⚠️ Customer '{selected_customer_name}' has no templates.")
        st.info("Please create a template for this customer first.")
        if st.button("Close"):
            st.session_state.show_create_report = False
            st.rerun()
        return
    
    # Check if customer has devices
    if not devices_data:
        st.warning(f"⚠️ Customer '{selected_customer_name}' has no devices.")
        st.info("Please add a device for this customer first.")
        if st.button("Close"):
            st.session_state.show_create_report = False
            st.rerun()
        return
    
    # Both templates and devices exist - show the form
    with st.form("create_report_form", clear_on_submit=True):
        # Build template options
        template_options = {f"{t['name']} (ID: {t['id']})": t['id'] for t in templates_data}
        
        # Build device options
        device_options = {f"{d[2]} - {d[5]} (ID: {d[0]})": d[0] for d in devices_data}
        
        selected_template = st.selectbox("Template", list(template_options.keys()))
        template_id = template_options[selected_template]
        
        selected_device = st.selectbox("Device", list(device_options.keys()))
        device_id = device_options[selected_device]
        
        col1, col2 = st.columns(2)
        with col1:
            cancel_btn = st.form_submit_button("❌ Cancel", use_container_width=True)
        with col2:
            submit_btn = st.form_submit_button("✅ Submit", use_container_width=True)
    
    if cancel_btn:
        st.session_state.show_create_report = False
        st.rerun()
    
    if not submit_btn:
        return
    
    # Create report
    try:
        # Get template commands
        template = get_template_by_id(template_id)
        commands = json.loads(template['command']) if isinstance(template['command'], str) else template['command']
        
        # Get device details
        device = get_device_by_id(device_id)
        customer = get_customer_by_id(customer_id) # This is the customer details for the selected customer. It is used to connect to the device via the jump host if necessary.
        
        # Connect to device and execute commands
        with st.spinner("Connecting to device..."):
            if template["jump_host"] == 1:
                jump, client = connect_via_jump_host(
                    customer["jump_host_ip"],
                    customer["jump_host_username"],
                    customer["jump_host_password"],
                    device["device_ip"],
                    device["username"],
                    device["password"]
                )
            else:
                client = connect_to_device(
                    device["device_ip"],
                    device["username"],
                    device["password"]
                )

        all_results = []
        
        with st.spinner("Executing commands..."):
            for cmd in commands:
                try:
                    result = run_command(client, cmd)
                    all_results.append(f"Command: {cmd}\n{result}\n{'='*80}\n")
                except Exception as e:
                    all_results.append(f"Command: {cmd}\nError: {str(e)}\n{'='*80}\n")
        
        close_connection(client)
        
        combined_result = "\n".join(all_results)
        
        # Save report to database
        report_id = create_report(device_id, customer_id, template_id, combined_result)
        
        st.success(f"Report created successfully! Report ID: {report_id}")
        st.session_state.show_create_report = False
        st.rerun()
        
    except Exception as e:
        st.error(f"Failed to create report: {str(e)}")

@st.dialog("Confirm Delete Reports")
def delete_report_dialog(report_ids):
    st.warning(f"⚠️ Are you sure you want to delete {len(report_ids)} report(s)?")
    st.caption("This action cannot be undone.")
    
    col1, col2 = st.columns(2)
    with col1:
        if st.button("❌ Cancel", key="cancel_delete_report"):
            st.session_state.show_delete_report = False
            st.rerun()
    
    with col2:
        if st.button("✅ Yes, Delete", key="confirm_delete_report"):
            try:
                for report_id in report_ids:
                    delete_report(report_id)
                st.success(f"Deleted {len(report_ids)} report(s)")
                st.session_state.show_delete_report = False
                st.rerun()
            except Exception as e:
                st.error(f"Failed to delete reports: {str(e)}")

@st.dialog("Download Report")
def download_report_dialog(report_id):
    # Get report
    report = get_report_by_id(report_id)
    
    # Generate PDF
    pdf_path = generate_pdf(report_id)
    
    # Offer download
    with open(pdf_path, "rb") as f:
        st.download_button("Download Report", data=f, file_name=f"Report_{get_customer_by_id(report['customer_id'])['name']}.pdf") # This is the file name that will be generated. It includes the customer name.
    if st.button("Close"):
        st.session_state.show_view_report = False
        st.rerun()
    
# -----------------------------
# Customer Details Page
# -----------------------------
if selected == "Customer Details":

    st.subheader("Customer Details")

    # -----------------------------
    # Initialize session state ONCE
    # -----------------------------
    if "show_add_customer" not in st.session_state:
        st.session_state.show_add_customer = False

    if "show_delete_customer" not in st.session_state:
        st.session_state.show_delete_customer = False

    if "show_update_customer" not in st.session_state:
        st.session_state.show_update_customer = False

    # -----------------------------
    # Load data from MySQL (WITH IMPROVED ERROR HANDLING)
    # -----------------------------
    try:
        # Show loading indicator
        with st.spinner("Loading customer data..."):
            # Connect to database
            conn = connect_to_db()
            
            # Execute query with row limit for safety
            df = pd.read_sql("SELECT * FROM customers LIMIT 1000", conn)
            
            # Close connection
            conn.close()
            
    except Exception as e:
        st.error("⚠️ Failed to load customer data")
        st.error(f"Error: {str(e)}")
        st.stop()


    df = df.rename(columns={
        "id": "Customer ID",
        "name": "Customer Name",
        "email": "Email",
        "jump_host": "Jump Host",
        "created_at": "Created At",
        "jump_host_ip": "Jump Host IP",
        "jump_host_username": "Jump Host Username",
        "jump_host_password": "Jump Host Password",
        "images": "Images"
    })

    df["Jump Host"] = df["Jump Host"].apply(lambda x: "Yes" if x else "No")

    # ✅ Checkbox must be boolean
    df.insert(0, "Select", False)

    edited_df = st.data_editor(
        df,
        hide_index=True,
        use_container_width=True,
        column_config={
            "Select": st.column_config.CheckboxColumn(
                "Select",
                help="Select rows to delete",
                width="small"
            ),
            "Jump Host IP": None,  # Hide customer ID
            "Jump Host Username": None,
            "Jump Host Password": None,
            "Images": None,
        },
        disabled=[
            "Customer ID",
            "Customer Name",
            "Email",
            "Jump Host",
            "Created At",
            "Jump Host IP",
            "Jump Host Username",
            "Jump Host Password",
            "Images"
        ]
    )

    selected_rows = edited_df[edited_df["Select"] == True]

    # -----------------------------
    # Action buttons (ONLY HERE)
    # -----------------------------
    col1, col2, col3 = st.columns(3)

    with col1:
        if st.button("➕ Add Customer"):
            st.session_state.show_add_customer = True

    with col2:
        if selected_rows.empty:
            st.button("✏️ Update Customer", disabled=True)
        else:
            if st.button("✏️ Update Customer"):
                st.session_state.show_update_customer = True

    with col3:
        if selected_rows.empty:
            st.button("🗑 Delete Customer", disabled=True)
        else:
            if st.button("🗑 Delete Customer"):
                st.session_state.show_delete_customer = True

# -----------------------------
# Open dialogs (ONLY HERE)
# -----------------------------
if st.session_state.show_add_customer:
    add_customer_dialog()

if st.session_state.show_delete_customer:
    customer_ids = selected_rows["Customer ID"].tolist()
    delete_customer_dialog(customer_ids)

if st.session_state.show_update_customer:
    # Pass the entire selected rows dataframe instead of just one ID
    update_customer_dialog(selected_rows)


# -----------------------------
# Device Details Page
# -----------------------------

if selected == "Device Details":
    st.subheader("Device Details")

    # Initialize session state
    if "show_add_device" not in st.session_state:
        st.session_state.show_add_device = False

    if "show_delete_device" not in st.session_state:
        st.session_state.show_delete_device = False

    if "show_update_device" not in st.session_state:
        st.session_state.show_update_device = False

    # Load data with JOIN to get customer name
    try:
        with st.spinner("Loading device data..."):
            conn = connect_to_db()
            
            # JOIN query to get customer name
            query = """
                SELECT 
                    d.id,
                    d.customer_id,
                    c.name as customer_name,
                    d.serial_number,
                    d.device_type,
                    d.device_model,
                    d.device_ip,
                    d.username,
                    d.password,
                    d.created_at
                FROM devices d
                LEFT JOIN customers c ON d.customer_id = c.id
                LIMIT 1000
            """
            df_devices = pd.read_sql(query, conn)
            conn.close()
            
    except Exception as e:
        st.error("⚠️ Failed to load device data")
        st.error(f"Error: {str(e)}")
        st.stop()

    df_devices = df_devices.rename(columns={
        "id": "Device ID",
        "customer_id": "Customer ID",
        "customer_name": "Customer Name",
        "serial_number": "Serial Number",
        "device_type": "Device Type",
        "device_model": "Device Model",
        "device_ip": "Device IP",
        "username": "Username",
        "password": "Password",
        "created_at": "Created At"
    })

    df_devices.insert(0, "Select", False)

    edited_df = st.data_editor(
        df_devices,
        hide_index=True,
        use_container_width=True,
        column_config={
            "Select": st.column_config.CheckboxColumn(
                "Select",
                help="Select rows to delete",
                width="small"
            ),
            "Customer ID": None,  # Hide customer ID
            "Username": None,
            "Password": None,
        },
        disabled=[
            "Device ID",
            "Customer Name",
            "Serial Number",
            "Device Type",
            "Device Model",
            "Device IP",
            "Created At"
        ]
    )

    selected_rows = edited_df[edited_df["Select"] == True]

    # -----------------------------
    # Action buttons (ONLY HERE)
    # -----------------------------
    col1, col2, col3 = st.columns(3)

    with col1:
        if st.button("➕ Add Device"):
            st.session_state.show_add_device = True

    with col2:
        if selected_rows.empty:
            st.button("✏️ Update Device", disabled=True)
        else:
            if st.button("✏️ Update Device"):
                st.session_state.show_update_device = True

    with col3:
        if selected_rows.empty:
            st.button("🗑 Delete Device", disabled=True)
        else:
            if st.button("🗑 Delete Device"):
                st.session_state.show_delete_device = True

    # -----------------------------
    # Open dialogs (ONLY HERE)
    # -----------------------------

    if st.session_state.show_add_device:
        add_device_dialog()

    if st.session_state.show_delete_device:
        device_ids = selected_rows["Device ID"].tolist()
        delete_device_dialog(device_ids)

    if st.session_state.show_update_device:
        update_device_dialog(selected_rows)


# -----------------------------
# Template Details Page
# -----------------------------

if selected == "Template Details":
    st.subheader("Template Details")

    # Initialize session state
    if "show_add_template" not in st.session_state:
        st.session_state.show_add_template = False

    if "show_delete_template" not in st.session_state:
        st.session_state.show_delete_template = False

    if "show_update_template" not in st.session_state:
        st.session_state.show_update_template = False

    # Load data with JOIN to get customer name
    try:
        with st.spinner("Loading template data..."):
            conn = connect_to_db()
            
            # JOIN query to get customer name
            query = """
                SELECT 
                    t.id,
                    t.name,
                    t.description,
                    t.command,
                    t.customer_id,
                    c.name as customer_name,
                    t.created_at,
                    t.jump_host
                FROM command_templates t
                LEFT JOIN customers c ON t.customer_id = c.id
                LIMIT 1000
            """
            df_templates = pd.read_sql(query, conn)
            conn.close()
            
    except Exception as e:
        st.error("⚠️ Failed to load template data")
        st.error(f"Error: {str(e)}")
        st.stop()

    df_templates = df_templates.rename(columns={
        "id": "Template ID",
        "name": "Name",
        "description": "Description",
        "command": "Command",
        "customer_id": "Customer ID",
        "customer_name": "Customer Name",
        "created_at": "Created At",
        "jump_host": "Jump Host"
    })
    
    # Convert jump_host boolean to Yes/No
    df_templates["Jump Host"] = df_templates["Jump Host"].apply(lambda x: "Yes" if x else "No")

    df_templates.insert(0, "Select", False)

    edited_df = st.data_editor(
        df_templates,
        hide_index=True,
        use_container_width=True,
        column_config={
            "Select": st.column_config.CheckboxColumn(
                "Select",
                help="Select rows to delete",
                width="small"
            ),
            "Customer ID": None,  # Hide customer ID
            "Command": None,      # Hide command column
        },
        disabled=[
            "Template ID",
            "Name",
            "Description",
            "Customer Name",
            "Created At",
            "Jump Host"
        ]
    )

    selected_rows = edited_df[edited_df["Select"] == True]

    # -----------------------------
    # Action buttons (ONLY HERE)
    # -----------------------------
    col1, col2, col3 = st.columns(3)

    with col1:
        if st.button("➕ Add Template"):
            st.session_state.show_add_template = True

    with col2:
        if selected_rows.empty:
            st.button("✏️ Update Template", disabled=True)
        else:
            if st.button("✏️ Update Template"):
                st.session_state.show_update_template = True

    with col3:
        if selected_rows.empty:
            st.button("🗑 Delete Template", disabled=True)
        else:
            if st.button("🗑 Delete Template"):
                st.session_state.show_delete_template = True

    # -----------------------------
    # Open dialogs (ONLY HERE)
    # -----------------------------

    if st.session_state.show_add_template:
        add_template_dialog()

    if st.session_state.show_delete_template:
        template_ids = selected_rows["Template ID"].tolist()
        delete_template_dialog(template_ids)

    if st.session_state.show_update_template:
        update_template_dialog(selected_rows)


# -----------------------------
# Reporting Page
# -----------------------------

if selected == "Report Details and Generate Report":
    st.subheader("Report Details")

    # Initialize session state
    if "show_add_report" not in st.session_state:
        st.session_state.show_create_report = False

    if "show_delete_report" not in st.session_state:
        st.session_state.show_delete_report = False

    if "show_view_report" not in st.session_state:
        st.session_state.show_view_report = False

    conn = connect_to_db()

    # JOIN query to get customer name, device info, and template name
    query = """
        SELECT
            r.id,
            r.device_id,
            d.serial_number as device_name,
            r.customer_id,
            c.name as customer_name,
            r.template_id,
            t.name as template_name,
            r.result,
            r.created_at

        FROM reports r
        LEFT JOIN devices d ON r.device_id = d.id
        LEFT JOIN customers c ON r.customer_id = c.id
        LEFT JOIN command_templates t ON r.template_id = t.id
        LIMIT 1000
    """
    df_reports = pd.read_sql(query, conn)
    conn.close()

    df_reports = df_reports.rename(columns={
        "id": "Report ID",
        "device_id": "Device ID",
        "device_name": "Device",
        "customer_id": "Customer ID",
        "customer_name": "Customer Name",
        "template_id": "Template ID",
        "template_name": "Template Name",
        "result": "Result",
        "created_at": "Created At"
    })

    df_reports.insert(0, "Select", False)

    edited_df = st.data_editor(
        df_reports,
        hide_index=True,
        use_container_width=True,
        column_config={
            "Select": st.column_config.CheckboxColumn(
                "Select",
                help="Select rows to delete",
                width="small"
            ),
            "Device ID": None,
            "Customer ID": None,
            "Template ID": None,
            "Result": None,
        },
        disabled=[
            "Report ID",
            "Device",
            "Customer Name",
            "Template Name",
            "Created At"
        ]
    )

    selected_rows = edited_df[edited_df["Select"] == True]

    # -----------------------------
    # Action buttons (ONLY HERE)
    # -----------------------------
    col1, col2, col3 = st.columns(3)

    with col1:
        if st.button("➕ Create Report"):
            st.session_state.show_create_report = True

    with col2:
        if selected_rows.empty:
            st.button("📋 Download Report", disabled=True)
        else:
            if st.button("📋 Download Report"):
                st.session_state.show_view_report = True

    with col3:
        if selected_rows.empty:
            st.button("🗑 Delete Report", disabled=True)
        else:
            if st.button("🗑 Delete Report"):
                st.session_state.show_delete_report = True

    # -----------------------------
    # Open dialogs (ONLY HERE)
    # -----------------------------

    if st.session_state.show_create_report:
        create_report_dialog()

    if st.session_state.show_delete_report:
        report_ids = selected_rows["Report ID"].tolist()
        delete_report_dialog(report_ids)

    if st.session_state.show_view_report:
        if not selected_rows.empty:
            report_id = selected_rows["Report ID"].tolist()[0]
            download_report_dialog(report_id)
