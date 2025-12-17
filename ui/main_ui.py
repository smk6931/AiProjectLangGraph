import streamlit as st

from login import login_page
from register import register_page
from dashboard import dashboard_page

st.set_page_config(page_title="AI Project", layout="centered")

if "page" not in st.session_state:
    st.session_state.page = "dashboard"

if st.session_state.page == "login":
    login_page()

elif st.session_state.page == "register":
    register_page()

elif st.session_state.page == "dashboard":
    dashboard_page()