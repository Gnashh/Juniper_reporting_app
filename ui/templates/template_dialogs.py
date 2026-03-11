import json
import streamlit as st
import pandas as pd
from PIL import Image
import io

from db.customer import get_customers
from db.templates import create_template, update_template, delete_template
from ui.utils import create_dismiss_handler


# -------------------------------
# PREDEFINED COMMANDS
# -------------------------------

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


# -------------------------------
# UTILITY
# -------------------------------

def modal(title):
    """Simple modal container replacement for st.dialog"""
    col1, col2, col3 = st.columns([1, 2, 1])

    with col2:
        with st.container(border=True):
            header_col, close_col = st.columns([9, 1])

            with header_col:
                st.markdown(f"### {title}")

            with close_col:
                if st.button("✖", key=f"close_{title}"):
                    st.session_state.show_add_template = False
                    st.session_state.show_update_template = False
                    st.session_state.show_delete_template = False
                    st.rerun()

            st.divider()
            return st.container()


def get_customer_options():
    data = get_customers()

    df = pd.DataFrame(
        data,
        columns=[
            "id",
            "name",
            "email",
            "jump_host",
            "created_at",
            "jump_host_ip",
            "jump_host_username",
            "jump_host_password",
            "images",
        ],
    )

    return {row["name"]: row["id"] for _, row in df.iterrows()}


# -------------------------------
# SUMMARY TABLE BUILDER
# -------------------------------

def render_summary_fields(session_key):

    st.session_state.setdefault(session_key, [{"field": "", "value": ""}])

    col1, col2 = st.columns(2)

    with col1:
        if st.button("➕ Add Field", key=f"add_{session_key}", use_container_width=True):
            st.session_state[session_key].append({"field": "", "value": ""})
            st.rerun()

    with col2:
        if st.button(
            "🗑 Remove Field",
            key=f"remove_{session_key}",
            use_container_width=True,
            disabled=len(st.session_state[session_key]) <= 1,
        ):
            st.session_state[session_key].pop()
            st.rerun()

    results = []

    for i, item in enumerate(st.session_state[session_key]):

        c1, c2 = st.columns(2)

        with c1:
            field = st.text_input(
                f"Field {i+1}",
                value=item["field"],
                key=f"field_{session_key}_{i}",
            )

        with c2:
            value = st.text_input(
                f"Value {i+1}",
                value=item["value"],
                key=f"value_{session_key}_{i}",
            )

        st.session_state[session_key][i] = {"field": field, "value": value}

        if field.strip():
            results.append({"field": field, "value": value})

    return results


# -------------------------------
# COMMAND BUILDER
# -------------------------------

def render_command_builder():

    st.session_state.setdefault("commands", [])

    c1, c2, c3, c4 = st.columns(4)

    with c1:
        if st.button("Add Header", use_container_width=True):
            st.session_state.commands.append({"type": "Header", "text": ""})
            st.rerun()

    with c2:
        if st.button("Add Predefined", use_container_width=True):
            st.session_state.commands.append({"type": "Predefined", "command": ""})
            st.rerun()

    with c3:
        if st.button("Add Custom", use_container_width=True):
            st.session_state.commands.append({"type": "Custom", "command": ""})
            st.rerun()

    with c4:
        if st.button(
            "Delete Last",
            use_container_width=True,
            disabled=len(st.session_state.commands) == 0,
        ):
            st.session_state.commands.pop()
            st.rerun()

    st.divider()

    items = []

    for i, item in enumerate(st.session_state.commands):

        st.markdown(f"**Item {i+1}**")

        if item["type"] == "Header":

            text = st.text_input(
                "Header Text",
                value=item.get("text", ""),
                key=f"header_{i}",
            )

            st.session_state.commands[i]["text"] = text

            if text.strip():
                items.append({"type": "Header", "text": text})

        elif item["type"] == "Predefined":

            cmd = st.selectbox(
                "Command",
                PREDEFINED_COMMANDS,
                key=f"cmd_{i}",
            )

            desc = st.text_area(
                "Description",
                key=f"desc_{i}",
            )

            items.append(
                {"type": "Predefined", "command": cmd, "description": desc}
            )

        else:

            cmd = st.text_input("Custom Command", key=f"custom_{i}")

            desc = st.text_area("Description", key=f"custom_desc_{i}")

            if cmd.strip():
                items.append(
                    {"type": "Custom", "command": cmd, "description": desc}
                )

        st.divider()

    return items


