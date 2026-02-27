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
from auth import require_authentication, logout_user, get_current_user, is_admin
from user_management import show_user_management

# -----------------------------
# Authentication Check
# -----------------------------
# This must be called before any other Streamlit code
require_authentication()

# -----------------------------
# Page config
# -----------------------------
st.set_page_config(
    page_title="Report App",
    page_icon=":bar_chart:",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Get current user info
current_user = get_current_user()

st.title("Reporting App")
if current_user:
    st.caption(f"👤 Logged in as: **{current_user['full_name'] or current_user['username']}**")

# -----------------------------
# Sidebar menu
# -----------------------------
with st.sidebar:
    # Build menu options based on user role
    menu_options = [
        "Customer Details",
        "Device Details",
        "Template Details",
        "Report Details and Generate Report"
    ]

    # Add User Management for admins
    if is_admin():
        menu_options.append("User Management")

    selected = option_menu(
        menu_title="MAIN MENU",
        options=menu_options
    )

    st.markdown("---")

    # User info and logout button
    if current_user:
        st.markdown(f"**👤 User:** {current_user['username']}")
        if current_user.get('is_admin'):
            st.markdown("**🔑 Role:** Administrator")
        else:
            st.markdown("**🔑 Role:** User")

        if st.button("🚪 Logout", use_container_width=True):
            logout_user()
            st.rerun()

# -----------------------------
# Dismiss Handlers
# -----------------------------
def create_dismiss_handler(dialog_key, cleanup_keys=None):
    """
    Universal dismiss handler factory.
    
    Args:
        dialog_key: The session state key for the dialog (e.g., 'show_add_customer')
        cleanup_keys: Optional list of session state keys to delete on dismiss
    """
    def handler():
        st.session_state[dialog_key] = False
        if cleanup_keys:
            for key in cleanup_keys:
                if key in st.session_state:
                    del st.session_state[key]
    return handler

# -----------------------------
# Customer Dialogs
# -----------------------------

@st.dialog("Add New Customer", on_dismiss=create_dismiss_handler("show_add_customer"), width="medium")
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


@st.dialog("Confirm Delete", on_dismiss=create_dismiss_handler("show_delete_customer"), width="small")
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


@st.dialog("Update Customer(s)", on_dismiss=create_dismiss_handler("show_update_customer", ["update_forms_data"]), width="medium")
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
@st.dialog("Add New Device", on_dismiss=create_dismiss_handler("show_add_device"), width="medium")
def add_device_dialog():
    with st.form("add_device_form", clear_on_submit=True):
        # Get customers
        customers_data = get_customers()
        customers_df = pd.DataFrame(customers_data, columns=["id", "name", "email", "created_at", "jump_host", "jump_host_ip", "jump_host_username", "jump_host_password", "images"])
        
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

@st.dialog("Confirm Delete Devices", on_dismiss=create_dismiss_handler("show_delete_device"), width="small")
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


@st.dialog("Update Device(s)", on_dismiss=create_dismiss_handler("show_update_device", ["update_forms_data"]), width="medium")
def update_device_dialog(selected_devices):
    """Update multiple devices at once"""
    st.write(f"Updating {len(selected_devices)} device(s)")
    
    if "update_forms_data" not in st.session_state:
        st.session_state.update_forms_data = {}
    
    with st.form("update_devices_form", clear_on_submit=False):
        updated_data = []
        
        # Get customers for dropdown
        customers_data = get_customers()
        customers_df = pd.DataFrame(customers_data, columns=["id", "name", "email", "created_at", "jump_host", "jump_host_ip", "jump_host_username", "jump_host_password", "images"])
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
@st.dialog("Add New Template", on_dismiss=create_dismiss_handler("show_add_template", ["commands"]), width="large")
def add_template_dialog():
    # Initialize commands in session state
    if "commands" not in st.session_state:
        st.session_state.commands = []
    
    # Get customers
    customers_data = get_customers()
    customers_df = pd.DataFrame(customers_data, columns=["id", "name", "email", "jump_host", "created_at", "jump_host_ip", "jump_host_username", "jump_host_password", "images"])
    
    customers = {row['name']: row['id'] for _, row in customers_df.iterrows()}
    selected_customer_name = st.selectbox("Customer", list(customers.keys()))
    customer_id = customers[selected_customer_name]
    
    name = st.text_input("Template Name")
    general_description = st.text_area("Template Description", placeholder="Describe what this template is for...")

    # Manual Summary Option
    st.markdown("---")
    st.markdown("### 📊 Manual Summary Configuration")
    
    manual_summary = st.radio(
        "Enable Manual Summary",
        ["No", "Yes"],
        horizontal=True,
        help="Add a custom summary table to the report"
    )
    
    manual_summary_desc = ""
    manual_summary_table = []
    
    if manual_summary == "Yes":
        manual_summary_desc = st.text_area(
            "Summary Description",
            placeholder="Enter a description for the manual summary section...",
            height=100
        )
        
        st.markdown("**Summary Table Fields**")
        st.caption("Define the fields that will appear in the summary table")
        
        # Initialize table fields in session state
        if "summary_fields" not in st.session_state:
            st.session_state.summary_fields = [{"field": "", "value": ""}]
        
        # Buttons for managing table fields
        col1, col2 = st.columns(2)
        with col1:
            if st.button("➕ Add Field", use_container_width=True):
                st.session_state.summary_fields.append({"field": "", "value": ""})
                st.rerun()
        with col2:
            if st.button("🗑️ Remove Last Field", use_container_width=True, disabled=len(st.session_state.summary_fields) <= 1):
                if len(st.session_state.summary_fields) > 1:
                    st.session_state.summary_fields.pop()
                    st.rerun()
        
        # Display table fields
        for idx, field_data in enumerate(st.session_state.summary_fields):
            col1, col2 = st.columns(2)
            with col1:
                field_name = st.text_input(
                    f"Field Name {idx + 1}",
                    value=field_data.get("field", ""),
                    key=f"field_name_{idx}",
                    placeholder="e.g., Device Model"
                )
            with col2:
                field_value = st.text_input(
                    f"Default Value {idx + 1}",
                    value=field_data.get("value", ""),
                    key=f"field_value_{idx}",
                    placeholder="e.g., MX480"
                )
            
            st.session_state.summary_fields[idx] = {
                "field": field_name,
                "value": field_value
            }
        
        # Build the table data
        manual_summary_table = [
            {"field": f["field"], "value": f["value"]} 
            for f in st.session_state.summary_fields 
            if f["field"].strip()
        ]

    st.markdown("---")
    st.markdown("### 📝 Commands Configuration")

    # Four buttons for managing items
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        if st.button("➕ Add Header", use_container_width=True):
            st.session_state.commands.append({
                "type": "Header",
                "text": "",
                "description": ""
            })
            st.rerun()
    
    with col2:
        if st.button("➕ Add Predefined Command", use_container_width=True):
            st.session_state.commands.append({
                "type": "Predefined",
                "command": "",
                "description": ""
            })
            st.rerun()
    
    with col3:
        if st.button("➕ Add Custom Command", use_container_width=True):
            st.session_state.commands.append({
                "type": "Custom",
                "command": "",
                "description": ""
            })
            st.rerun()
    
    with col4:
        if st.button("🗑️ Delete Last Item", use_container_width=True, disabled=len(st.session_state.commands) == 0):
            if st.session_state.commands:
                st.session_state.commands.pop()
                st.rerun()

    with st.form("add_template_form", clear_on_submit=True):
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
        
        items_list = []
        for idx, item in enumerate(st.session_state.commands):
            item_type = item.get("type", "Predefined")
            
            st.markdown(f"**Item {idx + 1}** - {item_type}")
            
            if item_type == "Header":
                header_text = st.text_input(
                    "Header Text",
                    value=item.get("text", ""),
                    key=f"header_{idx}",
                    placeholder="e.g., System Information"
                )
                
                st.session_state.commands[idx]["text"] = header_text
                
                if header_text and header_text.strip():
                    items_list.append({
                        "type": "Header",
                        "text": header_text.strip(),
                    })
            
            elif item_type == "Predefined":
                cmd_text = st.selectbox(
                    "Select Command",
                    predefined_commands,
                    key=f"cmd_{idx}",
                    index=predefined_commands.index(item.get("command")) if item.get("command") in predefined_commands else 0
                )
                
                cmd_desc = st.text_area(
                    "Command Description",
                    value=item.get("description", ""),
                    key=f"desc_{idx}",
                    placeholder="Describe what this command does",
                    height=80
                )
                
                st.session_state.commands[idx]["command"] = cmd_text
                st.session_state.commands[idx]["description"] = cmd_desc
                
                if cmd_text and cmd_text.strip():
                    items_list.append({
                        "type": "Predefined",
                        "command": cmd_text.strip(),
                        "description": cmd_desc.strip()
                    })
            
            else:  # Custom
                cmd_text = st.text_input(
                    "Enter Custom Command",
                    value=item.get("command", ""),
                    key=f"cmd_{idx}",
                    placeholder="e.g., show interfaces detail"
                )
                
                cmd_desc = st.text_area(
                    "Command Description",
                    value=item.get("description", ""),
                    key=f"desc_{idx}",
                    placeholder="Describe what this command does",
                    height=80
                )
                
                st.session_state.commands[idx]["command"] = cmd_text
                st.session_state.commands[idx]["description"] = cmd_desc
                
                if cmd_text and cmd_text.strip():
                    items_list.append({
                        "type": "Custom",
                        "command": cmd_text.strip(),
                        "description": cmd_desc.strip()
                    })
            
            st.markdown("---")
        
        col1, col2 = st.columns(2)
        with col1:
            cancel_btn = st.form_submit_button("❌ Cancel", use_container_width=True)
        with col2:
            submit_btn = st.form_submit_button("✅ Submit", use_container_width=True)

    if cancel_btn:
        st.session_state.commands = []
        if "summary_fields" in st.session_state:
            del st.session_state.summary_fields
        st.session_state.show_add_template = False
        st.rerun()
    
    if not submit_btn:
        return

    if not name or not general_description:
        st.error("Please fill in Template Name and Template Description")
        return
    
    if not items_list:
        st.error("Please add at least one item")
        return
    
    if manual_summary == "Yes" and not manual_summary_desc:
        st.error("Please provide a summary description")
        return
    
    if manual_summary == "Yes" and not manual_summary_table:
        st.error("Please add at least one summary field")
        return
    
    try:
        # Store the entire items_list as JSON (includes headers and commands)
        create_template(
            name=name,
            description=[item.get("description", "") for item in items_list],
            command=items_list,  # Store full structure with types
            customer_id=customer_id,
            general_desc=general_description,
            manual_summary_desc=manual_summary_desc if manual_summary == "Yes" else None,
            manual_summary_table=manual_summary_table if manual_summary == "Yes" else None
        )
        
        st.success("Template added successfully")
        st.session_state.commands = []
        if "summary_fields" in st.session_state:
            del st.session_state.summary_fields
        st.session_state.show_add_template = False
        st.rerun()
    except Exception as e:
        st.error(f"Failed to add template: {str(e)}")
        import traceback
        st.error(traceback.format_exc())

@st.dialog("Confirm Delete Template", on_dismiss=create_dismiss_handler("show_delete_template"), width="small")
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


@st.dialog("Update Template(s)", on_dismiss=create_dismiss_handler("show_update_template", ["update_forms_data"]), width="large")
def update_template_dialog(selected_templates):
    """Update multiple templates at once"""
    st.write(f"Updating {len(selected_templates)} template(s)")
    
    if "update_forms_data" not in st.session_state:
        st.session_state.update_forms_data = {}
    
    # Get customers for dropdown
    customers_data = get_customers()
    customers_df = pd.DataFrame(customers_data, columns=["id", "name", "email", "created_at", "jump_host", "jump_host_ip", "jump_host_username", "jump_host_password", "images"])
    customer_options = {row['name']: row['id'] for _, row in customers_df.iterrows()}
    customer_names = list(customer_options.keys())
    
    updated_data = []
    
    for idx, (_, template) in enumerate(selected_templates.iterrows()):
        template_id = template["Template ID"]
        
        st.markdown(f"### Template ID: {template_id}")
        
        # Manual Summary Section - OUTSIDE FORM
        st.markdown("### 📊 Manual Summary Configuration")
        
        has_manual_summary = template.get("Manual Summary Description") not in [None, "", "None"]
        
        manual_summary = st.radio(
            "Enable Manual Summary",
            ["No", "Yes"],
            index=1 if has_manual_summary else 0,
            horizontal=True,
            key=f"manual_summary_{template_id}"
        )
        
        manual_summary_desc = ""
        manual_summary_table = []
        
        if manual_summary == "Yes":
            manual_summary_desc = st.text_area(
                "Summary Description",
                value=template.get("Manual Summary Description", ""),
                placeholder="Enter a description for the manual summary section...",
                height=100,
                key=f"manual_summary_desc_{template_id}"
            )
            
            st.markdown("**Summary Table Fields**")
            st.caption("Define the fields that will appear in the summary table")
            
            # Parse existing manual summary table
            try:
                existing_table = json.loads(template.get("Manual Summary Table", "[]")) if isinstance(template.get("Manual Summary Table"), str) else template.get("Manual Summary Table", [])
                if not existing_table:
                    existing_table = [{"field": "", "value": ""}]
            except:
                existing_table = [{"field": "", "value": ""}]
            
            # Initialize table fields in session state for this template
            session_key = f"summary_fields_{template_id}"
            if session_key not in st.session_state:
                st.session_state[session_key] = existing_table
            
            # Buttons for managing table fields
            col1, col2 = st.columns(2)
            with col1:
                if st.button("➕ Add Field", use_container_width=True, key=f"add_field_{template_id}"):
                    st.session_state[session_key].append({"field": "", "value": ""})
                    st.rerun()
            with col2:
                if st.button("🗑️ Remove Last Field", use_container_width=True, disabled=len(st.session_state[session_key]) <= 1, key=f"remove_field_{template_id}"):
                    if len(st.session_state[session_key]) > 1:
                        st.session_state[session_key].pop()
                        st.rerun()
            
            # Display table fields
            for field_idx, field_data in enumerate(st.session_state[session_key]):
                col1, col2 = st.columns(2)
                with col1:
                    field_name = st.text_input(
                        f"Field Name {field_idx + 1}",
                        value=field_data.get("field", ""),
                        key=f"field_name_{template_id}_{field_idx}",
                        placeholder="e.g., Device Model"
                    )
                with col2:
                    field_value = st.text_input(
                        f"Default Value {field_idx + 1}",
                        value=field_data.get("value", ""),
                        key=f"field_value_{template_id}_{field_idx}",
                        placeholder="e.g., MX480"
                    )
                
                st.session_state[session_key][field_idx] = {
                    "field": field_name,
                    "value": field_value
                }
            
            # Build the table data
            manual_summary_table = [
                {"field": f["field"], "value": f["value"]} 
                for f in st.session_state[session_key] 
                if f["field"].strip()
            ]
        
        st.markdown("---")
        
        # NOW START THE FORM
        with st.form(f"update_template_form_{template_id}", clear_on_submit=False):
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
            
            general_description = st.text_area(
                "General Description",
                value=template["General Description"],
                key=f"general_desc_{template_id}"
            )

            update_time = st.text_input(
                "Update Time (YYYY-MM-DD HH:MM:SS)",
                value=str(template.get("Last Updated", "")),
                key=f"update_time_{template_id}",
                placeholder="2024-01-15 14:30:00"
            )
            
            # Parse existing commands and descriptions
            try:
                existing_commands = json.loads(template.get("Command", "[]")) if isinstance(template.get("Command"), str) else template.get("Command", [])
                existing_descriptions = json.loads(template.get("Description", "[]")) if isinstance(template.get("Description"), str) else template.get("Description", [])
            except:
                existing_commands = []
                existing_descriptions = []
            
            commands = st.text_area(
                "Commands (JSON array)",
                value=json.dumps(existing_commands, indent=2),
                key=f"cmd_{template_id}"
            )
            
            descriptions = st.text_area(
                "Descriptions (JSON array)",
                value=json.dumps(existing_descriptions, indent=2),
                key=f"desc_{template_id}"
            )
            
            col1, col2 = st.columns(2)
            with col1:
                cancel_btn = st.form_submit_button("❌ Cancel", use_container_width=True)
            with col2:
                submit_btn = st.form_submit_button("✅ Update", use_container_width=True)
            
            if cancel_btn:
                st.session_state.show_update_template = False
                if "update_forms_data" in st.session_state:
                    del st.session_state.update_forms_data
                for key in list(st.session_state.keys()):
                    if key.startswith("summary_fields_"):
                        del st.session_state[key]
                st.rerun()
            
            if submit_btn:
                if not name or not general_description:
                    st.error(f"Template ID {template_id}: Please fill all required fields")
                else:
                    try:
                        commands_list = json.loads(commands)
                        descriptions_list = json.loads(descriptions)
                        
                        update_template(
                            template_id, 
                            name, 
                            descriptions_list, 
                            commands_list, 
                            customer_id, 
                            general_description, 
                            update_time,
                            manual_summary_desc if manual_summary == "Yes" else None,
                            manual_summary_table if manual_summary == "Yes" else None
                        )
                        st.success(f"Template ID {template_id} updated successfully")
                        st.session_state.show_update_template = False
                        if "update_forms_data" in st.session_state:
                            del st.session_state.update_forms_data
                        for key in list(st.session_state.keys()):
                            if key.startswith("summary_fields_"):
                                del st.session_state[key]
                        st.rerun()
                    except json.JSONDecodeError:
                        st.error(f"Template ID {template_id}: Invalid JSON format")
                    except Exception as e:
                        st.error(f"Failed to update Template ID {template_id}: {str(e)}")
        
        if idx < len(selected_templates) - 1:
            st.divider()

# -----------------------------
# Report Dialogs
# -----------------------------

@st.dialog("Create New Report", on_dismiss=create_dismiss_handler("show_create_report"), width="large")
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
        
        # Add AI Summary option INSIDE the form
        aisummary = st.radio("AI Summary", ["Yes", "No"], horizontal=True)
        
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
    
    # Convert aisummary to integer AFTER form submission
    ai_summary_value = 1 if aisummary == "Yes" else 0
    
    # Create report
    try:
        # Get template commands and descriptions
        template = get_template_by_id(template_id)

        # Parse the command field (it's a JSON array with type info)
        items_list = json.loads(template['command']) if isinstance(template['command'], str) else template['command']
        
        # Get device details
        device = get_device_by_id(device_id)
        customer = get_customer_by_id(customer_id)
        
        # Connect to device and execute commands
        with st.spinner("Connecting to device..."):
            if customer["jump_host"] == 1:
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
            for item in items_list:
                # Check if it's a header
                if item.get("type") == "Header":
                    all_results.append({
                        "type": "Header",
                        "text": item.get("text", ""),
                        "status": "success"
                    })
                else:
                    # It's a command (Predefined or Custom)
                    cmd = item.get("command")
                    cmd_description = item.get("description", "")
                    
                    try:
                        result = run_command(client, cmd)
                        all_results.append({
                            "type": "Command",
                            "command": cmd,
                            "description": cmd_description,
                            "output": result,
                            "status": "success"
                        })
                    except Exception as e:
                        all_results.append({
                            "type": "Command",
                            "command": cmd,
                            "description": cmd_description,
                            "output": str(e),
                            "status": "error"
                        })
        
        close_connection(client)
        
        # Save report to database
        create_report(device_id, customer_id, template_id, all_results, ai_summary_value)
        
        st.success(f"Report created successfully!")
        st.session_state.show_create_report = False
        st.rerun()
        
    except Exception as e:
        st.error(f"Failed to create report: {str(e)}")
        import traceback
        st.error(traceback.format_exc())  # Add this to see full error details

@st.dialog("Confirm Delete Reports", on_dismiss=create_dismiss_handler("show_delete_report"), width="small")
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

@st.dialog("Download Report", on_dismiss=create_dismiss_handler("show_view_report"), width="small")
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
        },
        disabled=[
            "Device ID",
            "Customer Name",
            "Serial Number",
            "Username",
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
                    t.general_desc,
                    t.update_time,
                    t.manual_summary_desc,
                    t.manual_summary_table
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
        "general_desc": "General Description",
        "update_time": "Last Updated",
        "manual_summary_desc": "Manual Summary Description",
        "manual_summary_table": "Manual Summary Table"
    })
    
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
            "Description": None,
            "Command": None
        },
        disabled=[
            "Template ID",
            "Name",
            "Customer Name",
            "Created At",
            "General Description"
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
            r.created_at,
            r.aisummary

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
        "created_at": "Created At",
        "aisummary": "AI Summary"
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
            "AI Summary": None
        },
        disabled=[
            "Report ID",
            "Device",
            "Customer Name",
            "Template Name",
            "Created At",
            "AI Summary"
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

# -----------------------------
# User Management Page (Admin Only)
# -----------------------------
if selected == "User Management":
    show_user_management()
