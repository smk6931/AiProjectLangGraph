import streamlit as st

def render_intro():
    st.markdown("""
    <style>
        .hero {
            padding: 2rem;
            border-radius: 10px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            text-align: center;
            margin-bottom: 2rem;
        }
        .hero h1 {
            color: white;
            font-size: 3rem;
            font-weight: 700;
        }
        .hero p {
            font-size: 1.2rem;
            opacity: 0.9;
        }
    </style>
    <div class="hero">
        <h1>AI Franchise Manager</h1>
        <p>"단순한 자동화를 넘어, 생각하고 판단하는 AI 매니저"</p>
    </div>
    """, unsafe_allow_html=True)

    # 핵심 가치 (3 Columns)
    c1, c2, c3 = st.columns(3)
    
    with c1:
        st.container(border=True)
        st.markdown("### 📊 Auto Report")
        st.write("클릭 한 번 없이 매일 아침 분석되는 **주간 매출 리포트**")
    
    with c2:
        st.container(border=True)
        st.markdown("### 💬 AI Inquiry")
        st.write("규정집을 뒤지지 마세요. **채팅으로 물어보면** AI가 답합니다.")
    
    with c3:
        st.container(border=True)
        st.markdown("### ☁️ SaaS Ready")
        st.write("AWS 클라우드 기반으로 **어디서든 접속 가능한** 웹 솔루션")

    st.divider()

    col1, col2 = st.columns([1, 2])
    with col1:
        st.info("**Development Overview**")
        st.markdown("""
        - **Period**: 2024.12 ~ 2025.01 (1 Month)
        - **Role**: Full Stack Logic (1인 개발)
        - **Domain**: 프랜차이즈, 요식업, 무인매장
        """)
    
    with col2:
        st.success("**Why this matters?**")
        st.write("""
        이 프로젝트는 단순한 '데모'가 아닙니다. 현업의 Pain Point(데이터 분석의 어려움)를 해결하기 위해
        **LangGraph의 순환 구조**와 **RAG 파이프라인**을 엔지니어링 관점에서 구현한 **실전형 프로젝트**입니다.
        """)
