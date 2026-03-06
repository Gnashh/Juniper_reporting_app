import json
import streamlit as st
import pandas as pd

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

    for _, template in selected_templates.iterrows():

        template_id = template["Template ID"]

        st.markdown(f"### Template {template_id}")

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

        customer_index = 0

        if template.get("Customer Name") in customer_names:
            customer_index = customer_names.index(template["Customer Name"])

        selected_customer = st.selectbox(
            "Customer",
            customer_names,
            index=customer_index,
            key=f"customer_{template_id}",
        )

        col1, col2 = st.columns(2)

        with col1:
            if st.button("Cancel", key=f"cancel_{template_id}"):

                st.session_state.show_update_template = False
                st.rerun()

        with col2:
            if st.button("Update", key=f"update_{template_id}"):

                update_template(
                    template_id,
                    name,
                    template["Description"],
                    template["Command"],
                    customers[selected_customer],
                    desc,
                    None,
                    None,
                    None,
                )

                st.success(f"Template {template_id} updated")

                st.session_state.show_update_template = False
                st.rerun()

        st.divider()
