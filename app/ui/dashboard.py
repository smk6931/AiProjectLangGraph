# app/ui/dashboard.py
import streamlit as st

def dashboard_page():
    st.title("🚀 Dashboard")

    st.write(f"환영합니다 👋 {st.session_state.get('user_email')}")

    st.subheader("🧠 AI Agent")
    if st.button("AI 판단 실행 (더미)"):
        st.info("여기에 Gemini / Agent 로직 연결")

    st.divider()

    if st.button("로그아웃"):
        st.session_state.clear()
        st.session_state.page = "login"
        st.rerun()
