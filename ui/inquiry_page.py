import streamlit as st
import requests
import json
import pandas as pd
import altair as alt
import os

# API URL 설정 (로컬/서버 환경 자동 감지)
API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8080")

# --------------------------------------------------------------------------
# [UI Component 1] LangGraph 아키텍처 다이어그램
# --------------------------------------------------------------------------
def show_langgraph_architecture():
    """LangGraph 아키텍처 다이어그램을 표시하는 함수"""
    with st.expander("🧠 AI Agent 아키텍처 (LangGraph 구조도)", expanded=False):
        st.markdown("**이 AI Agent는 사용자의 의도를 파악하여 최적의 경로로 라우팅합니다.**")
        st.graphviz_chart("""
            digraph {
                rankdir=LR;
                node [shape=box, style=filled, fillcolor="white", fontname="Malgun Gothic"];
                edge [color="#666666"];
                
                User [label="👤 사용자 질문", shape=oval, fillcolor="#FFD700", style="filled,bold"];
                Router [label="🤖 AI Router\n(의도 파악/LLM)", fillcolor="#87CEEB", style="filled,rounded"];
                
                subgraph cluster_tools {
                    label = "🛠️ Tools & Knowledge Base";
                    style=dashed;
                    color="#444444";
                    
                    DB [label="📊 Sales DB\n(PostgreSQL)", fillcolor="#98FB98"];
                    RAG_Manual [label="📘 Manual RAG\n(Vector DB)", fillcolor="#FFB6C1"];
                    RAG_Policy [label="⚖️ Policy RAG\n(Vector DB)", fillcolor="#FFB6C1"];
                    Web [label="🌐 Web Search\n(Tavily API)", fillcolor="#E0E0E0"];
                }
                
                End [label="💬 최종 답변", shape=oval, fillcolor="#FFD700", style="filled,bold"];

                User -> Router [penwidth=2];
                Router -> DB [label="매출/통계", color="green"];
                Router -> RAG_Manual [label="방법/매뉴얼", color="red"];
                Router -> RAG_Policy [label="규정/계약", color="red"];
                Router -> Web [label="그 외 정보", style="dashed"];
                
                DB -> End;
                RAG_Manual -> End;
                RAG_Policy -> End;
                Web -> End;
            }
        """)

# --------------------------------------------------------------------------
# [UI Component 2] 추천 프롬프트 (Sample Prompts)
# --------------------------------------------------------------------------
def show_sample_prompts():
    """사용자가 참고할 만한 추천 프롬프트를 보여주는 토글"""
    with st.expander("� 질문이 막막하신가요? (추천 프롬프트)", expanded=False):
        tab1, tab2 = st.tabs(["📊 매출 분석", "📘 규정 & 매뉴얼"])
        with tab1:
            st.markdown("""
            - "지난달 **부산 해운대점** 매출 추이 알려줘"
            - "**서울 강남점**과 **강북점**의 커피 판매량 비교해줘"
            - "최근 3개월 동안 **가장 많이 팔린 메뉴 Top 3**는 뭐야?"
            """)
        with tab2:
            st.markdown("""
            - "**매장 오픈 준비**는 어떻게 해야 해? 체크리스트 줘"
            - "**복장 규정** 위반 시 어떤 페널티가 있어?"
            - "**커피머신 고장** 났을 때 긴급 조치 방법 알려줘"
            """)

# --------------------------------------------------------------------------
# [UI Component 3] 최근 검색어 (Real-time Logs)
# --------------------------------------------------------------------------
def show_recent_logs():
    """최근 검색 기록을 보여주는 토글"""
    with st.expander("🕒 최근 다른 점주님들의 검색어 (Real-time Logs)", expanded=False):
        if "messages" in st.session_state:
            recent_prompts = [
                msg["content"] 
                for msg in reversed(st.session_state.messages) 
                if msg["role"] == "user"
            ][:5]
            if recent_prompts:
                for q in recent_prompts:
                    st.text(f"🔍 {q}")
            else:
                st.info("아직 검색 기록이 없습니다.")

