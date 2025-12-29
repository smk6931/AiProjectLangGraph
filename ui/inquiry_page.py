import streamlit as st
import asyncio
import time

# [임시] 백엔드 연동 전 가짜 응답 함수
async def get_ai_response(query_text: str):
    await asyncio.sleep(1) # 생각하는 척 대기
    return f"✅ AI 분석 결과: '{query_text}'에 대한 답변입니다.\n(현재 UI 테스트 모드입니다)"

def show_langgraph_architecture():
    """LangGraph 아키텍처 다이어그램을 표시하는 함수"""
    with st.expander("🧠 AI Agent 아키텍처 (LangGraph 구조도)", expanded=False):
        st.markdown("""
        **이 AI Agent는 사용자의 의도를 파악하여 최적의 경로로 라우팅합니다.**
        """)
        
        # Graphviz로 흐름도 그리기
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

def simulate_ai_reasoning(query_text):
    """AI의 사고 과정을 시각적으로 보여주는 시뮬레이션 함수"""
    
    with st.status("🕵️‍♂️ AI가 답변을 생성하고 있습니다...", expanded=True) as status:
        
        # Step 1: 의도 파악
        st.write("🤔 질문 의도를 분석 중입니다... (Router)")
        time.sleep(0.7) 
        
        tool_icon = "🤖"
        tool_name = "General Chat"
        
        # (연출) 질문에 따라 경로가 바뀌는 척 보여주기
        if any(k in query_text for k in ["매출", "얼마", "판매", "실적", "순위", "가장 많이"]):
            st.write("✅ 분류: **매출/데이터 분석 (Sales Analysis)**")
            time.sleep(0.5)
            st.write("🔌 도구 연결: **AWS RDS (PostgreSQL)**")
            st.write("🔍 SQL Query 생성 및 실행 중...")
            tool_icon = "📊"
            tool_name = "Sales DB Agent"
            
        elif any(k in query_text for k in ["규정", "정책", "계약", "복장", "시간"]):
            st.write("✅ 분류: **사내 규정 (Company Policy)**")
            time.sleep(0.5)
            st.write("🔌 도구 연결: **Vector DB (Embeddings)**")
            st.write("� 관련 문서 검색 중 (Similarity Search)...")
            tool_icon = "⚖️"
            tool_name = "Policy RAG Agent"
            
        elif any(k in query_text for k in ["방법", "어떻게", "매뉴얼", "레시피", "만드는"]):
            st.write("✅ 분류: **운영 매뉴얼 (Operations Manual)**")
            time.sleep(0.5)
            st.write("🔌 도구 연결: **Vector DB (Embeddings)**")
            st.write("🔍 매뉴얼 검색 중...")
            tool_icon = "📘"
            tool_name = "Manual RAG Agent"
            
        elif any(k in query_text for k in ["검색", "찾아줘", "알려줘", "누구"]):
            st.write("⚠️ 사내 데이터 매칭 실패")
            time.sleep(0.5)
            st.write("✅ Fallback: **웹 검색 (Web Search)**")
            st.write("🔌 도구 연결: **Tavily Search API**")
            tool_icon = "🌐"
            tool_name = "Web Search Agent"
        
        else:
            st.write("✅ 분류: **일반 대화 (General Conversation)**")
            st.write("🧠 LLM이 직접 답변을 생성합니다.")

        time.sleep(0.5)
        
        # 상태창 업데이트 (완료)
        status.update(
            label=f"🚀 {tool_icon} {tool_name}가 답변을 완성했습니다!", 
            state="complete", 
            expanded=False # 다 끝나면 접기
        )

def inquiry_page():
    st.title("🤖 AI 프랜차이즈 매니저 (SOS)")
    st.markdown("매장 운영 중 궁금한 점이나 긴급 상황을 물어보세요. AI가 매뉴얼과 데이터를 분석해 즉시 답변합니다.")

    # [포트폴리오용] 아키텍처 보여주기
    show_langgraph_architecture()
    
    st.divider()

    # 세션 상태 초기화
    if "messages" not in st.session_state:
        st.session_state.messages = [
            {"role": "assistant", "content": "안녕하세요 점주님! 무엇을 도와드릴까요?\n\n- 매출 분석\n- 기기 고장/관리\n- 고객 응대/규정"}
        ]

    # 기존 메시지 출력
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    # 사용자 입력 처리
    if prompt := st.chat_input("질문을 입력하세요..."):
        # 사용자 메시지 저장 및 출력
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        # AI 응답 처리
        with st.chat_message("assistant"):
            # [포트폴리오용] AI 사고 과정 시뮬레이션 (UI 연출)
            simulate_ai_reasoning(prompt)
            
            # 실제 응답을 담을 공간
            response_placeholder = st.empty()
            full_response = ""
            
            try:
                # 비동기 함수 실행
                response = asyncio.run(get_ai_response(prompt))
                
                # 스트리밍 효과 (타자 치는 듯한 연출)
                for chunk in response.split():
                    full_response += chunk + " "
                    time.sleep(0.05)
                    response_placeholder.markdown(full_response + "▌")
                
                response_placeholder.markdown(full_response)
                
            except Exception as e:
                error_msg = f"죄송합니다. 오류가 발생했습니다: {str(e)}"
                response_placeholder.error(error_msg)
                full_response = error_msg

            # 응답 저장
            st.session_state.messages.append({"role": "assistant", "content": full_response})
