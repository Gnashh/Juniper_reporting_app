"""Report dialog components"""
import json
import streamlit as st
import pandas as pd
from db.customer import get_customers, get_customer_by_id
from db.devices import get_devices_by_customer_id, get_device_by_id
from db.templates import get_templates_by_customer_id, get_template_by_id
from db.reports import create_report, delete_report, get_report_by_id
from juniper_service import connect_to_device, close_connection, run_command, connect_via_jump_host
from gen_PDF import generate_pdf
from ui.utils import create_dismiss_handler


@st.dialog("Create New Report", on_dismiss=create_dismiss_handler("show_create_report"), width="large")
def create_report_dialog():
    """Create new report dialog"""
    customers_data = get_customers()
    customers_df = pd.DataFrame(customers_data,
                                columns=["id", "name", "email", "jump_host", "created_at",
                                         "jump_host_ip", "jump_host_username", "jump_host_password", "images"])

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

    with st.form("create_report_form", clear_on_submit=True):
        template_options = {f"{t['name']} (ID: {t['id']})": t["id"] for t in templates_data}
        device_options = {f"{d[2]} - {d[5]} - {d[9]} (ID: {d[0]})": d[0] for d in devices_data}

        selected_template = st.selectbox("Template", list(template_options.keys()))
        template_id = template_options[selected_template]

        selected_device = st.multiselect("Device(s)", list(device_options.keys()))
        device_id = [device_options[d] for d in selected_device] if selected_device else []

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

    ai_summary_value = 1 if aisummary == "Yes" else 0

    try:
        template = get_template_by_id(template_id)
        items_list = json.loads(template["command"]) if isinstance(template["command"], str) else template["command"]
        customer = get_customer_by_id(customer_id)

        # Loop through each selected device
        for dev_id in device_id:
            device = get_device_by_id(dev_id)
            
            with st.spinner(f"Connecting to device {device['hostname']}..."):
                if customer["jump_host"] == 1:
                    jump, client = connect_via_jump_host(
                        customer["jump_host_ip"], customer["jump_host_username"], customer["jump_host_password"],
                        device["device_ip"], device["username"], device["password"],
                    )
                else:
                    client = connect_to_device(device["device_ip"], device["username"], device["password"])

            all_results = []
            with st.spinner(f"Executing commands on {device['hostname']}..."):
                for item in items_list:
                    if item.get("type") == "Header":
                        all_results.append({"type": "Header", "text": item.get("text", ""), "status": "success"})
                    else:
                        cmd = item.get("command")
                        cmd_description = item.get("description", "")
                        try:
                            result = run_command(client, cmd)
                            all_results.append({"type": "Command", "command": cmd, "description": cmd_description,
                                                "output": result, "status": "success"})
                        except Exception as e:
                            all_results.append({"type": "Command", "command": cmd, "description": cmd_description,
                                                "output": str(e), "status": "error"})

            close_connection(client)
            create_report(dev_id, customer_id, template_id, all_results, ai_summary_value)
        
        st.success(f"Created {len(device_id)} report(s) successfully!")
        st.session_state.show_create_report = False
        st.rerun()

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


@st.dialog("Download Report", on_dismiss=create_dismiss_handler("show_view_report"), width="small")
def download_report_dialog(report_ids):
    """Download/view report dialog"""
    
    for report_id in report_ids:
        try:
            with st.spinner(f"Generating report {report_id}..."):
                pdf_buffer, filename = generate_pdf(report_id)                
                st.download_button(
                    f"Download {filename}",
                    data=pdf_buffer,
                    file_name=filename,
                    mime="application/pdf",
                    key=f"download_report_{report_id}"
                )
        except Exception as e:
            st.error(f"Failed to generate report {report_id}: {str(e)}")

    if st.button("Close"):
        st.session_state.show_view_report = False
        st.rerun()