# --------------------------------------------------------------------------
# [Logic] AI 메시지 렌더링 함수
# --------------------------------------------------------------------------
def display_ai_message(message_content):
    """
    AI 메시지를 렌더링하는 함수 (JSON 처리 + 시각화)
    """
    try:
        # 1. JSON 파싱 시도
        if isinstance(message_content, str):
            json_data = json.loads(message_content)
        else:
            json_data = message_content
            
        # 2. Key Metrics (숫자 카드) 렌더링
        if "key_metrics" in json_data:
            metrics = json_data["key_metrics"]
            cols = st.columns(3)
            with cols[0]:
                st.metric(label="기간", value=metrics.get("period", "-"))
            with cols[1]:
                st.metric(label="총 매출", value=f"{int(metrics.get('total_sales', 0)):,}원")
            with cols[2]:
                st.metric(label="총 주문", value=f"{int(metrics.get('total_orders', 0)):,}건")
            st.divider()

        # 3. Chart Rendering (그래프)
        if "chart_data" in json_data and json_data["chart_data"]:
            st.caption("📊 " + json_data.get("chart_setup", {}).get("title", "데이터 시각화"))
            df = pd.DataFrame(json_data["chart_data"])
            base = alt.Chart(df).encode(x=alt.X('date', axis=alt.Axis(title='날짜')))
            bar = base.mark_bar(color='#5DADE2').encode(y=alt.Y('sales', axis=alt.Axis(title='매출액(원)')))
            line = base.mark_line(color='#E74C3C').encode(y=alt.Y('orders', axis=alt.Axis(title='주문수(건)')))
            chart = alt.layer(bar, line).resolve_scale(y='independent')
            st.altair_chart(chart, use_container_width=True)

        # 4. 텍스트 내용 렌더링
        if "summary" in json_data:
            st.info(f"💡 요약: {json_data['summary']}")
        if "detail" in json_data:
            st.markdown(json_data['detail'])
        if "action_items" in json_data and json_data["action_items"]:
            st.markdown("### 📋 제안 사항")
            for item in json_data["action_items"]:
                st.markdown(f"- {item}")
        if "sources" in json_data and json_data["sources"]:
            st.caption("📚 참고 자료:")
            for src in json_data["sources"]:
                st.caption(f"- {src}")

    except json.JSONDecodeError:
        st.markdown(message_content)
    except Exception as e:
        st.error(f"렌더링 오류: {e}")
        st.markdown(message_content)

