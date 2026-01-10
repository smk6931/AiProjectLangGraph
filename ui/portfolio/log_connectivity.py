import streamlit as st

def render_log_connectivity():
    st.header("9. 🔥 Log #1: Connectivity Issue")
    st.caption("AWS Deployment & DB Connection Refused")

    st.markdown("### 🚨 The Incident")
    st.write("로컬(Windows)에서는 완벽하게 작동하던 코드가, AWS EC2(Ubuntu)에 배포하자마자 **DB 연결 에러**를 뿜으며 뻗어버림.")
    
    with st.expander("📄 Error Log (Click to view)", expanded=True):
        st.code("""
sqlalchemy.exc.OperationalError: (psycopg.OperationalError) 
connection to server at "127.0.0.1", port 5433 failed: Connection refused
Is the server running on that host and accepting TCP/IP connections?
        """, language="text")

    st.divider()

    st.markdown("### 🕵️ Root Cause Analysis")
    st.markdown("""
    1. **환경의 차이**: 
       - 로컬에서는 보안상 **SSH Tunneling**을 통해 `localhost:5433`으로 DB에 우회 접속함.
       - 서버는 RDS와 같은 VPC(사설망) 안에 있으므로 터널링이 불필요함.
    2. **설정 파일 실수**:
       - Git으로 코드를 배포하면서 `.env` 파일의 내용까지 로컬 설정(`localhost:5433`)이 그대로 적용됨.
    """)

    st.divider()

    st.markdown("### ✅ Solution")
    
    c1, c2 = st.columns(2)
    with c1:
        st.error("❌ Before (Local .env)")
        st.code("""
DB_HOST=127.0.0.1
DB_PORT=5433  <-- Tunneling Port
        """, language="bash")
    
    with c2:
        st.success("⭕ After (Server .env)")
        st.code("""
DB_HOST=database-aws.rds.amazonaws.com
DB_PORT=5432  <-- Direct Port
        """, language="bash")
        
    st.info("**Lesson Learned**: 배포 환경(Production)과 개발 환경(Dev)의 `.env`는 철저히 분리해서 관리해야 한다.")
