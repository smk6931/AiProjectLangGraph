import streamlit as st
# import Graphviz

def about_page():
    st.title("🛠️ Project Architecture & Tech Stack")
    st.markdown("---")

    # 1. Project Overview
    st.header("1. 프로젝트 개요")
    st.info("""
    **"AI 프랜차이즈 매니저 (SOS)"**는 점주들의 매장 운영을 돕기 위해 설계된 **LangGraph 기반의 멀티 에이전트 시스템**입니다.
    단순한 챗봇을 넘어, **실시간 매출 데이터 분석**, **매뉴얼/규정 RAG 검색**, 그리고 **웹 검색을 통한 할루시네이션 방지** 기능을 통합하여
    실질적인 운영 솔루션을 제공합니다.
    """)

    # 2. System Architecture (Graphviz)
    st.header("2. 시스템 아키텍처 (System Architecture)")
    st.markdown("LangGraph를 활용한 **Stateful Multi-Agent Workflow** 구조입니다.")
    
    st.graphviz_chart("""
        digraph {
            rankdir=LR;
            node [shape=box, style="filled,rounded", fontname="Malgun Gothic", fillcolor="white"];
            edge [color="#666666"];
            
            User [label="👤 사용자 (User)", shape=oval, fillcolor="#FFD700", style="filled,bold"];
            Router [label="🤖 Intent Router\n(GPT-4o)", fillcolor="#87CEEB"];
            
            subgraph cluster_agents {
                label = "Core Agents Modules";
                style=dashed;
                color="#444444";
                bgcolor="#f9f9f9";
                
                Diagnosis [label="📊 Diagnosis Agent\n(매출 분석 & SQL Gen)", fillcolor="#98FB98"];
                Manual [label="📘 Manual RAG\n(Vector Search)", fillcolor="#FFB6C1"];
                Web [label="🌐 Google Search\n(Gemini Grounding)", fillcolor="#E0E0E0"];
            }
            
            Validation [label="✅ Contextual Check\n(Relevancy Filter)", fillcolor="#FFDEAD"];
            Answer [label="💬 Answer Synthesis\n(Structured Output)", fillcolor="#87CEFA"];
            
            User -> Router [label="질문 입력"];
            Router -> Diagnosis [label="매출 문의", color="green", penwidth=2];
            Router -> Manual [label="규정/매뉴얼", color="red", penwidth=2];
            
            Diagnosis -> Answer [label="Data Context"];
            Manual -> Validation [label="Docs"];
            
            Validation -> Web [label="유사도 낮음", style="dashed", color="orange"];
            Validation -> Answer [label="유사도 높음", color="blue"];
            Web -> Answer [label="Web Results"];
        }
    """)
    
    # 3. DB Schema (ERD)
    st.header("3. 데이터베이스 설계 (PostgreSQL)")
    st.markdown("매장 운영에 필요한 핵심 데이터를 **관계형 데이터베이스(RDBMS)**로 정규화하여 관리합니다.")
    
    st.graphviz_chart("""
        graph {
            rankdir=LR;
            node [shape=record, fontname="Malgun Gothic", fontsize=10];
            
            Stores [label="🏢 STORES | {store_id (PK)|store_name|region}"];
            Menus [label="🍔 MENUS | {menu_id (PK)|menu_name|category|price}"];
            Orders [label="🧾 ORDERS | {order_id (PK)|store_id (FK)|menu_id (FK)|ordered_at|quantity}"];
            Reviews [label="⭐ REVIEWS | {review_id (PK)|order_id (FK)|rating|review_text}"];
            SalesDaily [label="📈 SALES_DAILY | {date|store_id|total_sales|weather_info}"];
            
            Stores -- Orders [label="1:N"];
            Menus -- Orders [label="1:N"];
            Orders -- Reviews [label="1:1"];
            Stores -- SalesDaily [label="1:N"];
        }
    """)

    # 4. Tech Stack & Features
    st.header("4. 핵심 기술 및 구현 특징")
    
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("🔧 Tech Stack")
        st.markdown("""
        - **LLM Orchestration**: LangChain, LangGraph (State Management)
        - **Model**: OpenAI GPT-4o (Reasoning), Gemini 2.0 Flash (Grounding)
        - **Backend**: FastAPI (Async Server)
        - **Database**: PostgreSQL (AWS RDS Compatible)
        - **Frontend**: Streamlit (Dashboard UI)
        - **Deployment**: AWS EC2 (Ubuntu), Nginx (Reverse Proxy)
        """)
        
    with col2:
        st.subheader("✨ Key Features")
        st.markdown("""
        1.  **Hallucination Control**:
            - DB 데이터 부재 시 "데이터 없음" 명시.
            - RAG 유사도 기반 **Gemini Grounding (Web Search)** 연동.
        2.  **Smart Period Analysis**:
            - 시스템 날짜가 아닌 **DB 데이터 기준(Data-Driven)**으로 분석 기간 자동 보정.
        3.  **Structured Output**:
            - 단순 텍스트가 아닌 **JSON 기반 구조화된 응답**으로 UI 시각화 연동.
        """)

if __name__ == "__main__":
    about_page()
