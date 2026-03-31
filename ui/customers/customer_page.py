"""Customer Details page"""
import streamlit as st
import pandas as pd
from db.connect_to_db import connect_to_db
from ui.customers.customer_dialogs import (
    add_customer_dialog,
    delete_customer_dialog,
    update_customer_dialog,
)


def show_customer_page():
    """Render the Customer Details page."""
    st.subheader("Customer Details")

    # Initialise session state flags
    st.session_state.setdefault("show_add_customer", False)
    st.session_state.setdefault("show_delete_customer", False)
    st.session_state.setdefault("show_update_customer", False)

    # Load data
    try:
        with st.spinner("Loading customer data..."):
            conn = connect_to_db()
            df = pd.read_sql("SELECT * FROM customers LIMIT 1000", conn)
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
        "device_type": "Device Type",        
        "created_at": "Created At",
        "jump_host_ip": "Jump Host IP",
        "jump_host_username": "Jump Host Username",
        "jump_host_password": "Jump Host Password",
        "jump_host_hostname": "Jump Host Hostname",        
        "jump_port": "Jump Host Port",        
        "images": "Images",
    })
    df["Jump Host"] = df["Jump Host"].apply(lambda x: "Yes" if x else "No")
    df.insert(0, "Select", False)

    edited_df = st.data_editor(
        df,
        hide_index=True,
        use_container_width=True,
        column_config={
            "Select": st.column_config.CheckboxColumn("Select", help="Select rows to delete", width="small"),
            "Jump Host IP": None,
            "Jump Host Username": None,
            "Jump Host Password": None,
            "Jump Host Hostname": None,   
            "Jump Host Port": None,         
            "Images": None,
            "Device Type": None,
            "target_port": None,
        },
        disabled=["Customer ID", "Customer Name", "Email", "Jump Host", "Created At",
                   "Jump Host IP", "Jump Host Username", "Jump Host Password", "Jump Host Hostname","Jump Host Port", "Images", "Device Type"],
    )

    selected_rows = edited_df[edited_df["Select"] == True]

    # Action buttons
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

    # Open dialogs
    if st.session_state.show_add_customer:
        add_customer_dialog()
    if st.session_state.show_delete_customer:
        delete_customer_dialog(selected_rows["Customer ID"].tolist())
    if st.session_state.show_update_customer:
        update_customer_dialog(selected_rows)

