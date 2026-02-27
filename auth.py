import streamlit as st
from db.users import authenticate_user, get_user_by_id

def check_authentication():
    """
    Check if user is authenticated.
    Returns True if authenticated, False otherwise.
    """
    if "authenticated" not in st.session_state:
        st.session_state.authenticated = False
    
    if "user" not in st.session_state:
        st.session_state.user = None
    
    return st.session_state.authenticated

def login_user(username, password):
    """
    Attempt to log in a user.
    Returns True if successful, False otherwise.
    """
    user = authenticate_user(username, password)
    
    if user:
        st.session_state.authenticated = True
        st.session_state.user = {
            'id': user['id'],
            'username': user['username'],
            'full_name': user['full_name'],
            'email': user['email'],
            'is_admin': user['is_admin']
        }
        return True
    
    return False

def logout_user():
    """Log out the current user"""
    st.session_state.authenticated = False
    st.session_state.user = None
    # Clear other session state if needed
    for key in list(st.session_state.keys()):
        if key not in ['authenticated', 'user']:
            del st.session_state[key]

def get_current_user():
    """Get the currently logged-in user"""
    return st.session_state.get('user', None)

def is_admin():
    """Check if current user is an admin"""
    user = get_current_user()
    return user and user.get('is_admin', False)

def show_login_page():
    """Display the login page"""
    st.set_page_config(
        page_title="Login - Juniper Reporting App",
        page_icon=":lock:",
        layout="centered"
    )
    
    # Center the login form
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        st.title("🔐 Login")
        st.markdown("---")
        
        with st.form("login_form"):
            username = st.text_input("Username", placeholder="Enter your username")
            password = st.text_input("Password", type="password", placeholder="Enter your password")
            
            submit = st.form_submit_button("Login", use_container_width=True)
            
            if submit:
                if not username or not password:
                    st.error("Please enter both username and password")
                else:
                    if login_user(username, password):
                        st.success("Login successful!")
                        st.rerun()
                    else:
                        st.error("Invalid username or password")
        
        st.markdown("---")

def require_authentication():
    """
    Decorator/function to require authentication.
    Call this at the start of your app to enforce login.
    """
    if not check_authentication():
        show_login_page()
        st.stop()

