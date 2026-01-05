import streamlit as st

def render_log_rag():
    st.header("11. 🔥 Log #3: RAG Accuracy")
    st.caption("Keyword Search vs Semantic Search")

    st.markdown("### 🚨 The Incident")
    st.write("사용자가 **'알바 복장 규정이 뭐야?'**라고 물었는데, 챗봇이 **'관련 정보를 찾을 수 없습니다'**라고 답변함.")
    st.info("하지만 DB에는 분명히 **'직원 유니폼 착용 가이드'**라는 문서가 존재했음.")

    st.divider()

    st.markdown("### 🕵️ Experiment: Why it failed?")
    st.write("두 가지 검색 방식의 차이를 비교 실험함.")

    col1, col2 = st.columns(2)
    with col1:
        st.container(border=True)
        st.markdown("#### 🔍 Keyword Match (SQL LIKE)")
        st.code("SELECT * FROM manuals WHERE content LIKE '%복장%'", language="sql")
        st.error("Result: 0건 (실패)")
        st.caption("텍스트에 '복장'이라는 단어가 100% 일치해야만 찾음. '유니폼'은 못 찾음.")

    with col2:
        st.container(border=True)
        st.markdown("#### 🧠 Vector Match (Cosine)")
        st.code("SELECT * FROM manuals ORDER BY embedding <=> query_vec LIMIT 1", language="sql")
        st.success("Result: '직원 유니폼 가이드' (유사도 0.88)")
        st.caption("'복장'과 '유니폼'이 문맥적으로 유사하다는 것을 벡터 공간에서 인식함.")

    st.divider()

    st.markdown("### ✅ Final Logic: Hybrid Search")
    st.write("단순히 벡터만 쓰면 '고유명사(제품명)' 검색이 약해질 수 있어서, 두 가지를 섞어서 사용.")
    
    st.code("""
# app/inquiry/nodes/retrieval.py

# 1. 키워드 검색 시도 (명확한 단어)
keyword_results = db.search_keyword(query)

# 2. 결과 없으면 벡터 검색 시도 (의미적 유사성)
if not keyword_results:
    vector_results = db.search_vector(query_embedding)
    
return vector_results
    """, language="python")
