# utils/ui_components.py
import streamlit as st

def show_success(msg):
    st.success(msg)

def show_error(msg):
    st.error(msg)

def download_button(data: bytes, filename: str, label: str):
    """Render a Streamlit download button reliably for bytes."""
    st.download_button(label=label, data=data, file_name=filename)
