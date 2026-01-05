import streamlit as st

def render_feat_inquiry():
    st.header("8. 💬 Feat: Inquiry Agent")
    st.caption("Adaptive RAG & Web Search Pipeline")

    st.markdown("### 💡 Core Strategy: \"Router Pattern\"")
    st.info("모든 질문을 벡터 검색에 넣지 않습니다. **질문의 의도**에 따라 가장 적합한 도구를 선택합니다.")
    
    # --- Section 1: Concept Visual ---
    st.graphviz_chart("""
    digraph Router {
        rankdir=LR;
        node [shape=box, style=filled, fillcolor="white"];
        
        Question [label="User Query", shape=ellipse, fillcolor="#FFD700"];
        Router [label="LLM Router", fillcolor="#87CEEB"];
        
        Tool1 [label="Sales Node\n(Text-to-SQL)", fillcolor="#FFB6C1"];
        Tool2 [label="Manual Node\n(pgvector RAG)", fillcolor="#98FB98"];
        Tool3 [label="Policy/Web Node\n(Tavily Search)", fillcolor="#D3D3D3"];
        
        Question -> Router;
        Router -> Tool1 [label="매출/통계"];
        Router -> Tool2 [label="기기/레시피"];
        Router -> Tool3 [label="규정/트렌드"];
    }
    """)

    st.divider()

    # --- Section 2: Real Code (Tabs) ---
    st.subheader("💻 Implementation Details")
    tab1, tab2, tab3 = st.tabs(["Router Logic", "Adaptive Stream", "Tool Integration"])
    
    with tab1:
        st.markdown("**LLM Router Node**")
        st.write("사용자의 자연어 질문을 분석하여 `sales`, `manual`, `policy` 3가지 카테고리로 분류합니다.")
        st.code("""
# app/inquiry/nodes/router.py

prompt = f\"\"\"
질문의 핵심 의도를 파악하여 분류하세요.
질문: "{question}"

1. sales: 매출, 판매량, 주문 건수 (DB 조회)
2. manual: 기기 조작, 고장 수리, 레시피 (매뉴얼 검색)
3. policy: 매장 규정, 외부 트렌드, 날씨 (웹/규정 검색)

[Output JSON]
{{"category": "sales" | "manual" | "policy", "reason": "이유"}}
\"\"\"
        """, language="python")

    with tab2:
        st.markdown("**Steaming Flow Control**")
        st.write("`yield`를 사용하여 각 단계의 진행 상황을 UI에 실시간으로 중계합니다.")
        st.code("""
# app/inquiry/inquiry_agent.py

async def run_final_answer_stream(...):
    if category == "sales":
        yield json.dumps({"step": "sales", "message": "📉 매출 데이터 분석 중..."})
        state = await diagnosis_node(state)  # Wait for SQL/Analysis
        
    elif mode == "web":
        yield json.dumps({"step": "web", "message": "🌐 외부 트렌드 검색 중..."})
        state = await web_search_node(state) # Tavily API
        
    yield json.dumps({"step": "answer", "message": "✍️ 답변 작성 중..."})
        """, language="python")

    with tab3:
        st.markdown("**Tavily Web Search Integration**")
        st.write("단순 RAG로 해결되지 않는 '최신 정보(트렌드, 날씨)'는 외부 검색 도구를 연결했습니다.")
        st.code("""
# app/clients/tavily.py (Example)

tavily = TavilyClient(api_key=TAVILY_API_KEY)
response = tavily.search(query="요즘 뜨는 디저트 트렌드", search_depth="advanced")

# Context Injection
context = "\\n".join([res['content'] for res in response['results']])
prompt = f"다음 검색 결과를 바탕으로 답변해: {context}"
        """, language="python")

    st.divider()

    st.success("""
    **Conclusion**: 
    단일 LLM에 의존하지 않고, **SQL DB + Vector DB + Web Search**를 상황에 맞게 스위칭하는 
    **오케스트레이션(Orchestration)** 능력이 핵심입니다.
    """)
