from menu_page import menu_page
from dashboard import dashboard_page
from register import register_page
from login import login_page
import streamlit as st
import sys
import os

# ui 디렉토리를 path에 추가 (필요시)
sys.path.append(os.path.dirname(os.path.abspath(__file__)))


st.set_page_config(page_title="AI Project", layout="wide")

# 세션 상태 초기화
if "page" not in st.session_state:
    st.session_state.page = "dashboard"

# 로그인 상태 확인 및 리다이렉트 (로그인 안 된 경우)
if "user_email" not in st.session_state:
    if st.session_state.page not in ["login", "register"]:
        st.session_state.page = "login"

# --- 사이드바 내비게이션 (로그인한 경우만 표시) ---
if "user_email" in st.session_state:
    with st.sidebar:
        st.title("📌 관리 메뉴")
        st.write(f"접속 중: {st.session_state.user_email}")

        selection = st.radio(
            "이동하기",
            ["대시보드", "메뉴 조회"],
            index=0 if st.session_state.page == "dashboard" else 1
        )

        # 라디오 버튼 선택에 따른 페이지 변경
        if selection == "대시보드":
            st.session_state.page = "dashboard"
        elif selection == "메뉴 조회":
            st.session_state.page = "menu_page"

        st.divider()
        if st.button("로그아웃"):
            st.session_state.clear()
            st.session_state.page = "login"
            st.rerun()

# --- 페이지 라우팅 ---
if st.session_state.page == "login":
    login_page()

elif st.session_state.page == "register":
    register_page()

elif st.session_state.page == "dashboard":
    dashboard_page()

elif st.session_state.page == "menu_page":
    menu_page()
