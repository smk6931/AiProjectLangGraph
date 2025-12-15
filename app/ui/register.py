# app/ui/register.py
import streamlit as st
import requests

API_URL = "http://localhost:8080"

def register_page():
    st.title("📝 Register")

    email = st.text_input("Email")
    nickname = st.text_input("Nickname")
    password = st.text_input("Password", type="password")

    if st.button("Register"):
        res = requests.post(
            f"{API_URL}/user/create",
            json={
                "email": email,
                "nickname": nickname,
                "password_hash": password
            }
        )

        if res.status_code == 200:
            st.success("회원가입 성공")
            st.session_state.page = "login"
            st.rerun()
        else:
            st.error("회원가입 실패")

    st.button("뒤로가기", on_click=lambda: go_login())

def go_login():
    st.session_state.page = "login"
