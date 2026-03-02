"""Template dialog components"""
import json
import streamlit as st
import pandas as pd
from db.customer import get_customers
from db.templates import create_template, update_template, delete_template
from ui.utils import create_dismiss_handler

# ── Predefined Juniper commands ──────────────────────────────────────────────
PREDEFINED_COMMANDS = [
    "show version",
    "show chassis routing-engine",
    "show chassis hardware",
    "show chassis environment",
    "show system uptime",
    "show interfaces terse",
    "show system alarms",
    "show chassis alarms",
]


# ── Helpers ───────────────────────────────────────────────────────────────────

def _render_summary_fields(session_key: str):
    """Render the add/remove buttons and input rows for a manual-summary table."""
    col1, col2 = st.columns(2)
    with col1:
        if st.button("➕ Add Field", use_container_width=True, key=f"add_field_{session_key}"):
            st.session_state[session_key].append({"field": "", "value": ""})
            st.rerun()
    with col2:
        disabled = len(st.session_state[session_key]) <= 1
        if st.button("🗑️ Remove Last Field", use_container_width=True, disabled=disabled, key=f"rm_field_{session_key}"):
            st.session_state[session_key].pop()
            st.rerun()

    for idx, field_data in enumerate(st.session_state[session_key]):
        c1, c2 = st.columns(2)
        with c1:
            field_name = st.text_input(f"Field Name {idx + 1}", value=field_data.get("field", ""),
                                       key=f"field_name_{session_key}_{idx}", placeholder="e.g., Device Model")
        with c2:
            field_value = st.text_input(f"Default Value {idx + 1}", value=field_data.get("value", ""),
                                        key=f"field_value_{session_key}_{idx}", placeholder="e.g., MX480")
        st.session_state[session_key][idx] = {"field": field_name, "value": field_value}

    return [{"field": f["field"], "value": f["value"]} for f in st.session_state[session_key] if f["field"].strip()]


def _render_command_item(idx: int, item: dict) -> dict | None:
    """Render a single command/header item inside a form. Returns the built item dict or None."""
    item_type = item.get("type", "Predefined")
    st.markdown(f"**Item {idx + 1}** — {item_type}")

    if item_type == "Header":
        header_text = st.text_input("Header Text", value=item.get("text", ""),
                                    key=f"header_{idx}", placeholder="e.g., System Information")
        st.session_state.commands[idx]["text"] = header_text
        if header_text.strip():
            return {"type": "Header", "text": header_text.strip()}

    elif item_type == "Predefined":
        safe_index = PREDEFINED_COMMANDS.index(item["command"]) if item.get("command") in PREDEFINED_COMMANDS else 0
        cmd_text = st.selectbox("Select Command", PREDEFINED_COMMANDS, key=f"cmd_{idx}", index=safe_index)
        cmd_desc = st.text_area("Command Description", value=item.get("description", ""),
                                key=f"desc_{idx}", placeholder="Describe what this command does", height=80)
        st.session_state.commands[idx].update({"command": cmd_text, "description": cmd_desc})
        if cmd_text.strip():
            return {"type": "Predefined", "command": cmd_text.strip(), "description": cmd_desc.strip()}

    else:  # Custom
        cmd_text = st.text_input("Enter Custom Command", value=item.get("command", ""),
                                 key=f"cmd_{idx}", placeholder="e.g., show interfaces detail")
        cmd_desc = st.text_area("Command Description", value=item.get("description", ""),
                                key=f"desc_{idx}", placeholder="Describe what this command does", height=80)
        st.session_state.commands[idx].update({"command": cmd_text, "description": cmd_desc})
        if cmd_text.strip():
            return {"type": "Custom", "command": cmd_text.strip(), "description": cmd_desc.strip()}

    return None


# ── Add Template ──────────────────────────────────────────────────────────────

