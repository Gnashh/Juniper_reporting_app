"""Customer dialog components"""
import re
import streamlit as st
from db.customer import create_customer, update_customer, delete_customer, get_customer_by_id
from ui.utils import create_dismiss_handler


@st.dialog("Add New Customer", on_dismiss=create_dismiss_handler("show_add_customer"), width="medium")
def add_customer_dialog():
    """Add new customer dialog"""
    # Jump host selection OUTSIDE form for dynamic updates
    jump_host = st.radio("Jump Host?", ["No", "Yes"], index=0, key="add_customer_jump_host")

    with st.form("add_customer_form", clear_on_submit=True):
        name = st.text_input("Name")
        email = st.text_input("Email")
        image = st.file_uploader("Upload Image, optional, 1x1 recommended", type=["jpg", "jpeg", "png"])

        if jump_host == "Yes":
            jump_host_ip = st.text_input("Jump Host IP")
            jump_host_username = st.text_input("Jump Host Username")
            jump_host_password = st.text_input("Jump Host Password", type="password")
        else:
            jump_host_ip = None
            jump_host_username = None
            jump_host_password = None

        col1, col2 = st.columns(2)
        with col1:
            cancel_btn = st.form_submit_button("❌ Cancel", use_container_width=True)
        with col2:
            submit_btn = st.form_submit_button("✅ Submit", use_container_width=True)

    if cancel_btn:
        st.session_state.show_add_customer = False
        st.rerun()

    if not submit_btn:
        return

    if not name or not email:
        st.error("Please fill all required fields")
        return
    if not re.match(r"[^@]+@[^@]+\.[^@]+", email):
        st.error("Please enter a valid email address")
        return
    if jump_host == "Yes" and not (jump_host_ip and jump_host_username and jump_host_password):
        st.error("Please fill all jump host fields")
        return

    jump_host_value = 1 if jump_host == "Yes" else 0
    try:
        create_customer(name, email, jump_host_value, jump_host_ip, jump_host_username, jump_host_password, image)
        st.success("Customer added successfully")
        st.session_state.show_add_customer = False
        st.rerun()
    except Exception as e:
        st.error(f"Failed to add customer: {str(e)}")


@st.dialog("Confirm Delete", on_dismiss=create_dismiss_handler("show_delete_customer"), width="small")
def delete_customer_dialog(customer_ids):
    """Delete customer dialog"""
    st.warning(f"⚠️ Are you sure you want to delete {len(customer_ids)} customer(s)?")
    st.caption("This action cannot be undone.")

    col1, col2 = st.columns(2)
    with col1:
        if st.button("❌ Cancel", key="cancel_delete"):
            st.session_state.show_delete_customer = False
            st.rerun()
    with col2:
        if st.button("✅ Yes, Delete", key="confirm_delete"):
            try:
                for cust_id in customer_ids:
                    delete_customer(cust_id)
                st.success(f"Deleted {len(customer_ids)} customer(s)")
                st.session_state.show_delete_customer = False
                st.rerun()
            except Exception as e:
                st.error(f"Failed to delete customers: {str(e)}")



@st.dialog("Update Customer(s)", on_dismiss=create_dismiss_handler("show_update_customer", ["update_forms_data"]), width="medium")
def update_customer_dialog(selected_customers):
    """Update multiple customers at once. Each customer gets its own form fields."""
    st.write(f"Updating {len(selected_customers)} customer(s)")

    if "update_forms_data" not in st.session_state:
        st.session_state.update_forms_data = {}

    with st.form("update_customers_form", clear_on_submit=False):
        updated_data = []

        for idx, (_, customer) in enumerate(selected_customers.iterrows()):
            customer_id = customer["Customer ID"]
            full_customer = get_customer_by_id(customer_id)

            st.markdown(f"### Customer ID: {customer_id}")

            name = st.text_input("Name", value=customer["Customer Name"], key=f"name_{customer_id}")
            email = st.text_input("Email", value=customer["Email"], key=f"email_{customer_id}")
            image = st.file_uploader("Upload Image, optional, 1x1 recommended", type=["jpg", "jpeg", "png"], key=f"image_{customer_id}")

            current_jump_host = customer["Jump Host"]
            jump_host_default = "Yes" if isinstance(current_jump_host, str) and current_jump_host.lower() == "yes" else "No"

            jump_host = st.radio("Jump Host?", ["No", "Yes"], index=1 if jump_host_default == "Yes" else 0, key=f"jump_host_{customer_id}")

            if jump_host == "Yes":
                jump_host_ip = st.text_input("Jump Host IP", value=full_customer.get("jump_host_ip") or "", key=f"jump_host_ip_{customer_id}")
                jump_host_username = st.text_input("Jump Host Username", value=full_customer.get("jump_host_username") or "", key=f"jump_host_username_{customer_id}")
                jump_host_password = st.text_input("Jump Host Password", value=full_customer.get("jump_host_password") or "", type="password", key=f"jump_host_password_{customer_id}")
            else:
                jump_host_ip = full_customer.get("jump_host_ip")
                jump_host_username = full_customer.get("jump_host_username")
                jump_host_password = full_customer.get("jump_host_password")

            updated_data.append({
                "id": customer_id,
                "name": name,
                "email": email,
                "image": image,
                "jump_host": jump_host,
                "jump_host_ip": jump_host_ip,
                "jump_host_username": jump_host_username,
                "jump_host_password": jump_host_password,
            })

            if idx < len(selected_customers) - 1:
                st.divider()

        col1, col2 = st.columns(2)
        with col1:
            cancel_btn = st.form_submit_button("❌ Cancel", use_container_width=True)
        with col2:
            submit_btn = st.form_submit_button("✅ Update All", use_container_width=True)

        if cancel_btn:
            st.session_state.show_update_customer = False
            st.session_state.pop("update_forms_data", None)
            st.rerun()

        if submit_btn:
            all_valid = True
            for data in updated_data:
                if not data["name"] or not data["email"]:
                    st.error(f"Customer ID {data['id']}: Please fill all required fields")
                    all_valid = False
                elif not re.match(r"[^@]+@[^@]+\.[^@]+", data["email"]):
                    st.error(f"Customer ID {data['id']}: Please enter a valid email address")
                    all_valid = False

            if all_valid:
                success_count = 0
                for data in updated_data:
                    try:
                        jump_host_value = 1 if data["jump_host"] == "Yes" else 0
                        update_customer(data["id"], data["name"], data["email"], jump_host_value, data["jump_host_ip"], data["jump_host_username"], data["jump_host_password"], data["image"])
                        success_count += 1
                    except Exception as e:
                        st.error(f"Failed to update Customer ID {data['id']}: {str(e)}")

                if success_count > 0:
                    st.success(f"Successfully updated {success_count} customer(s)")

                st.session_state.show_update_customer = False
                st.session_state.pop("update_forms_data", None)
                st.rerun()
