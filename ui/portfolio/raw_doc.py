import streamlit as st
import os

def render_raw_doc():
    st.subheader("📜 Full Document (Markdown)")
    try:
        # 루트 기준 경로
        file_path = os.path.join(os.getcwd(), "docs", "portfolio", "PORTFOLIO_MASTER.md")
        with open(file_path, "r", encoding="utf-8") as f:
            st.code(f.read(), language="markdown")
    except Exception as e:
        st.error(f"File not found: {e}")
