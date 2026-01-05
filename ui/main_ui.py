from debug_utils import render_session_state_viewer
from menu_page import menu_page
from review_page import review_page
from dashboard import dashboard_page
from register import register_page
from login import login_page
from inquiry_page import inquiry_page
from guide_page import guide_page
import streamlit as st
import sys
import os

# ui 디렉토리를 path에 추가 (필요시)
st.session_state.user_email = "email"

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

st.set_page_config(page_title="AI Project", layout="wide")

# 스타일 적용 (전역)
try:
    from styles import apply_custom_styles
    apply_custom_styles()
except ImportError:
    pass

# 세션 상태 초기화
if "page" not in st.session_state:
    st.session_state.page = "inquiry_page" # AI 매니저를 메인으로 설정

# 로그인 상태 확인 및 리다이렉트 (로그인 안 된 경우)
if "user_email" not in st.session_state:
    if st.session_state.page not in ["login", "register"]:
        st.session_state.page = "login"

# --- 사이드바 내비게이션 (로그인한 경우만 표시) ---
if "user_email" in st.session_state:
    with st.sidebar:
        st.title("관리 메뉴")
        st.markdown("환영합니다, **점주님**!")
        
        st.divider()

        # 페이지 이름과 내부 키 매핑
        nav_options = {
            "AI 매니저 (Main)": "inquiry_page", 
            "총매출/AI 분석": "dashboard",
            "메뉴 조회": "menu_page",
            "리뷰 관리": "review_page",
            "매뉴얼 & 규정": "guide_page",
            # "👨‍💻 개발자 노트 (Portfolio)": "portfolio_page"
        }

        # 현재 페이지의 index 찾기
        current_idx = 0
        current_page = st.session_state.page
        
        # 값이 없는 경우(예: 외부 요인으로 페이지가 바뀐 경우) 방어
        if current_page not in nav_options.values():
            current_page = "inquiry_page"
            
        for i, val in enumerate(nav_options.values()):
            if val == current_page:
                current_idx = i
                break

        selection = st.radio(
            "이동하기",
            list(nav_options.keys()),
            index=current_idx,
            label_visibility="collapsed"
        )
        
        st.session_state.page = nav_options[selection]

        # st.divider()
        # if st.button("로그아웃"):
        #     st.session_state.clear()
        #     st.session_state.page = "login"
        #     st.rerun()

        # --- 디버그 세션 조회 컴포넌트 추가 ---
        render_session_state_viewer()

# --- 페이지 라우팅 ---
if st.session_state.page == "login":
    login_page()

elif st.session_state.page == "register":
    register_page()

elif st.session_state.page == "dashboard":
    dashboard_page()

elif st.session_state.page == "inquiry_page":
    inquiry_page()

elif st.session_state.page == "menu_page":
    menu_page()

elif st.session_state.page == "review_page":
    review_page()

elif st.session_state.page == "guide_page":
    guide_page()

# elif st.session_state.page == "portfolio_page":
#     from portfolio_page import render_portfolio_page
#     render_portfolio_page()
