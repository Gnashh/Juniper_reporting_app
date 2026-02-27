import streamlit as st
import pandas as pd
from db.users import create_user, get_all_users, update_user, delete_user, change_password
from auth import get_current_user, is_admin
import re

def show_user_management():
    """Display user management interface (admin only)"""
    
    if not is_admin():
        st.error("⛔ Access Denied: Admin privileges required")
        return
    
    st.subheader("👥 User Management")
    
    # Initialize session state
    if "show_add_user" not in st.session_state:
        st.session_state.show_add_user = False
    if "show_delete_user" not in st.session_state:
        st.session_state.show_delete_user = False
    if "show_change_password" not in st.session_state:
        st.session_state.show_change_password = False
    
    # Load users
    try:
        users = get_all_users()
        df = pd.DataFrame(users)
        
        if not df.empty:
            df = df.rename(columns={
                "id": "User ID",
                "username": "Username",
                "full_name": "Full Name",
                "email": "Email",
                "is_active": "Active",
                "is_admin": "Admin",
                "created_at": "Created At",
                "last_login": "Last Login"
            })
            
            df["Active"] = df["Active"].apply(lambda x: "✅" if x else "❌")
            df["Admin"] = df["Admin"].apply(lambda x: "✅" if x else "❌")
            
            df.insert(0, "Select", False)
            
            edited_df = st.data_editor(
                df,
                hide_index=True,
                use_container_width=True,
                column_config={
                    "Select": st.column_config.CheckboxColumn(
                        "Select",
                        help="Select users",
                        width="small"
                    )
                },
                disabled=[
                    "User ID", "Username", "Full Name", "Email", 
                    "Active", "Admin", "Created At", "Last Login"
                ]
            )
            
            selected_rows = edited_df[edited_df["Select"] == True]
            
            # Action buttons
            col1, col2, col3 = st.columns(3)
            
            with col1:
                if st.button("➕ Add User"):
                    st.session_state.show_add_user = True
            
            with col2:
                if selected_rows.empty or len(selected_rows) != 1:
                    st.button("🔑 Change Password", disabled=True)
                else:
                    if st.button("🔑 Change Password"):
                        st.session_state.show_change_password = True
                        st.session_state.selected_user_id = selected_rows.iloc[0]["User ID"]
            
            with col3:
                if selected_rows.empty:
                    st.button("🗑 Delete User", disabled=True)
                else:
                    if st.button("🗑 Delete User"):
                        st.session_state.show_delete_user = True
            
            # Show dialogs
            if st.session_state.show_add_user:
                add_user_dialog()
            
            if st.session_state.show_delete_user:
                user_ids = selected_rows["User ID"].tolist()
                delete_user_dialog(user_ids)
            
            if st.session_state.show_change_password:
                change_password_dialog(st.session_state.selected_user_id)
        
        else:
            st.info("No users found")
            if st.button("➕ Add User"):
                st.session_state.show_add_user = True
            
            if st.session_state.show_add_user:
                add_user_dialog()
    
    except Exception as e:
        st.error(f"Failed to load users: {str(e)}")

@st.dialog("Add New User")
def add_user_dialog():
    with st.form("add_user_form", clear_on_submit=True):
        username = st.text_input("Username*", placeholder="Enter username")
        password = st.text_input("Password*", type="password", placeholder="Enter password")
        confirm_password = st.text_input("Confirm Password*", type="password", placeholder="Confirm password")
        full_name = st.text_input("Full Name", placeholder="Enter full name")
        email = st.text_input("Email", placeholder="Enter email")
        is_admin = st.checkbox("Administrator")
        
        col1, col2 = st.columns(2)
        with col1:
            cancel_btn = st.form_submit_button("❌ Cancel", use_container_width=True)
        with col2:
            submit_btn = st.form_submit_button("✅ Submit", use_container_width=True)
    
    if cancel_btn:
        st.session_state.show_add_user = False
        st.rerun()
    
    if submit_btn:
        if not username or not password:
            st.error("Username and password are required")
            return
        
        if password != confirm_password:
            st.error("Passwords do not match")
            return
        
        if len(password) < 6:
            st.error("Password must be at least 6 characters")
            return
        
        if email and not re.match(r"[^@]+@[^@]+\.[^@]+", email):
            st.error("Invalid email address")
            return
        
        try:
            create_user(username, password, full_name, email, is_admin)
            st.success(f"User '{username}' created successfully")
            st.session_state.show_add_user = False
            st.rerun()
        except Exception as e:
            st.error(f"Failed to create user: {str(e)}")

@st.dialog("Delete User(s)")
def delete_user_dialog(user_ids):
    current_user = get_current_user()

    # Check if trying to delete self
    if current_user['id'] in user_ids:
        st.error("⚠️ You cannot delete your own account!")
        if st.button("Close"):
            st.session_state.show_delete_user = False
            st.rerun()
        return

    st.warning(f"⚠️ Are you sure you want to delete {len(user_ids)} user(s)?")
    st.caption("This action cannot be undone.")

    col1, col2 = st.columns(2)
    with col1:
        if st.button("❌ Cancel", key="cancel_delete_user"):
            st.session_state.show_delete_user = False
            st.rerun()

    with col2:
        if st.button("✅ Yes, Delete", key="confirm_delete_user"):
            try:
                for user_id in user_ids:
                    delete_user(user_id)
                st.success(f"Deleted {len(user_ids)} user(s)")
                st.session_state.show_delete_user = False
                st.rerun()
            except Exception as e:
                st.error(f"Failed to delete users: {str(e)}")

@st.dialog("Change Password")
def change_password_dialog(user_id):
    with st.form("change_password_form"):
        new_password = st.text_input("New Password*", type="password", placeholder="Enter new password")
        confirm_password = st.text_input("Confirm Password*", type="password", placeholder="Confirm new password")

        col1, col2 = st.columns(2)
        with col1:
            cancel_btn = st.form_submit_button("❌ Cancel", use_container_width=True)
        with col2:
            submit_btn = st.form_submit_button("✅ Change Password", use_container_width=True)

    if cancel_btn:
        st.session_state.show_change_password = False
        st.rerun()

    if submit_btn:
        if not new_password:
            st.error("Password is required")
            return

        if new_password != confirm_password:
            st.error("Passwords do not match")
            return

        if len(new_password) < 6:
            st.error("Password must be at least 6 characters")
            return

        try:
            change_password(user_id, new_password)
            st.success("Password changed successfully")
            st.session_state.show_change_password = False
            st.rerun()
        except Exception as e:
            st.error(f"Failed to change password: {str(e)}")

