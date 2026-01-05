import streamlit as st

def render_api():
    st.header("6. 🔌 API Specification")
    st.caption("FastAPI & RESTful Design")

    st.info("프론트엔드(Streamlit)와 AI 로직(LangGraph)은 **API로 완전히 분리**되어 있습니다.")

    tab1, tab2, tab3 = st.tabs(["💬 Chat API", "📊 Report API", "📈 Data API"])

    with tab1:
        st.subheader("POST /api/v1/inquiry")
        st.write("사용자 질문을 받아 스트리밍 답변을 반환합니다.")
        st.code("""
{
  "query": "이번주 배달 매출 얼마야?",
  "store_id": 1,
  "history": [...] 
}
        """, language="json")

    with tab2:
        st.subheader("POST /api/v1/report/generate")
        st.write("특정 날짜 기준으로 AI 리포트 생성을 트리거합니다. (Batch Job)")
        st.code("""
{
  "target_date": "2025-01-04",
  "store_id": 1
}
# Response: { "status": "success", "report_id": 101 }
        """, language="json")
    
    with tab3:
        st.subheader("GET /api/v1/sales/daily")
        st.write("차트 렌더링을 위한 시계열 원본 데이터를 조회합니다.")
        st.code("""
# Query Params
?store_id=1&start_date=2024-12-01&end_date=2024-12-31
        """, language="http")
