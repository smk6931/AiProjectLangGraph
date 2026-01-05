import streamlit as st

def render_feat_report():
    st.header("7. 🤖 Feat: AI Report Agent")
    st.caption("Batch Pipeline & Structured Output Strategy")

    # --- Section 1: Concept ---
    st.markdown("### 💡 Core Strategy: \"Engineering over Prompting\"")
    st.info("LLM에게 모든 걸 맡기지 않고, **Python의 계산 능력**과 **Regex의 파싱 능력**을 결합하여 무결성을 확보했습니다.")

    col1, col2 = st.columns(2)
    with col1:
        st.markdown("**❌ Bad Practice**")
        st.write("LLM에게 계산시키기: `123 + 456=?`")
        st.write("LLM에게 JSON 강제하기: `제발 JSON 줘`")
    
    with col2:
        st.markdown("**✅ My Solution**")
        st.write("Python Pre-calc: `sum([123, 456])`")
        st.write("Tag Parsing: `<SECTION> 내용 </SECTION>`")

    st.divider()

    # --- Section 2: Real Code (Tabs) ---
    st.subheader("💻 Implementation Details")
    tab1, tab2, tab3 = st.tabs(["State Design", "Analysis Logic", "Tag Parser"])

    with tab1:
        st.markdown("**LangGraph State Definition**")
        st.caption("데이터 흐름을 명확히 정의하여 노드 간 의존성을 관리합니다.")
        st.code("""
class ReportState(TypedDict):
    store_id: int
    store_name: str
    target_date: str 
    
    # Raw Data (DB Fetch)
    sales_data: List[Dict[str, Any]]
    reviews_data: List[Dict[str, Any]]
    
    # Pre-calculated Metrics (Python Logic)
    calculated_total_sales: float 
    calculated_prev_sales: float
    
    # Final Output
    final_report: Dict[str, Any]
    execution_logs: Annotated[List[str], append_logs]
        """, language="python")

    with tab2:
        st.markdown("**Hybrid Analysis Node**")
        st.caption("Python으로 통계(Growth Rate)를 먼저 계산하고, LLM에게 Context로 주입합니다.")
        st.code("""
# 1. Python Calculation (Reliability)
this_week_total = state["calculated_total_sales"]
prev_week_total = state.get("calculated_prev_sales", 0)
growth_rate = ((this_week_total - prev_week_total) / prev_week_total * 100)

# 2. Context Injection
prompt = f\"\"\"
현재 매출 성장률: {growth_rate:+.1f}%
이번주 총 매출: {int(this_week_total):,}원
데이터를 바탕으로 매출 변동 원인을 분석해줘.
\"\"\"
        """, language="python")

    with tab3:
        st.markdown("**Robust Tag Parsing**")
        st.caption("JSON 파싱 에러를 0%로 만들기 위한 정규식 전략입니다.")
        st.code("""
# LLM Output Example:
# <SECTION:SUMMARY>매출이 10% 올랐습니다.</SECTION:SUMMARY>

def extract_section(tag, text):
    pattern = f"<{tag}>(.*?)</{tag}>"
    match = re.search(pattern, text, re.DOTALL)
    return match.group(1).strip() if match else ""

summary = extract_section("SECTION:SUMMARY", raw_text)
# 결과: "매출이 10% 올랐습니다." (안전함)
        """, language="python")

    st.divider()
    
    # --- Section 3: Result Visual ---
    st.subheader("📉 Final Output (Process Flow)")
    st.graphviz_chart("""
    digraph G {
        rankdir=LR;
        node [shape=box];
        
        DB [label="PostgreSQL\n(Sales/Review)", shape=cylinder];
        Fetch [label="Fetch Node\n(Data Gathering)"];
        Calc [label="Python Calc\n(Metrics)", style=filled, fillcolor="#e6f3ff"];
        LLM [label="LLM Analysis\n(Reasoning)", style=filled, fillcolor="#fff0e0"];
        Parser [label="Tag Parser\n(Validation)"];
        Save [label="Save DB"];
        
        DB -> Fetch;
        Fetch -> Calc;
        Calc -> LLM [label="Context"];
        LLM -> Parser [label="Raw Text"];
        Parser -> Save [label="Structured Data"];
    }
    """)
