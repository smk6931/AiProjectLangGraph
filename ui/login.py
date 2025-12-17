# app/ui/login.py
import streamlit as st
import requests

API_URL = "http://localhost:8080"

def login_page():
    st.title("🔐 Login")

    email = st.text_input("Email")
    password = st.text_input("Password", type="password")

    if st.button("Login"):
        res = requests.post(
            f"{API_URL}/user/login",
            json={"email": email}
        )

        if res.status_code == 200:
            st.session_state.user_email = email
            st.session_state.page = "dashboard"
            st.rerun()
        else:
            st.error("로그인 실패")

    st.button("회원가입", on_click=lambda: go_register())

def go_register():
    st.session_state.page = "register"