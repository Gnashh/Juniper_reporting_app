"""Report Details page"""
import streamlit as st
import pandas as pd
from db.connect_to_db import connect_to_db
from ui.reports.report_dialogs import (
    create_report_dialog,
    delete_report_dialog,
    download_report_dialog,
)


def show_report_page():
    """Render the Report Details and Generate Report page."""
    st.subheader("Report Details")

    st.session_state.setdefault("show_create_report", False)
    st.session_state.setdefault("show_delete_report", False)
    st.session_state.setdefault("show_view_report", False)

    try:
        with st.spinner("Loading report data..."):
            conn = connect_to_db()
            query = """
                SELECT
                    r.id,
                    r.device_id,
                    d.serial_number AS device_name,
                    r.customer_id,
                    c.name AS customer_name,
                    r.template_id,
                    t.name AS template_name,
                    r.result,
                    r.created_at,
                    r.ai_summary
                FROM reports r
                LEFT JOIN devices d ON r.device_id = d.id
                LEFT JOIN customers c ON r.customer_id = c.id
                LEFT JOIN command_templates t ON r.template_id = t.id
                LIMIT 1000
            """
            df_reports = pd.read_sql(query, conn)
            conn.close()
    except Exception as e:
        st.error("⚠️ Failed to load report data")
        st.error(f"Error: {str(e)}")
        st.stop()

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
        "ai_summary": "AI Summary",
    })
    df_reports.insert(0, "Select", False)

    edited_df = st.data_editor(
        df_reports,
        hide_index=True,
        use_container_width=True,
        column_config={
            "Select": st.column_config.CheckboxColumn("Select", help="Select rows to delete", width="small"),
            "Device ID": None,
            "Customer ID": None,
            "Template ID": None,
            "Result": None,
            "AI Summary": None,
        },
        disabled=["Report ID", "Device", "Customer Name", "Template Name", "Created At", "AI Summary"],
    )

    selected_rows = edited_df[edited_df["Select"] == True]

    # Action buttons
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

    # Open dialogs
    if st.session_state.show_create_report:
        create_report_dialog()
    if st.session_state.show_delete_report:
        delete_report_dialog(selected_rows["Report ID"].tolist())
    if st.session_state.show_view_report and not selected_rows.empty:
        download_report_dialog(selected_rows["Report ID"].tolist()[0])

