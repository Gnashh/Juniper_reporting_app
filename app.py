import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

import streamlit as st
from streamlit_option_menu import option_menu
from auth import require_authentication, logout_user, get_current_user, is_admin
from user_management import show_user_management
from ui.customers.customer_page import show_customer_page
from ui.devices.device_page import show_device_page
from ui.templates.template_page import show_template_page
from ui.reports.report_page import show_report_page

# -----------------------------
# Authentication Check
# -----------------------------
# This must be called before any other Streamlit code
require_authentication()

# -----------------------------
# Page config
# -----------------------------
st.set_page_config(
    page_title="Report App",
    page_icon=":bar_chart:",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Get current user info
current_user = get_current_user()

st.title("Reporting App")
if current_user:
    st.caption(f"👤 Logged in as: **{current_user['full_name'] or current_user['username']}**")

# -----------------------------
# Sidebar menu
# -----------------------------
with st.sidebar:
    # Build menu options based on user role
    menu_options = [
        "Customer Details",
        "Device Details",
        "Template Details",
        "Report Details and Generate Report"
    ]

    # Add User Management for admins
    if is_admin():
        menu_options.append("User Management")

    selected = option_menu(
        menu_title="MAIN MENU",
        options=menu_options
    )

    st.markdown("---")

    # User info and logout button
    if current_user:
        st.markdown(f"**👤 User:** {current_user['username']}")
        if current_user.get('is_admin'):
            st.markdown("**🔑 Role:** Administrator")
        else:
            st.markdown("**🔑 Role:** User")

        if st.button("🚪 Logout", use_container_width=True):
            logout_user()
            st.rerun()

# -----------------------------
# Page routing
# -----------------------------
if selected == "Customer Details":
    show_customer_page()

elif selected == "Device Details":
    show_device_page()

elif selected == "Template Details":
    show_template_page()

elif selected == "Report Details and Generate Report":
    show_report_page()

elif selected == "User Management":
    show_user_management()