# -------------------------------
# ADD TEMPLATE
# -------------------------------

@st.dialog("Add Template", on_dismiss=create_dismiss_handler("show_add_template", ["commands", "summary_fields"]), width="large")
def add_template_dialog():

    customers = get_customer_options()

    selected = st.selectbox("Customer", list(customers.keys()))
    customer_id = customers[selected]

    name = st.text_input("Template Name")
    description = st.text_area("Template Description")

    company_logo_file = st.file_uploader("Upload Company Logo", type=["jpg", "jpeg", "png"])
    
    company_logo = None
    if company_logo_file:
        company_logo = company_logo_file.read()
        try:
            st.image(company_logo, width=100, caption="Logo Preview")
        except Exception as e:
            st.error(f"Invalid image file: {str(e)}")
            company_logo = None

    st.markdown("### Manual Summary")

    enable_summary = st.toggle("Enable Summary")

    summary_desc = ""
    summary_table = []

    if enable_summary:

        summary_desc = st.text_area("Summary Description")

        summary_table = render_summary_fields("summary_fields")

    st.markdown("### Commands")

    commands = render_command_builder()

    col1, col2 = st.columns(2)

    with col1:
        if st.button("Cancel", use_container_width=True):

            st.session_state.show_add_template = False
            st.session_state.pop("commands", None)
            st.session_state.pop("summary_fields", None)

            st.rerun()

    with col2:
        if st.button("Submit", use_container_width=True):

            if not name or not description:
                st.error("Name and description required")
                return

            if not commands:
                st.error("Add at least one command")
                return

            create_template(
                name=name,
                description=[x.get("description", "") for x in commands],
                command=commands,
                customer_id=customer_id,
                general_desc=description,
                manual_summary_desc=summary_desc if enable_summary else None,
                manual_summary_table=summary_table if enable_summary else None,
                company_logo=company_logo,
            )

            st.success("Template created")

            st.session_state.show_add_template = False
            st.session_state.pop("commands", None)
            st.session_state.pop("summary_fields", None)

            st.rerun()


# -------------------------------
# DELETE TEMPLATE
# -------------------------------

@st.dialog("Delete Template", on_dismiss=create_dismiss_handler("show_delete_template"), width="small")
def delete_template_dialog(template_ids):

    st.warning(f"Delete {len(template_ids)} template(s)?")

    col1, col2 = st.columns(2)

    with col1:
        if st.button("Cancel", use_container_width=True):
            st.session_state.show_delete_template = False
            st.rerun()

    with col2:
        if st.button("Delete", use_container_width=True):

            for i in template_ids:
                delete_template(i)

            st.success("Templates deleted")

            st.session_state.show_delete_template = False
            st.rerun()


# -------------------------------
# UPDATE TEMPLATE
# -------------------------------

