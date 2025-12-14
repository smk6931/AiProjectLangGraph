# app/ui/main.py
import streamlit as st
import requests

API_URL = "http://localhost:8080"

st.set_page_config(page_title="AI Project Login", layout="centered")

if "page" not in st.session_state:
    st.session_state.page = "login"

def go_login():
    st.session_state.page = "login"

def go_register():
    st.session_state.page = "register"

# 로그인 화면
if st.session_state.page == "login":
    st.title("🔐 Login")

    email = st.text_input("Email")
    password = st.text_input("Password", type="password")

    if st.button("Login"):
        res = requests.post(
            f"{API_URL}/login",
            json={"user_email": email}
        )
        if res.status_code == 200:
            st.success("로그인 성공")
        else:
            st.error("로그인 실패")

    st.button("회원가입", on_click=go_register)

# 회원가입 화면
if st.session_state.page == "register":
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
            go_login()
        else:
            st.error("회원가입 실패")

    st.button("뒤로가기", on_click=go_login)