# --------------------------------------------------------------------------
# [Page] 메인 페이지 함수 (여기가 핵심!)
# --------------------------------------------------------------------------
def inquiry_page():
    st.title("🤖 AI 프랜차이즈 매니저 (SOS)")
    st.markdown("매장 운영 중 궁금한 점이나 긴급 상황을 물어보세요. AI가 매뉴얼과 데이터를 분석해 즉시 답변합니다.")

    # [NEW] 포트폴리오용 추가 컴포넌트 3종 세트
    show_langgraph_architecture()
    show_sample_prompts()
    show_recent_logs()
    
    st.divider()

    # 세션 상태 초기화
    if "messages" not in st.session_state:
        st.session_state.messages = []
        st.session_state.messages.append({
            "role": "assistant",
            "content": "안녕하세요 점주님! 무엇을 도와드릴까요?\n\n- 매출 분석\n- 기기 고장/관리\n- 고객 응대/규정", 
            "category": "system"
        })

    # 1. 채팅 기록 표시
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            # 과정 로그 출력
            if "logs" in msg:
                with st.status("✅ 분석 과정 기록", expanded=False, state="complete") as status:
                    for log in msg["logs"]:
                        st.write(f"🔹 {log['message']}")
                        if log.get('details') and log['details'].get('type') == 'web_result':
                            with st.expander("🌐 웹 검색 결과 확인", expanded=True):
                                st.write(log['details']['content'])
            # 최종 답변 출력
            if msg["content"]:
                display_ai_message(msg["content"])

    # 2. 사용자 입력 처리
    if prompt := st.chat_input("질문을 입력하세요..."):
        st.session_state.messages.append({"role": "user", "content": prompt})
        st.chat_message("user").markdown(prompt)
        
        # 3. [Phase 1] 검색 및 진단 요청
        with st.chat_message("assistant"):
            with st.status("🕵️‍♀️ 질문을 분석하고 내부 데이터를 검색 중입니다...", expanded=True) as status:
                try:
                    res = requests.post(f"{API_BASE_URL}/inquiry/check", json={"store_id": 1, "question": prompt})
                    if res.status_code == 200:
                        check_data = res.json()["data"]
                        status.update(label="✅ 검색 완료! 결과를 확인해주세요.", state="complete", expanded=False)
                        st.session_state.pending_inquiry = {"question": prompt, "check_data": check_data}
                        st.rerun()
                    else:
                        status.update(label="❌ 오류 발생", state="error")
                        st.error("서버 오류가 발생했습니다.")
                except Exception as e:
                    status.update(label="❌ 연결 실패", state="error")
                    st.error(f"API 호출 실패: {e}")

    # 4. [Phase 2] 사용자 선택 대기 (검색 결과가 있을 때)
    if "pending_inquiry" in st.session_state:
        pending = st.session_state.pending_inquiry
        data = pending["check_data"]
        question = pending["question"]
        cat = data["category"]
        score = data["similarity_score"]
        top_doc = data.get("top_document")
        
        with st.chat_message("assistant"):
            st.info(f"🤔 **'{cat}'** 관련 질문이군요.")
            
            if cat == "sales":
                st.write("매출 데이터를 분석하여 진단 리포트를 생성합니다.")
                sc1, sc2 = st.columns([2, 1])
                with sc1:
                    if st.button("🚀 분석 시작", type="primary", use_container_width=True):
                        st.session_state.processing_mode = "db"
                        st.session_state.processing_meta = {"question": question, "category": cat, "context": []}
                        del st.session_state.pending_inquiry
                        st.rerun()
                with sc2:
                    if st.button("❌ 종료", use_container_width=True):
                        del st.session_state.pending_inquiry
                        st.rerun()
            else:
                st.markdown(f"**검색된 가장 유사한 문서** (유사도: `{score}%`)")
                if top_doc:
                    with st.expander(f"📄 {top_doc.get('title', '제목 없음')}", expanded=True):
                        st.write(top_doc.get('content', '내용 없음'))
                else:
                    st.warning("관련된 문서를 찾지 못했습니다.")

                col1, col2, col3 = st.columns([2, 2, 1])
                with col1:
                    btn_type = "primary" if score >= 60 else "secondary"
                    if st.button("✅ 이 정보로 답변", type=btn_type, use_container_width=True):
                        st.session_state.processing_mode = "db"
                        st.session_state.processing_meta = {"question": question, "category": cat, "context": data.get("context_data", [])}
                        del st.session_state.pending_inquiry
                        st.rerun()
                with col2:
                    btn_type = "primary" if score < 60 else "secondary"
                    if st.button("🌐 웹 검색", type=btn_type, use_container_width=True):
                        st.session_state.processing_mode = "web"
                        st.session_state.processing_meta = {"question": question, "category": cat, "context": []}
                        del st.session_state.pending_inquiry
                        st.rerun()
                with col3:
                    if st.button("❌ 종료", use_container_width=True):
                        del st.session_state.pending_inquiry
                        st.rerun()

    # 5. [Phase 3] 최종 답변 생성 (선택 완료 후)
    if "processing_mode" in st.session_state:
        mode = st.session_state.processing_mode
        meta = st.session_state.get("processing_meta", {})
        question = meta.get("question", "")
        category = meta.get("category", "manual")
        context = meta.get("context", [])
        
        with st.chat_message("assistant"):
            status_container = st.status(f"🚀 {mode.upper()} 모드로 답변 생성 중...", expanded=True)
            try:
                response = requests.post(
                    f"{API_BASE_URL}/inquiry/generate/stream",
                    json={"store_id": 1, "question": question, "category": category, "mode": mode, "context_data": context},
                    stream=True
                )
                
                final_result = {}
                execution_logs = []
                
                if response.status_code == 200:
                    for line in response.iter_lines():
                        if line:
                            try:
                                decoded = line.decode('utf-8')
                                data = json.loads(decoded)
                                step = data.get("step")
                                msg = data.get("message")
                                details = data.get("details")
                                
                                status_container.write(f"🔹 {msg}")
                                if details and details.get("type") == "web_result":
                                     with status_container.expander("🌐 웹 검색 결과"):
                                         st.write(details.get("content"))
                                
                                execution_logs.append({"step": step, "message": msg, "details": details})
                                if data.get("final_answer"):
                                    final_result["answer"] = data["final_answer"]
                                    final_result["category"] = category
                            except: continue
                            
                    status_container.update(label="✅ 분석 및 답변 생성 완료!", state="complete", expanded=True)
                    
                    if "answer" in final_result:
                        answer = final_result["answer"]
                        display_ai_message(answer)
                        st.session_state.messages.append({
                            "role": "assistant", 
                            "content": answer, 
                            "category": category, 
                            "raw_category": category, 
                            "logs": execution_logs 
                        })
                else:
                    st.error(f"오류: {response.text}")
            except Exception as e:
                st.error(f"실행 오류: {e}")
                
        del st.session_state.processing_mode
        if "processing_meta" in st.session_state: del st.session_state.processing_meta
        st.rerun()

    # 사이드바 팁
    with st.sidebar:
        st.info("💡 **Tip**")
        st.markdown("- 지난달 매출 어때?")
        st.markdown("- 커피 머신 오류")
        st.markdown("- 환불 규정")
        if st.button("🗑️ 대화 초기화"):
            st.session_state.messages = []
            st.rerun()
