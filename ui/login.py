# app/ui/login.py
import streamlit as st
from api_utils import post_api


def login_page():
    st.title("🔐 Login")

    email = st.text_input("Email")
    password = st.text_input("Password", type="password")

    if st.button("Login"):
        res_data = post_api("/user/login", json_data={"email": email})

        if res_data:
            st.session_state.user_email = email
            st.session_state.page = "dashboard"
            st.rerun()

    st.button("회원가입", on_click=lambda: go_register())


def go_register():
    st.session_state.page = "register"
