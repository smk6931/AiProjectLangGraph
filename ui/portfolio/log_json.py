import streamlit as st

def render_log_json():
    st.header("10. 🔥 Log #2: LLM JSON Parsing Crash")
    st.caption("Reliability Engineering against Hallucination")

    st.markdown("### 🚨 The Incident")
    st.write("리포트 생성 도중 Python Backend가 500 Error를 내며 중단됨. 원인은 `json.loads()` 실패.")

    with st.expander("📄 Error Log (Click to view)", expanded=True):
        st.code("""
json.decoder.JSONDecodeError: Expecting ',' delimiter: line 5 column 20 (char 85)
File "app/report/report_graph.py", line 280, in analyze_data_node
    result = json.loads(llm_response)
        """, language="text")

    st.markdown("### 🕵️ Root Cause")
    st.write("LLM에게 \"JSON 포맷으로 줘\"라고 요청했으나, LLM이 가끔 실수함.")
    st.warning("예시: `{\"summary\": \"내용\" ... 설명입니다.}` (뒤에 사족을 붙임) 또는 Trailing Comma(`,`) 문제.")

    st.divider()

    st.markdown("### ✅ Solution: Tag Parsing")
    st.write("JSON 파싱을 포기하고, **Regex(정규식)** 기반의 태그 추출 방식으로 전환.")

    tab1, tab2 = st.tabs(["Prompt Change", "Python Code Changes"])
    
    with tab1:
        st.markdown("**Prompt Engineering**")
        st.code("""
(전) JSON 형식으로 출력해줘.
(후) 반드시 <SECTION:ANALYSIS> 태그 안에 분석 내용을 적어줘.
        """, language="text")
        
    with tab2:
        st.markdown("**Python Helper Function**")
        st.code("""
import re

def extract_section(tag, text):
    # 태그 안의 내용만 쏙 빼냄 (Dotall 옵션으로 줄바꿈 포함)
    pattern = f"<{tag}>(.*?)</{tag}>"
    match = re.search(pattern, text, re.DOTALL)
    if match:
        return match.group(1).strip()
    return "" # 실패 시 빈 문자열 반환 (Error 안 냄)

# 적용
analysis = extract_section("SECTION:ANALYSIS", llm_response)
        """, language="python")

    st.success("**Outcome**: 파이프라인 성공률 99% 이상 달성 (형식이 조금 깨져도 태그만 있으면 복구 가능)")
