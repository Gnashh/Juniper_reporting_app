"""Device Details page"""
import streamlit as st
import pandas as pd
from db.connect_to_db import connect_to_db
from ui.devices.device_dialogs import (
    add_device_dialog,
    delete_device_dialog,
    update_device_dialog,
)


def show_device_page():
    """Render the Device Details page."""
    st.subheader("Device Details")

    st.session_state.setdefault("show_add_device", False)
    st.session_state.setdefault("show_delete_device", False)
    st.session_state.setdefault("show_update_device", False)

    # Load data via JOIN
    try:
        with st.spinner("Loading device data..."):
            conn = connect_to_db()
            query = """
                SELECT
                    d.id,
                    d.customer_id,
                    c.name AS customer_name,
                    d.serial_number,
                    d.hostname,
                    d.device_type,
                    d.device_model,
                    d.device_ip,
                    d.device_port,
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
        "hostname": "Hostname",
        "device_type": "Device Type",
        "device_model": "Device Model",
        "device_ip": "Device IP",
        "device_port": "Device Port",
        "username": "Device Username",
        "password": "Device Password",
        "created_at": "Created At",
    })
    df_devices.insert(0, "Select", False)

    edited_df = st.data_editor(
        df_devices,
        hide_index=True,
        use_container_width=True,
        column_config={
            "Select": st.column_config.CheckboxColumn("Select", help="Select rows to delete", width="small"),
            "Customer ID": None,
            "Device Port": None,
            "Device Password": None,
        },
        disabled=["Device ID", "Customer Name", "Serial Number", "Hostname", "Device Username", "Device Password",
                   "Device Type", "Device Model", "Device IP", "Device Port", "Created At"],
    )

    selected_rows = edited_df[edited_df["Select"] == True]

    # Action buttons
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

    # Open dialogs
    if st.session_state.show_add_device:
        add_device_dialog()
    if st.session_state.show_delete_device:
        delete_device_dialog(selected_rows["Device ID"].tolist())
    if st.session_state.show_update_device:
        update_device_dialog(selected_rows)

