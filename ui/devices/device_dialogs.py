"""Device dialog components"""
import streamlit as st
import pandas as pd
from db.customer import get_customers
from db.devices import create_device, update_device, delete_device
from ui.utils import create_dismiss_handler


@st.dialog("Add New Device", on_dismiss=create_dismiss_handler("show_add_device"), width="medium")
def add_device_dialog():
    """Add new device dialog"""
    with st.form("add_device_form", clear_on_submit=True):
        customers_data = get_customers()
        customers_df = pd.DataFrame(
            customers_data,
            columns=["id", "name", "email", "created_at", "jump_host",
                     "jump_host_ip", "jump_host_username", "jump_host_password", "images"],
        )
        customer_options = {row["name"]: row["id"] for _, row in customers_df.iterrows()}

        selected_customer_name = st.selectbox("Customer", list(customer_options.keys()))
        customer_id = customer_options[selected_customer_name]

        serial_number = st.text_input("Serial Number")
        device_type = st.selectbox("Device Type", ["Router", "Switch", "Firewall"])
        device_model = st.text_input("Device Model")
        device_ip = st.text_input("Device IP")
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")

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

    if not all([selected_customer_name, serial_number, device_type, device_model, device_ip, username, password]):
        st.error("Please fill all required fields")
        return

    try:
        create_device(customer_id, serial_number, device_type, device_model, device_ip, username, password)
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
                 "jump_host_ip", "jump_host_username", "jump_host_password", "images"],
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

            serial_number = st.text_input("Serial Number", value=device["Serial Number"], key=f"serial_{device_id}")

            device_types = ["Router", "Switch", "Firewall"]
            type_index = device_types.index(device["Device Type"]) if device["Device Type"] in device_types else 0
            device_type = st.selectbox("Device Type", device_types, index=type_index, key=f"type_{device_id}")

            device_model = st.text_input("Device Model", value=device["Device Model"], key=f"model_{device_id}")
            device_ip = st.text_input("Device IP", value=device["Device IP"], key=f"ip_{device_id}")

            updated_data.append({
                "id": device_id,
                "customer_id": customer_id,
                "serial_number": serial_number,
                "device_type": device_type,
                "device_model": device_model,
                "device_ip": device_ip,
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
                st.session_state.pop("update_forms_data", None)
                st.rerun()

