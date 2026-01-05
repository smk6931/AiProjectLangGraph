import streamlit as st
import os
import sys

# 컴포넌트 임포트 (경로 문제 해결)
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# 📁 Modular Components Import
from portfolio.intro import render_intro
from portfolio.planning import render_planning
from portfolio.tech_stack import render_tech_stack
from portfolio.schema import render_schema
from portfolio.architecture import render_architecture
from portfolio.api import render_api
from portfolio.feat_report import render_feat_report
from portfolio.feat_inquiry import render_feat_inquiry
from portfolio.log_connectivity import render_log_connectivity
from portfolio.log_json import render_log_json
from portfolio.log_rag import render_log_rag
from portfolio.roadmap import render_roadmap
from portfolio.raw_doc import render_raw_doc

def render_portfolio_page():
    # --- 제목 섹션 ---
    st.title("👨‍💻 Developer's Technical Whitepaper")
    st.caption("AI Franchise Manager Project Portfolio (2024.12 ~ 2025.01)")
    
    st.divider()

    # --- 레이아웃 구성: 왼쪽(목차) / 오른쪽(내용) ---
    col_nav, col_content = st.columns([1, 4])

    with col_nav:
        st.subheader("📚 Chapters")
        
        # 목차 리스트 정의 (함수 매핑)
        chapters = {
            "1. Project Overview": render_intro,
            "2. Planning Intent": render_planning,
            "3. Tech Stack Strategy": render_tech_stack,
            "4. Database Schema": render_schema,
            "5. System Architecture": render_architecture,
            "6. API Specification": render_api,
            "7. Feat: Report Agent": render_feat_report,
            "8. Feat: Inquiry Agent": render_feat_inquiry,
            "9. Log #1: Connectivity": render_log_connectivity,
            "10. Log #2: JSON Parsing": render_log_json,
            "11. Log #3: RAG Accuracy": render_log_rag,
            "12. Future Roadmap": render_roadmap,
            "📜 Full Document (Raw)": render_raw_doc
        }
        
        # 라디오 버튼으로 챕터 선택
        selected_chapter_name = st.radio(
            "Go to Section:",
            list(chapters.keys()),
            label_visibility="collapsed"
        )
        
        # 선택된 렌더링 함수 가져오기
        render_function = chapters[selected_chapter_name]

    # --- 콘텐츠 렌더링 ---
    with col_content:
        # 깔끔하게 해당 함수만 실행 (지저분한 if-elif 제거)
        render_function()
