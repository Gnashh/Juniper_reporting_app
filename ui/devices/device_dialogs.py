"""Device dialog components"""
import streamlit as st
import pandas as pd
from db.customer import get_customers
from db.devices import create_device, update_device, delete_device
from ui.utils import create_dismiss_handler


@st.dialog("Add New Device", on_dismiss=create_dismiss_handler("show_add_device"), width="medium")
def add_device_dialog():
    """Add new device dialog"""
    customers_data = get_customers()
    customers_df = pd.DataFrame(
        customers_data,
        columns=["id", "name", "email", "created_at", "jump_host",
                 "jump_host_ip", "jump_host_username", "jump_host_password", "images", "device_type", "jump_host_hostname", "jump_port"],
    )
    customer_options = {row["name"]: row["id"] for _, row in customers_df.iterrows()}

    # Customer selection OUTSIDE form so we can react to changes
    selected_customer_name = st.selectbox("Customer", list(customer_options.keys()), key="add_device_customer")
    customer_id = customer_options[selected_customer_name]
    
    # Get customer details to check jump host configuration
    selected_customer = customers_df[customers_df["id"] == customer_id].iloc[0]
    
    # Convert jump_host to boolean - handle both int and timestamp
    jump_host_value = selected_customer['jump_host']
    has_jump_host = bool(jump_host_value) and jump_host_value != 0
    
    is_juniper_jump = (has_jump_host and selected_customer["device_type"] == "Juniper")
    
    # Show warning if Juniper jump host
    if is_juniper_jump:
        st.warning("⚠️ This customer uses a Juniper jump host. Device port is restricted to **22** only (Juniper SSH client limitation).")

    with st.form("add_device_form", clear_on_submit=True):
        hostname = st.text_input("Hostname", key="hostname")
        serial_number = st.text_input("Serial Number", key="serial_number")
        device_type = st.selectbox("Device Type", ["Router", "Switch", "Firewall"])
        device_model = st.text_input("Device Model")
        device_ip = st.text_input("Device IP")
        
        # Port field - disabled if Juniper jump host
        if is_juniper_jump:
            device_port = st.number_input(
                "Device Port", 
                value=22, 
                disabled=True,
                help="Port is locked to 22 because this customer uses a Juniper jump host, which only supports standard SSH port."
            )
        else:
            device_port = st.number_input(
                "Device Port", 
                min_value=1, 
                max_value=65535, 
                value=22,
                help="SSH port for connecting to this device."
            )
        
        username = st.text_input("Device Username")
        password = st.text_input("Device Password", type="password")

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

    if not all([selected_customer_name, hostname, serial_number, device_type, device_model, device_ip, device_port, username, password]):
        st.error("Please fill all required fields")
        return

    try:
        create_device(customer_id, serial_number, hostname, device_type, device_model, device_ip, device_port, username, password)
        st.success("Device added successfully")
        st.session_state.show_add_device = False
        st.rerun()
    except Exception as e:
        st.error(f"Failed to add device: {str(e)}")


@st.dialog("Confirm Delete Devices", on_dismiss=create_dismiss_handler("show_delete_device"), width="small")
def delete_device_dialog(device_ids):
    """Delete device dialog"""
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

    st.session_state.setdefault("update_forms_data", {})

    customers_data = get_customers()
    customers_df = pd.DataFrame(
        customers_data,
        columns=["id", "name", "email", "created_at", "jump_host",
                 "jump_host_ip", "jump_host_username", "jump_host_password", "images", "device_type", "jump_host_hostname", "jump_port"],
    )
    customer_options = {row["name"]: row["id"] for _, row in customers_df.iterrows()}
    customer_names = list(customer_options.keys())

    with st.form("update_devices_form", clear_on_submit=False):
        updated_data = []

        for idx, (_, device) in enumerate(selected_devices.iterrows()):
            device_id = device["Device ID"]
            st.markdown(f"### Device ID: {device_id}")

            current_customer = device.get("Customer Name", "")
            customer_index = customer_names.index(current_customer) if current_customer in customer_names else 0
            selected_customer = st.selectbox("Customer", customer_names, index=customer_index, key=f"customer_{device_id}")
            customer_id = customer_options[selected_customer]
            
            # Check if selected customer uses Juniper jump host
            selected_customer_row = customers_df[customers_df["id"] == customer_id].iloc[0]
            
            # Convert jump_host to boolean - handle both int and timestamp
            jump_host_value = selected_customer_row['jump_host']
            has_jump_host = bool(jump_host_value) and jump_host_value != 0
            
            is_juniper_jump = (has_jump_host and selected_customer_row["device_type"] == "Juniper")
            
            if is_juniper_jump:
                st.info(f"ℹ️ Customer '{selected_customer}' uses a Juniper jump host — device port locked to 22")

            serial_number = st.text_input("Serial Number", value=device["Serial Number"], key=f"serial_{device_id}")
            hostname = st.text_input("Hostname", value=device["Hostname"], key=f"hostname_{device_id}")

            device_types = ["Router", "Switch", "Firewall"]
            type_index = device_types.index(device["Device Type"]) if device["Device Type"] in device_types else 0
            
            device_type = st.selectbox("Device Type", device_types, index=type_index, key=f"type_{device_id}")
            device_model = st.text_input("Device Model", value=device["Device Model"], key=f"model_{device_id}")
            device_ip = st.text_input("Device IP", value=device["Device IP"], key=f"ip_{device_id}")
            
            # Port field - disabled if Juniper jump host
            current_port = int(device.get("Device Port", 22))
            if is_juniper_jump:
                device_port = st.number_input(
                    "Device Port", 
                    value=22, 
                    disabled=True,
                    help="Port is locked to 22 because this customer uses a Juniper jump host.",
                    key=f"port_{device_id}"
                )
            else:
                device_port = st.number_input(
                    "Device Port", 
                    min_value=1, 
                    max_value=65535, 
                    value=current_port, 
                    key=f"port_{device_id}"
                )

            device_username = st.text_input("Device Username", value=device.get("username", ""), key=f"username_{device_id}")
            device_password = st.text_input("Device Password", value=device.get("password", ""), type="password", key=f"password_{device_id}")

            updated_data.append({
                "id": device_id,
                "customer_id": customer_id,
                "serial_number": serial_number,
                "hostname": hostname,
                "device_type": device_type,
                "device_model": device_model,
                "device_ip": device_ip,
                "device_port": device_port,
                "username": device_username,                
                "password": device_password,                 
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
            st.session_state.pop("update_forms_data", None)
            st.rerun()

        if submit_btn:
            all_valid = True
            for data in updated_data:
                if not data["hostname"] or not data["serial_number"] or not data["device_type"] or not data["device_model"] or not data["device_ip"] or not data["device_port"] or not data["username"] or not data["password"]:
                    st.error(f"Device ID {data['id']}: Please fill all required fields")
                    all_valid = False

            if all_valid:
                success_count = 0
                for data in updated_data:
                    try:
                        update_device(data["id"], data["customer_id"], data["serial_number"], data["hostname"], data["device_type"], data["device_model"], data["device_ip"], data["device_port"], data["username"], data["password"])
                        success_count += 1
                    except Exception as e:
                        st.error(f"Failed to update Device ID {data['id']}: {str(e)}")

                if success_count > 0:
                    st.success(f"Successfully updated {success_count} device(s)")

                st.session_state.show_update_device = False
                st.session_state.pop("update_forms_data", None)
                st.rerun()

