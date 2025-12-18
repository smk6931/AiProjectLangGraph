from debug_utils import render_session_state_viewer
from menu_page import menu_page
from review_page import review_page
from dashboard import dashboard_page
from register import register_page
from login import login_page
import streamlit as st
import sys
import os

# ui 디렉토리를 path에 추가 (필요시)
st.session_state.user_email = "email"

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

        # 페이지 이름과 내부 키 매핑
        nav_options = {
            "🏠 대시보드": "dashboard",
            "🍴 메뉴 조회": "menu_page",
            "💬 리뷰 관리": "review_page"
        }

        # 현재 페이지의 index 찾기
        current_idx = 0
        current_page = st.session_state.page
        for i, val in enumerate(nav_options.values()):
            if val == current_page:
                current_idx = i
                break

        selection = st.radio(
            "이동하기",
            list(nav_options.keys()),
            index=current_idx
        )

        st.session_state.page = nav_options[selection]

        st.divider()
        if st.button("로그아웃"):
            st.session_state.clear()
            st.session_state.page = "login"
            st.rerun()

        # --- 디버그 세션 조회 컴포넌트 추가 ---
        render_session_state_viewer()

# --- 페이지 라우팅 ---
if st.session_state.page == "login":
    login_page()

elif st.session_state.page == "register":
    register_page()

elif st.session_state.page == "dashboard":
    dashboard_page()

elif st.session_state.page == "menu_page":
    menu_page()

elif st.session_state.page == "review_page":
    review_page()
