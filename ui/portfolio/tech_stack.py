import streamlit as st

def render_tech_stack():
    st.header("3. 🛠️ Tech Stack Strategy")
    st.caption("기술 스택 선정 이유")

    # 탭으로 구분
    tab_core, tab_back, tab_data = st.tabs(["🧠 AI Core", "🔌 Backend & Infra", "💾 Data"])

    with tab_core:
        c1, c2 = st.columns([1, 2])
        with c1:
            st.markdown("### LangGraph")
            st.write("Stateful Agent Framework")
        with c2:
            st.info("**Selection Reason**")
            st.write("""
            LangChain의 단순한 Chain(선형) 구조로는 복잡한 에이전트 행동을 구현하기 어렵습니다.
            **상태(State) 유지, 순환(Cycle), 수정(Correction)**이 가능한 LangGraph를 도입하여
            **'생각하고 스스로 고치는'** 에이전트를 설계했습니다.
            """)
            st.code("StateGraph(ReportState) -> Fetch -> Analyze -> Save", language="python")

    with tab_back:
        col1, col2 = st.columns(2)
        with col1:
            st.container(border=True)
            st.markdown("#### Backend: FastAPI")
            st.write("✅ **Async IO**: 비동기 처리에 최적화")
            st.write("✅ **Pydantic**: 완벽한 타입 검증")
            st.write("✅ **Swagger**: 문서 자동화")
        
        with col2:
            st.container(border=True)
            st.markdown("#### Infra: AWS EC2")
            st.write("✅ **Ubuntu LTS**: 안정적인 리눅스 환경")
            st.write("✅ **SSH Tunneling**: 보안 접속 구현")
            st.write("✅ **Nohup**: 백그라운드 프로세스 관리")

    with tab_data:
        st.markdown("### PostgreSQL + pgvector (Hybrid DB)")
        st.warning("일반적인 RDB따로, Vector DB(Pinecone)따로 쓰면 관리가 복잡합니다.")
        st.success("""
        **단일 DB 전략**: 
        PostgreSQL 하나에 **매출 데이터(Relational)**와 **매뉴얼 임베딩(Vector)**을 모두 담았습니다.
        이로 인해 조인(Join)과 트랜잭션 관리가 획기적으로 단순해졌습니다.
        """)
        
        st.graphviz_chart("""
        digraph DB {
            rankdir=LR;
            node [shape=box];
            Store [label="Stores Table"];
            Sales [label="Sales Table"];
            Vector [label="Embedding Table\n(pgvector)", style=filled, fillcolor="#ffeeee"];
            
            Store -> Sales;
            Store -> Vector [label="Hybrid Search"];
        }
        """)