@st.dialog("Add New Template", on_dismiss=create_dismiss_handler("show_add_template", ["commands"]), width="large")
def add_template_dialog():
    """Add new template dialog"""
    st.session_state.setdefault("commands", [])

    # Customer selector
    customers_data = get_customers()
    customers_df = pd.DataFrame(customers_data,
                                columns=["id", "name", "email", "jump_host", "created_at",
                                         "jump_host_ip", "jump_host_username", "jump_host_password", "images"])
    customers = {row["name"]: row["id"] for _, row in customers_df.iterrows()}
    selected_customer_name = st.selectbox("Customer", list(customers.keys()))
    customer_id = customers[selected_customer_name]

    name = st.text_input("Template Name")
    general_description = st.text_area("Template Description", placeholder="Describe what this template is for...")

    # Manual Summary
    st.markdown("---")
    st.markdown("### 📊 Manual Summary Configuration")
    manual_summary = st.radio("Enable Manual Summary", ["No", "Yes"], horizontal=True,
                              help="Add a custom summary table to the report")

    manual_summary_desc = ""
    manual_summary_table = []

    if manual_summary == "Yes":
        manual_summary_desc = st.text_area("Summary Description",
                                           placeholder="Enter a description for the manual summary section...", height=100)
        st.markdown("**Summary Table Fields**")
        st.caption("Define the fields that will appear in the summary table")
        st.session_state.setdefault("summary_fields", [{"field": "", "value": ""}])
        manual_summary_table = _render_summary_fields("summary_fields")



    # Commands configuration
    st.markdown("---")
    st.markdown("### 📝 Commands Configuration")

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        if st.button("➕ Add Header", use_container_width=True):
            st.session_state.commands.append({"type": "Header", "text": "", "description": ""})
            st.rerun()
    with col2:
        if st.button("➕ Add Predefined Command", use_container_width=True):
            st.session_state.commands.append({"type": "Predefined", "command": "", "description": ""})
            st.rerun()
    with col3:
        if st.button("➕ Add Custom Command", use_container_width=True):
            st.session_state.commands.append({"type": "Custom", "command": "", "description": ""})
            st.rerun()
    with col4:
        if st.button("🗑️ Delete Last Item", use_container_width=True, disabled=len(st.session_state.commands) == 0):
            st.session_state.commands.pop()
            st.rerun()

    with st.form("add_template_form", clear_on_submit=True):
        items_list = []
        for idx, item in enumerate(st.session_state.commands):
            built = _render_command_item(idx, item)
            if built:
                items_list.append(built)
            st.markdown("---")

        col1, col2 = st.columns(2)
        with col1:
            cancel_btn = st.form_submit_button("❌ Cancel", use_container_width=True)
        with col2:
            submit_btn = st.form_submit_button("✅ Submit", use_container_width=True)

    def _cleanup_add():
        st.session_state.commands = []
        st.session_state.pop("summary_fields", None)
        st.session_state.show_add_template = False

    if cancel_btn:
        _cleanup_add()
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
        create_template(
            name=name,
            description=[item.get("description", "") for item in items_list],
            command=items_list,
            customer_id=customer_id,
            general_desc=general_description,
            manual_summary_desc=manual_summary_desc if manual_summary == "Yes" else None,
            manual_summary_table=manual_summary_table if manual_summary == "Yes" else None,
        )
        st.success("Template added successfully")
        _cleanup_add()
        st.rerun()
    except Exception as e:
        import traceback
        st.error(f"Failed to add template: {str(e)}")
        st.error(traceback.format_exc())


# ── Delete Template ───────────────────────────────────────────────────────────

@st.dialog("Confirm Delete Template", on_dismiss=create_dismiss_handler("show_delete_template"), width="small")
def delete_template_dialog(template_ids):
    """Delete template dialog"""
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



# ── Update Template ───────────────────────────────────────────────────────────

