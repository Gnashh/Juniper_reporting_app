"""Template Details page"""
import streamlit as st
import pandas as pd
from db.connect_to_db import connect_to_db
from ui.templates.template_dialogs import (
    add_template_dialog,
    delete_template_dialog,
    update_template_dialog,
)


def show_template_page():
    """Render the Template Details page."""
    st.subheader("Template Details")

    st.session_state.setdefault("show_add_template", False)
    st.session_state.setdefault("show_delete_template", False)
    st.session_state.setdefault("show_update_template", False)

    try:
        with st.spinner("Loading template data..."):
            conn = connect_to_db()
            query = """
                SELECT
                    t.id,
                    t.name,
                    t.description,
                    t.command,
                    t.customer_id,
                    c.name AS customer_name,
                    t.created_at,
                    t.general_desc,
                    t.update_time,
                    t.manual_summary_desc,
                    t.manual_summary_table,
                    t.company_logo
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
        "manual_summary_table": "Manual Summary Table",
        "company_logo": "Company Logo",
    })
    df_templates.insert(0, "Select", False)

    edited_df = st.data_editor(
        df_templates,
        hide_index=True,
        use_container_width=True,
        column_config={
            "Select": st.column_config.CheckboxColumn("Select", help="Select rows to delete", width="small"),
            "Customer ID": None,
            "Description": None,
            "Command": None,
            "Company Logo": None,
        },
        disabled=["Template ID", "Name", "Customer Name", "Created At", "General Description", "Last Updated", "Manual Summary Description", "Manual Summary Table"],
    )

    selected_rows = edited_df[edited_df["Select"] == True]

    # Action buttons
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

    # Open dialogs
    if st.session_state.show_add_template:
        add_template_dialog()
    if st.session_state.show_delete_template:
        delete_template_dialog(selected_rows["Template ID"].tolist())
    if st.session_state.show_update_template:
        update_template_dialog(selected_rows)

