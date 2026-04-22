"""Report dialog components"""
import json
import streamlit as st
import pandas as pd
from db.customer import get_customers, get_customer_by_id
from db.devices import get_devices_by_customer_id, get_device_by_id
from db.templates import get_templates_by_customer_id, get_template_by_id
from db.reports import create_report, delete_report, get_report_by_id
from juniper_service import (
    connect_to_device,
    connect_via_jump_host,
    run_command,
    close,
)
from gen_PDF import generate_pdf
from ui.utils import create_dismiss_handler
from premade_report import create_premade_report


@st.dialog("Create New Report", on_dismiss=create_dismiss_handler("show_create_report"), width="large")
def create_report_dialog():
    """Create new report dialog"""
    customers_data = get_customers()
    customers_df = pd.DataFrame(
        customers_data,
        columns=[
            "id", "name", "email", "jump_host", "jump_host_ip", "jump_host_username", "jump_host_password", "jump_host_hostname", "jump_port", "device_type", "images", "created_at",
        ],
    )

    if customers_df.empty:
        st.error("No customers found. Please create a customer first.")
        if st.button("Close"):
            st.session_state.show_create_report = False
            st.rerun()
        return

    customer_options = {row["name"]: row["id"] for _, row in customers_df.iterrows()}
    selected_customer_name = st.selectbox("Customer", list(customer_options.keys()), key="report_customer_select")
    customer_id = customer_options[selected_customer_name]

    templates_data = get_templates_by_customer_id(customer_id)
    devices_data = get_devices_by_customer_id(customer_id)

    if not templates_data:
        st.warning(f"⚠️ Customer '{selected_customer_name}' has no templates.")
        st.info("Please create a template for this customer first.")
        if st.button("Close"):
            st.session_state.show_create_report = False
            st.rerun()
        return

    if not devices_data:
        st.warning(f"⚠️ Customer '{selected_customer_name}' has no devices.")
        st.info("Please add a device for this customer first.")
        if st.button("Close"):
            st.session_state.show_create_report = False
            st.rerun()
        return

    # Template selection - OUTSIDE form
    template_options = {f"{t['name']} (ID: {t['id']})": t["id"] for t in templates_data}
    selected_template = st.selectbox("Template", list(template_options.keys()))
    template_id = template_options[selected_template]
    
    # Get template to check premade_report flag
    template = get_template_by_id(template_id)
    
    # Device selection - OUTSIDE form
    device_options = {f"{d[2]} - {d[5]} - {d[9]} (ID: {d[0]})": d[0] for d in devices_data}
    selected_device = st.multiselect("Device(s)", list(device_options.keys()))
    device_id = [device_options[d] for d in selected_device] if selected_device else []
    
    # File uploaders - only if premade_report
    uploaded_files = {}
    if template.get("premade_report") == 1 and device_id:
        st.markdown("### Upload Log Files")
        for dev_id in device_id:
            device = get_device_by_id(dev_id)
            uploaded_file = st.file_uploader(
                f"Upload .log file for {device['hostname']}", 
                type=["log", "txt"],
                key=f"upload_{dev_id}"
            )
            if uploaded_file:
                uploaded_files[dev_id] = uploaded_file

    # AI Summary - no form needed
    aisummary = st.radio("AI Summary", ["Yes", "No"], horizontal=True)

    # Buttons - no form needed
    col1, col2 = st.columns(2)
    with col1:
        if st.button("❌ Cancel", use_container_width=True):
            st.session_state.show_create_report = False
            st.rerun()
    with col2:
        if st.button("✅ Submit", use_container_width=True):
            ai_summary_value = 1 if aisummary == "Yes" else 0
            
            try:
                items_list = (
                    json.loads(template["command"])
                    if isinstance(template["command"], str)
                    else template["command"]
                )
                customer = get_customer_by_id(customer_id)
                jump_port = int(customer.get("jump_port") or 22)
                successful_reports = 0

                if template.get("premade_report") == 1:
                    # Premade report flow - process uploaded files
                    if not uploaded_files:
                        st.error("❌ Please upload log files for all selected devices")
                        return
                    
                    for dev_id, uploaded_file in uploaded_files.items():
                        all_results = create_premade_report(dev_id, customer_id, template_id, uploaded_file)
                        create_report(dev_id, customer_id, template_id, all_results, ai_summary_value)
                        successful_reports += 1
                else:
                    # Live report flow - connect to devices
                    for dev_id in device_id:
                        device = get_device_by_id(dev_id)
                        target_port = int(device.get("device_port") or 22)

                        with st.spinner(f"Connecting to device {device['hostname']}..."):
                            try:
                                if customer["jump_host"] != 0:
                                    connection = connect_via_jump_host(
                                        customer["device_type"],
                                        customer["jump_host_ip"],
                                        customer["jump_host_username"],
                                        customer["jump_host_password"],
                                        customer["jump_host_hostname"],
                                        device["device_ip"],
                                        device["username"],
                                        device["password"],
                                        jump_port=jump_port,
                                        target_port=target_port,
                                    )
                                else:
                                    connection = connect_to_device(
                                        device["device_ip"],
                                        device["username"],
                                        device["password"],
                                        target_port=target_port,
                                    )
                            except ConnectionError as e:
                                st.error(f"❌ {str(e)}")
                                continue
                            except Exception as e:
                                st.error(f"❌ Unexpected connection error: {str(e)}")
                                continue

                        all_results = []
                        with st.spinner(f"Executing commands on {device['hostname']}..."):
                            for item in items_list:
                                if item.get("type") == "Header":
                                    all_results.append({
                                        "type": "Header",
                                        "text": item.get("text", ""),
                                        "status": "success",
                                    })
                                else:
                                    cmd = item.get("command")
                                    cmd_description = item.get("description", "")
                                    try:
                                        result = run_command(connection, cmd)
                                        all_results.append({
                                            "type": "Command",
                                            "command": cmd,
                                            "description": cmd_description,
                                            "output": result,
                                            "status": "success",
                                        })
                                    except Exception as e:
                                        all_results.append({
                                            "type": "Command",
                                            "command": cmd,
                                            "description": cmd_description,
                                            "output": str(e),
                                            "status": "error",
                                        })

                        close(connection)
                        create_report(dev_id, customer_id, template_id, all_results, ai_summary_value)
                        successful_reports += 1

                if successful_reports > 0:
                    st.success(f"✅ Created {successful_reports} report(s) successfully!")
                    st.session_state.show_create_report = False
                    st.rerun()
                else:
                    st.error("❌ No reports were created.")

            except Exception as e:
                import traceback
                st.error(f"Failed to create report: {str(e)}")
                st.error(traceback.format_exc())


@st.dialog("Confirm Delete Reports", on_dismiss=create_dismiss_handler("show_delete_report"), width="small")
def delete_report_dialog(report_ids):
    """Delete report dialog"""
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