@st.dialog("Update Template(s)", on_dismiss=create_dismiss_handler("show_update_template", ["update_forms_data"]), width="large")
def update_template_dialog(selected_templates):
    """Update multiple templates at once"""
    st.write(f"Updating {len(selected_templates)} template(s)")
    st.session_state.setdefault("update_forms_data", {})

    customers_data = get_customers()
    customers_df = pd.DataFrame(customers_data,
                                columns=["id", "name", "email", "created_at", "jump_host",
                                         "jump_host_ip", "jump_host_username", "jump_host_password", "images"])
    customer_options = {row["name"]: row["id"] for _, row in customers_df.iterrows()}
    customer_names = list(customer_options.keys())

    for idx, (_, template) in enumerate(selected_templates.iterrows()):
        template_id = template["Template ID"]
        st.markdown(f"### Template ID: {template_id}")

        # Manual Summary — outside form for dynamic interactivity
        st.markdown("### 📊 Manual Summary Configuration")
        has_manual_summary = template.get("Manual Summary Description") not in [None, "", "None"]
        manual_summary = st.radio("Enable Manual Summary", ["No", "Yes"],
                                  index=1 if has_manual_summary else 0, horizontal=True,
                                  key=f"manual_summary_{template_id}")

        manual_summary_desc = ""
        manual_summary_table = []

        if manual_summary == "Yes":
            manual_summary_desc = st.text_area("Summary Description",
                                               value=template.get("Manual Summary Description", ""),
                                               placeholder="Enter a description for the manual summary section...",
                                               height=100, key=f"manual_summary_desc_{template_id}")
            st.markdown("**Summary Table Fields**")
            st.caption("Define the fields that will appear in the summary table")

            session_key = f"summary_fields_{template_id}"
            if session_key not in st.session_state:
                try:
                    raw = template.get("Manual Summary Table", "[]")
                    existing_table = json.loads(raw) if isinstance(raw, str) else raw
                    if not existing_table:
                        existing_table = [{"field": "", "value": ""}]
                except Exception:
                    existing_table = [{"field": "", "value": ""}]
                st.session_state[session_key] = existing_table

            manual_summary_table = _render_summary_fields(session_key)

        st.markdown("---")

        with st.form(f"update_template_form_{template_id}", clear_on_submit=False):
            customer_index = customer_names.index(template.get("Customer Name", "")) \
                if template.get("Customer Name") in customer_names else 0
            selected_customer = st.selectbox("Customer", customer_names, index=customer_index,
                                             key=f"customer_{template_id}")
            customer_id = customer_options[selected_customer]

            name = st.text_input("Template Name", value=template["Name"], key=f"name_{template_id}")
            general_description = st.text_area("General Description", value=template["General Description"],
                                               key=f"general_desc_{template_id}")
            update_time = st.text_input("Update Time (YYYY-MM-DD HH:MM:SS)",
                                        value=str(template.get("Last Updated", "")),
                                        key=f"update_time_{template_id}", placeholder="2024-01-15 14:30:00")

            try:
                raw_cmd = template.get("Command", "[]")
                existing_commands = json.loads(raw_cmd) if isinstance(raw_cmd, str) else raw_cmd
                raw_desc = template.get("Description", "[]")
                existing_descriptions = json.loads(raw_desc) if isinstance(raw_desc, str) else raw_desc
            except Exception:
                existing_commands, existing_descriptions = [], []

            commands = st.text_area("Commands (JSON array)", value=json.dumps(existing_commands, indent=2),
                                    key=f"cmd_{template_id}")
            descriptions = st.text_area("Descriptions (JSON array)", value=json.dumps(existing_descriptions, indent=2),
                                        key=f"desc_{template_id}")

            col1, col2 = st.columns(2)
            with col1:
                cancel_btn = st.form_submit_button("❌ Cancel", use_container_width=True)
            with col2:
                submit_btn = st.form_submit_button("✅ Update", use_container_width=True)

            def _cleanup_update():
                st.session_state.show_update_template = False
                st.session_state.pop("update_forms_data", None)
                for key in [k for k in st.session_state if k.startswith("summary_fields_")]:
                    del st.session_state[key]

            if cancel_btn:
                _cleanup_update()
                st.rerun()

            if submit_btn:
                if not name or not general_description:
                    st.error(f"Template ID {template_id}: Please fill all required fields")
                else:
                    try:
                        commands_list = json.loads(commands)
                        descriptions_list = json.loads(descriptions)
                        update_template(template_id, name, descriptions_list, commands_list, customer_id,
                                        general_description, update_time,
                                        manual_summary_desc if manual_summary == "Yes" else None,
                                        manual_summary_table if manual_summary == "Yes" else None)
                        st.success(f"Template ID {template_id} updated successfully")
                        _cleanup_update()
                        st.rerun()
                    except json.JSONDecodeError:
                        st.error(f"Template ID {template_id}: Invalid JSON format")
                    except Exception as e:
                        st.error(f"Failed to update Template ID {template_id}: {str(e)}")

        if idx < len(selected_templates) - 1:
            st.divider()
