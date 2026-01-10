import streamlit as st

def render_architecture():
    st.header("5. 🏗️ System Architecture")
    st.caption("Router Pattern & Hybrid Agent Pipeline")

    st.markdown("""
    **Architecture Logic**:
    사용자의 질문/요청이 들어오면 **Router**가 의도를 파악하여 적절한 전문 에이전트에게 라우팅합니다.
    """)

    # Mermaid Diagram
    st.image("https://mermaid.ink/img/pako:eNplkktvwjAMx7_KyXlA4tBLB9TuMCG022rTS6w0akpSnAZCffcl5UW7TfH3s_3_bMc5lUYFSpD1q-y0eWDoPFlzch_tW-fM2W2028Z-7IeP8TD0g3C0-zh0_eFjHIbB7iYID8PtdhgGo937OLj70w_3H_vhcPe-96N_20nBChU0hApqqG1eSclz4R_Qk8K51KxQeW6U4rmwUjHheE7JCo2hS-iS1pW1c3-I0hV6Q91QZ-h_oTv0gV7zXCljVqg810rx96nQeO7S-hO05F7W3lD_QvclT9S9Urxk7-Vz6xJ6T89L3hX6E_QoVFaQo1hAhmIOGYp5ZCiWkKFYRoZipQxQk2GAmgyj1GQYoSbDgJoMA9RkGKSmlL5YQYZaGaoVZKjVkKG2ghy1Msql-g9Qk1Eu9X-gJqNcGv5ATUa5NPyBmoxyKfgDNRnlcl0y1N5QuyFD7Q21GzLU3lC7IUOtjHI5_gPUZJRLe4D6X4xyaQ9Qk1Eu7QFqMspv6y-oxSi_rb-AFvN0y2_rL6jFKL-tv4B-i_8BFm0zCQ?type=png")
    
    c1, c2 = st.columns(2)
    with c1:
        st.markdown("### 📊 Report Pipeline (Batch)")
        st.write("1. **Fetch**: DB 수집 & Python 선행 계산")
        st.write("2. **Reason**: LLM이 수치를 보고 원인 분석")
        st.write("3. **Save**: JSON(Tag) 형태로 DB 저장")
    
    with c2:
        st.markdown("### 💬 Inquiry Pipeline (Real-time)")
        st.write("1. **Intent**: 질문 의도 분류 (Router)")
        st.write("2. **Tool Use**: RAG 검색 / Web Search")
        st.write("3. **Answer**: 문맥을 고려한 최종 답변")