@st.dialog("Update Templates", on_dismiss=create_dismiss_handler("show_update_template"), width="large")
def update_template_dialog(selected_templates):

    customers = get_customer_options()
    customer_names = list(customers.keys())

    all_updates = []

    for idx, (_, template) in enumerate(selected_templates.iterrows()):

        template_id = template["Template ID"]
        st.markdown(f"### Template {template_id}")

        # -------------------------
        # Template fields
        # -------------------------
        name = st.text_input(
            "Template Name",
            value=template["Name"],
            key=f"name_{template_id}",
        )

        desc = st.text_area(
            "Description",
            value=template["General Description"],
            key=f"desc_{template_id}",
        )

        # -------------------------
        # Customer selector
        # -------------------------
        customer_index = 0
        if template.get("Customer Name") in customer_names:
            customer_index = customer_names.index(template["Customer Name"])

        selected_customer = st.selectbox(
            "Customer",
            customer_names,
            index=customer_index,
            key=f"customer_{template_id}",
        )

        # -------------------------
        # Show existing logo safely
        # -------------------------
        existing_logo = template.get("Company Logo")

        if isinstance(existing_logo, (bytes, bytearray)) and len(existing_logo) > 0:
            try:
                image = Image.open(io.BytesIO(existing_logo))
                image.verify()  # validate image
                image = Image.open(io.BytesIO(existing_logo))  # reopen after verify
                st.image(image, width=100, caption="Current Logo")
            except Exception:
                st.warning("Stored logo is corrupted or not a valid image.")

        st.markdown("Upload a new logo to replace the current one.")

        # -------------------------
        # Upload new logo
        # -------------------------
        company_logo_file = st.file_uploader(
            "Upload Company Logo",
            type=["jpg", "jpeg", "png"],
            key=f"logo_{template_id}",
        )

        company_logo = None

        if company_logo_file:
            try:
                company_logo = company_logo_file.read()
                image = Image.open(io.BytesIO(company_logo))
                st.image(image, width=100, caption="New Logo Preview")
            except Exception as e:
                st.error(f"Invalid image file: {str(e)}")
                company_logo = None

        # -------------------------
        # Manual Summary Section
        # -------------------------
        st.markdown("### Manual Summary")
        
        # Check if manual summary exists
        has_manual_summary = template.get("Manual Summary Description") is not None
        
        enable_summary = st.toggle(
            "Enable Summary", 
            value=has_manual_summary,
            key=f"enable_summary_{template_id}"
        )
        
        manual_summary_desc = None
        manual_summary_table = None
        
        if enable_summary:
            # Manual Summary Description
            manual_summary_desc = st.text_area(
                "Summary Description",
                value=template.get("Manual Summary Description", ""),
                key=f"manual_summary_desc_{template_id}",
            )
            
            # Manual Summary Table
            st.markdown("**Summary Table**")
            
            # Parse existing table data
            existing_table = template.get("Manual Summary Table")
            if isinstance(existing_table, str):
                try:
                    existing_table = json.loads(existing_table)
                except:
                    existing_table = []
            elif not isinstance(existing_table, list):
                existing_table = []
            
            # Initialize session state for this template's summary fields
            session_key = f"summary_fields_{template_id}"
            if session_key not in st.session_state:
                if existing_table:
                    st.session_state[session_key] = existing_table
                else:
                    st.session_state[session_key] = [{"field": "", "value": ""}]
            
            # Render the summary table editor
            manual_summary_table = render_summary_fields(session_key)



        # -------------------------
        # Commands Section
        # -------------------------
        st.markdown("### Commands")
        
        # Parse existing commands
        existing_commands = template.get("Command")
        if isinstance(existing_commands, str):
            try:
                existing_commands = json.loads(existing_commands)
            except:
                existing_commands = []
        elif not isinstance(existing_commands, list):
            existing_commands = []
        
        # Initialize session state for this template's commands
        commands_key = f"commands_{template_id}"
        if commands_key not in st.session_state:
            st.session_state[commands_key] = existing_commands if existing_commands else []
        
        # Command builder buttons
        c1, c2, c3, c4 = st.columns(4)
        
        with c1:
            if st.button("Add Header", key=f"add_header_{template_id}", use_container_width=True):
                st.session_state[commands_key].append({"type": "Header", "text": ""})
                st.rerun()
        
        with c2:
            if st.button("Add Predefined", key=f"add_predefined_{template_id}", use_container_width=True):
                st.session_state[commands_key].append({"type": "Predefined", "command": ""})
                st.rerun()
        
        with c3:
            if st.button("Add Custom", key=f"add_custom_{template_id}", use_container_width=True):
                st.session_state[commands_key].append({"type": "Custom", "command": ""})
                st.rerun()
        
        with c4:
            if st.button(
                "Delete Last",
                key=f"delete_last_{template_id}",
                use_container_width=True,
                disabled=len(st.session_state[commands_key]) == 0,
            ):
                st.session_state[commands_key].pop()
                st.rerun()
        
        st.divider()
        
        # Render command items
        updated_commands = []
        
        for i, item in enumerate(st.session_state[commands_key]):
            
            st.markdown(f"**Item {i+1}**")
            
            if item.get("type") == "Header":
                
                text = st.text_input(
                    "Header Text",
                    value=item.get("text", ""),
                    key=f"header_{template_id}_{i}",
                )
                
                st.session_state[commands_key][i]["text"] = text
                
                if text.strip():
                    updated_commands.append({"type": "Header", "text": text})
            
            elif item.get("type") == "Predefined":
                
                # Find index of current command in predefined list
                current_cmd = item.get("command", "")
                cmd_index = 0
                if current_cmd in PREDEFINED_COMMANDS:
                    cmd_index = PREDEFINED_COMMANDS.index(current_cmd)
                
                cmd = st.selectbox(
                    "Command",
                    PREDEFINED_COMMANDS,
                    index=cmd_index,
                    key=f"cmd_{template_id}_{i}",
                )
                
                desc = st.text_area(
                    "Description",
                    value=item.get("description", ""),
                    key=f"desc_{template_id}_{i}",
                )
                
                updated_commands.append(
                    {"type": "Predefined", "command": cmd, "description": desc}
                )
            
            else:  # Custom
                
                cmd = st.text_input(
                    "Custom Command",
                    value=item.get("command", ""),
                    key=f"custom_{template_id}_{i}"
                )
                
                desc = st.text_area(
                    "Description",
                    value=item.get("description", ""),
                    key=f"custom_desc_{template_id}_{i}"
                )
                
                if cmd.strip():
                    updated_commands.append(
                        {"type": "Custom", "command": cmd, "description": desc}
                    )
            
            st.divider()

        # Store the update data
        all_updates.append({
            "template_id": template_id,
            "name": name,
            "desc": desc,
            "selected_customer": selected_customer,
            "company_logo": company_logo,
            "existing_logo": existing_logo,
            "enable_summary": enable_summary,
            "manual_summary_desc": manual_summary_desc,
            "manual_summary_table": manual_summary_table,
            "updated_commands": updated_commands,
        })

        if idx < len(selected_templates) - 1:
            st.divider()

    # -------------------------
    # Buttons (outside loop)
    # -------------------------
    col1, col2 = st.columns(2)

    with col1:
        if st.button("Cancel", use_container_width=True):
            st.session_state.show_update_template = False
            st.rerun()

    with col2:
        if st.button("Update All", use_container_width=True):
            
            for update_data in all_updates:
                
                if not update_data["updated_commands"]:
                    st.error(f"Template {update_data['template_id']}: Add at least one command")
                    return

                final_logo = update_data["company_logo"] if update_data["company_logo"] else update_data["existing_logo"]
                description_array = [x.get("description", "") for x in update_data["updated_commands"]]

                update_template(
                    update_data["template_id"],
                    update_data["name"],
                    description_array,
                    update_data["updated_commands"],
                    customers[update_data["selected_customer"]],
                    update_data["desc"],
                    None,
                    update_data["manual_summary_desc"] if update_data["enable_summary"] else None,
                    update_data["manual_summary_table"] if update_data["enable_summary"] else None,
                    final_logo,
                )

            st.success(f"Updated {len(all_updates)} template(s)")
            st.session_state.show_update_template = False
            st.rerun()
