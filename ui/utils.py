"""Shared UI utilities"""
import streamlit as st


def create_dismiss_handler(dialog_key, cleanup_keys=None):
    """
    Universal dismiss handler factory.

    Args:
        dialog_key: The session state key for the dialog (e.g., 'show_add_customer')
        cleanup_keys: Optional list of session state keys to delete on dismiss
    """
    def handler():
        st.session_state[dialog_key] = False
        if cleanup_keys:
            for key in cleanup_keys:
                if key in st.session_state:
                    del st.session_state[key]
    return handler

