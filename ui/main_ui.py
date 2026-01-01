from menu_page import menu_page
from review_page import review_page
from dashboard import dashboard_page
from register import register_page
from login import login_page
from inquiry_page import inquiry_page
from guide_page import guide_page
from about_project import about_page
import streamlit as st
import sys
import os

# ui 디렉토리를 path에 추가 (필요시)
st.session_state.user_email = "email"

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

st.set_page_config(page_title="AI Project", layout="wide")

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
        st.title("📌 관리 메뉴")
        st.markdown("👋 환영합니다, **점주님**!")
        
        st.divider()

        # 페이지 이름과 내부 키 매핑 (순서 변경: AI 매니적 최상단)
        # '프로젝트 구조'는 별도로 뺌
        nav_options = {
            "🧠 AI 매니저 (Main)": "inquiry_page", 
            "📊 총매출/AI 분석": "dashboard",
            "🍴 메뉴 조회": "menu_page",
            "💬 리뷰 관리": "review_page",
            "📚 매뉴얼 & 규정": "guide_page"
        }

        # 현재 페이지의 index 찾기
        current_idx = 0
        current_page = st.session_state.page
        
        # 'about_project' 페이지에 있을 때는 라디오 버튼 선택 해제 효과를 위해 index 조작 필요하지만
        # Streamlit 라디오는 선택 해제가 안되므로, 가장 가까운 메뉴나 기본값 유지.
        # 여기선 Main이 선택된 것처럼 보이게 하거나, 별도 처리.
        if current_page == "about_project":
             # 사이드바 메뉴에는 없지만 페이지는 About인 상태.
             # 라디오 버튼은 그냥 'AI 매니저'나 이전에 선택했던걸 가리키게 둠.
             pass
        elif current_page not in nav_options.values():
            current_page = "inquiry_page"
            
        # 역매핑 (Value -> Key)
        val_to_key = {v: k for k, v in nav_options.items()}
        default_key = val_to_key.get(current_page, "🧠 AI 매니저 (Main)")
        
        # 라디오 버튼 인덱스 찾기
        keys = list(nav_options.keys())
        try:
            current_idx = keys.index(default_key)
        except:
            current_idx = 0

        selection = st.radio(
            "이동하기",
            keys,
            index=current_idx,
            label_visibility="collapsed"
        )
        
        # 사용자가 라디오 버튼을 클릭했을 때만 페이지 변경 로직 작동하도록
        # (About 프로젝트 버튼 클릭 시 강제로 페이지가 바뀌므로 충돌 방지)
        if st.session_state.page != "about_project":
             st.session_state.page = nav_options[selection]
        else:
             # About 페이지 상태에서도 라디오를 누르면 이동해야 함.
             # 하지만 selection은 이미 변경된 상태일 수 있음.
             # 단순하게: 라디오 값이 바뀌면 무조건 이동.
             if nav_options[selection] != "inquiry_page" and st.session_state.page == "about_project": 
                 # Main이 아닌 다른거 누르면 이동
                 st.session_state.page = nav_options[selection]
             elif nav_options[selection] == "inquiry_page" and st.session_state.page == "about_project":
                 # About 상태에서 Main 누르면 이동해야하는데, 라디오 기본값이 Main이라 감지가 안될 수 있음.
                 # 버튼 방식이 깔끔함.
                 pass
        
        # 라디오 로직 보정: selection이 현재 page와 다르면 이동 (가장 확실)
        if nav_options[selection] != st.session_state.page and st.session_state.page != "about_project":
             st.session_state.page = nav_options[selection]
        # About 페이지에서 메뉴로 복귀하는 로직은 버튼 클릭 시 처리됨

        st.divider()
        
        # [NEW] 하단 프로젝트 정보 섹션
        st.caption("Developed by Antigravity")
        if st.button("🛠️ 프로젝트 기술 구조 (About)", use_container_width=True):
             st.session_state.page = "about_project"
             st.rerun()

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

elif st.session_state.page == "about_project":
    about_page()
