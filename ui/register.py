# app/ui/register.py
import streamlit as st
from api_utils import post_api


def register_page():
    st.title("📝 Register")

    email = st.text_input("Email")

    if st.button("Register"):
        res_data = post_api("/user/register", json_data={"email": email})

        if res_data:
            st.success("회원가입 성공! 로그인해주세요.")
            st.session_state.page = "login"
            st.rerun()

    st.button("로그인으로 이동", on_click=lambda: go_login())


def go_login():
    st.session_state.page = "login"
