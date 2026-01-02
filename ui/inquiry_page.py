import streamlit as st
import requests
import json
import pandas as pd
import altair as alt
import os

# 스타일 파일 임포트 (Root 실행 기준)
try:
    from ui.styles import apply_custom_styles, show_metric_card
except ImportError:
    # 혹시 모를 경로 에러 대비 (같은 폴더)
    from styles import apply_custom_styles, show_metric_card

# API URL 설정
API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8080")

# ==============================================================================
# [UI Component 1] LangGraph 아키텍처 다이어그램 (Expander)
# ==============================================================================
def show_langgraph_architecture():
    with st.expander("AI Agent 아키텍처 (Processing Flow)", expanded=False):
        st.markdown("""
        <div style="text-align: center; color: #8B949E; margin-bottom: 10px;">
            User Intent Analysis ➔ Route Optimization ➔ Specialized Retrieval ➔ Synthesis
        </div>
        """, unsafe_allow_html=True)

# ... (중략) ...

# ==============================================================================
# [UI Component 2] 추천 프롬프트 & 로그
# ==============================================================================
def show_sample_prompts():
    """추천 프롬프트 섹션"""
    with st.expander("추천 질문 (Click to Copy)", expanded=False):
        c1, c2 = st.columns(2)
        with c1:
            st.caption("매출 분석")
            st.code('서울강남점의 최근 매출 하락 원인을 메뉴별로 분석해줘', language=None)
            st.code('최근 1주일간 가장 잘팔린 메뉴 Top 5와 그 이유를 리뷰 기반으로 알려줘', language=None)
            st.code('부산점과 서울점의 매출과 리뷰를 비교해서 개선점을 제안해줘', language=None)
        with c2:
            st.caption("매뉴얼 & 규정")
            st.code('고객이 환불을 요구할 때 규정과 응대 멘트 알려줘', language=None)
            st.code('오픈 조와 마감 조가 해야 할 필수 체크리스트는?', language=None)
            # st.code('매장 위생 점검 항목 리스트와 준비물 요약해줘', language=None)
            # st.code('신규 아르바이트생 교육 시 강조해야 할 복장 규정은?', language=None)
            st.code('서울 종로구의 짜장면 맛집 추천해줘 (웹 검색)', language=None)

def show_recent_logs():
    """최근 검색어 섹션"""
    with st.expander("최근 검색 기록 (Recent Activity)", expanded=False):
        if "messages" in st.session_state and len(st.session_state.messages) > 1:
            recent = [m["content"] for m in reversed(st.session_state.messages) if m["role"]=="user"][:5]
            for r in recent: st.text(f"🔍 {r}")
        else:
            st.info("No recent activity.")

# ==============================================================================
# [Logic] AI 메시지 렌더링 (Custom CSS 적용)
# ==============================================================================
def display_ai_message(message_content):
    """
    AI 응답을 파싱하여 카드형 UI, 차트 등으로 렌더링
    """
    json_data = None
    
    # 1. Parsing 시도
    try:
        if isinstance(message_content, dict):
            json_data = message_content
        elif isinstance(message_content, str):
            # 혹시 마크다운 코드 블록(```json ... ```)으로 감싸져 있을 경우 제거
            clean_content = message_content.strip()
            if clean_content.startswith("```json"):
                clean_content = clean_content[7:]
            if clean_content.endswith("```"):
                clean_content = clean_content[:-3]
            
            json_data = json.loads(clean_content)
    except json.JSONDecodeError:
        # JSON이 아닌 일반 텍스트 메시지 (단순 출력)
        st.markdown(message_content)
        return
    except Exception as e:
        st.error(f"Error parsing response: {e}")
        st.code(message_content)
        return

    # 2. 렌더링 로직 (파싱 성공 시)
    try:
        if not json_data:
            st.markdown(str(message_content))
            return

        # (1) Key Metrics (카드 UI)
        if "key_metrics" in json_data and json_data["key_metrics"]:
            metrics = json_data["key_metrics"]
            # 리스트형 처리
            if isinstance(metrics, dict):
                 m_list = [{"label": k, "value": v} for k, v in metrics.items()]
            else:
                 m_list = metrics
            
            if m_list:
                cols = st.columns(len(m_list[:3]))
                for i, m in enumerate(m_list[:3]):
                    show_metric_card(
                        cols[i], 
                        label=str(m.get("label") or m.get("title", "Metric")), 
                        value=str(m.get("value")), 
                        delta=str(m.get("delta")) if m.get("delta") else None
                    )
                st.markdown("---")

        # (2) Chart Rendering
        if "chart_data" in json_data and json_data["chart_data"]:
            title = json_data.get("chart_setup", {}).get("title", "데이터 시각화")
            st.markdown(f"#### 📊 {title}")
            
            c_data = json_data["chart_data"]
            if isinstance(c_data, list) and len(c_data) > 0:
                df = pd.DataFrame(c_data)
                
                # Chart Setup 정보 활용
                c_setup = json_data.get("chart_setup", {})
                x_col = c_setup.get("x", "date") # 기본값 date
                y_col = c_setup.get("y", "sales") # 기본값 sales
                
                # 컬럼이 실제 데이터에 있는지 확인 (없으면 첫번째, 두번째 컬럼 사용)
                if x_col not in df.columns: x_col = df.columns[0]
                if y_col not in df.columns and len(df.columns) > 1: y_col = df.columns[1]

                # Altair Chart
                chart = alt.Chart(df).mark_bar(cornerRadiusTopLeft=5, cornerRadiusTopRight=5).encode(
                    x=alt.X(f'{x_col}:O', title=x_col.upper(), axis=alt.Axis(labelAngle=0)),
                    y=alt.Y(f'{y_col}:Q', title=y_col.upper()),
                    tooltip=[x_col, y_col],
                    color=alt.value("#4facfe")
                ).properties(height=300)
                st.altair_chart(chart, use_container_width=True)

        # (3) Text Content
        if "answer" in json_data:
            st.markdown(json_data['answer'])
        elif "summary" in json_data:
            st.info(f"💡 **Insight**: {json_data['summary']}")
            
        # (4) References
        if "used_docs" in json_data and json_data["used_docs"]:
             with st.expander("📚 Referenced Sources (참고 자료)"):
                 for d in json_data["used_docs"]:
                     if "http" in d:
                         # URL Link Parsing
                         parts = d.split("http")
                         text_title = parts[0].strip(" -[]")
                         url = "http" + parts[1].split()[0].rstrip(")")
                         
                         title = text_title if text_title else "External Link"
                         st.markdown(f"- 🔗 [{title}]({url})")
                     else:
                         st.markdown(f"- {d}")

        if "used_reviews" in json_data:
             revs = json_data["used_reviews"]
             if revs:
                 with st.expander(f"💬 고객 리뷰 근거 ({len(revs)}건)"):
                      for r in revs[:5]:
                          st.caption(f"{r.get('ordered_at', '')[:10]} | {r.get('menu_name', '')}")
                          st.markdown(f"**{'⭐'*int(r.get('rating',0))}**: {r.get('review_text')}")
                          st.divider()

    except Exception as e:
        st.error(f"Render Error: {e}")
        st.write(json_data)
            
# ... (중략) ...

# ==============================================================================
# [Page] 메인 페이지 엔트리포인트
# ==============================================================================
def inquiry_page():
    # 1. Custom CSS 적용
    apply_custom_styles()
    
    # 2. Header Area
    st.markdown("<h1>AI Franchise Manager</h1>", unsafe_allow_html=True)
    st.caption("LLM & LangGraph 기반 지능형 매장 운영 지원 시스템")
    
    # 3. Top Components
    show_langgraph_architecture()
    show_sample_prompts()
    show_recent_logs()
    
    st.divider()

    # 4. Session Init
    if "messages" not in st.session_state:
        st.session_state.messages = [{
            "role": "assistant", 
            "content": "안녕하세요! 점주님, 무엇을 도와드릴까요?\n\n데이터 분석, 매장 규정, 고객 응대 등 궁금한 점을 편하게 물어보세요."
        }]

    # 5. Chat History Render
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            if "logs" in msg:
                # 상태 메시지를 작고 깔끔하게
                with st.status("✅ Analysis Process", expanded=False, state="complete") as s:
                    for l in msg["logs"]: 
                         st.write(f"🔹 {l['message']}")
            if msg["content"]:
                display_ai_message(msg["content"])

    # 6. User Input
    if prompt := st.chat_input("질문을 입력하세요..."):
        st.session_state.messages.append({"role": "user", "content": prompt})
        st.chat_message("user").markdown(prompt)
        
        # --- [Phase 1: Check] ---
        with st.chat_message("assistant"):
            with st.status("🕵️ Analyzing your inquiry...", expanded=True) as status:
                try:
                    res = requests.post(f"{API_BASE_URL}/inquiry/check", json={"store_id": 1, "question": prompt})
                    if res.status_code == 200:
                        data = res.json()["data"]
                        status.update(label="Analysis Complete. Please select an action.", state="complete", expanded=False)
                        st.session_state.pending_inquiry = {"question": prompt, "data": data}
                        st.rerun()
                    else:
                        status.update(label="Server Error", state="error")
                except Exception as e:
                    status.update(label=f"Connection Error: {e}", state="error")

    # 7. [Phase 2: Action Selection]
    if "pending_inquiry" in st.session_state:
        pending = st.session_state.pending_inquiry
        # data 변수 제거하고 직접 접근
        category = pending["data"].get("category", "general")
        question = pending["question"]
        
        with st.chat_message("assistant"):
            # 깔끔한 Action Card
            st.markdown(f"""
            <div style="background-color: #1F242C; border: 1px solid #4facfe; border-radius: 8px; padding: 15px; margin-bottom: 10px;">
                <h3 style="margin:0; color: #4facfe;">🚀 {category.upper()} Analysis</h3>
                <p style="color: #8B949E; margin-top: 5px;">질문의 의도를 파악하고 관련 데이터를 조회했습니다.</p>
            </div>
            """, unsafe_allow_html=True)
            
            if category == "sales":
                # [분석 정보 미리보기] 직접 접근 방식 사용
                if pending["data"].get("sales_data"):
                    st.info(f"""
                    **📋 분석 계획 (Execution Plan)**
                    - **Target Store**: {pending["data"]["sales_data"].get("target_store_name") or "전체 지점"}
                    - **Data Sources**: Sales(매출), Reviews(리뷰), Menus(메뉴)
                    - **Analysis Type**: Trend & Performance
                    """)
                else:
                    st.write("매출 데이터를 심층 분석하여 리포트를 생성합니다.")
                c1, c2 = st.columns([1, 1])
                if c1.button("분석 시작", type="primary", use_container_width=True):
                    st.session_state.processing_mode = "db"
                    st.session_state.processing_meta = {"question": question, "category": category, "context": []}
                    del st.session_state.pending_inquiry
                    st.rerun()
                if c2.button("취소", use_container_width=True):
                    del st.session_state.pending_inquiry
                    st.rerun()
            else: # Manual / Policy
                candidates = pending["data"].get("candidates", [])
                st.write(f"🔍 **{len(candidates)}**건의 관련 문서를 찾았습니다.")
                
                # [AI Recommendation]
                recommendation = pending["data"].get("recommendation", {})
                if recommendation and recommendation.get("comment"):
                    rec_msg = recommendation["comment"]
                    if "웹 검색" in rec_msg or "낮습니다" in rec_msg:
                        st.warning(f"{rec_msg}")
                    else:
                        st.success(f"{rec_msg}")
                
                selected_docs = []
                if candidates:
                    st.markdown("---")
                    st.caption("참고할 문서를 선택하세요 (체크박스):")
                    
                    for c in candidates:
                        # 파싱: [제목] (유사도: 0.xx) 형태라고 가정
                        first_line = c.split('\n')[0]
                        # 제목과 상세 내용 분리
                        title = first_line
                        score_text = ""
                        
                        if "(유사도:" in first_line:
                            parts = first_line.split("(유사도:")
                            title = parts[0].strip()
                            score_text = f"(유사도: {parts[1].replace(')', '').strip()})"
                        
                        # 카드 스타일 배경
                        col_chk, col_txt = st.columns([0.1, 0.9])
                        with col_chk:
                             # Default True
                             is_checked = st.checkbox("Select", value=True, key=c[:20], label_visibility="collapsed")
                        
                        with col_txt:
                             # Custom Style
                             st.markdown(f"""
                             <div style="
                                 background-color: #161B22; 
                                 padding: 10px; 
                                 border-radius: 8px; 
                                 border: 1px solid #30363D; 
                                 display: flex; 
                                 justify-content: space-between; 
                                 align-items: center;
                                 margin-bottom: 5px;">
                                 <span style="font-weight: bold; color: #E6EDF3;">📄 {title}</span>
                                 <span style="font-size: 0.8em; color: #4facfe; background-color: rgba(79, 172, 254, 0.1); padding: 2px 8px; border-radius: 12px;">
                                     {score_text}
                                 </span>
                             </div>
                             """, unsafe_allow_html=True)
                             # 상세 내용 (옵션: 너무 길면 생략하거나 expander로)
                             # with st.expander("내용 미리보기"):
                             #    st.text(c)
                        
                        if is_checked:
                             selected_docs.append(c)
                    
                    st.markdown("---")
                
                c1, c2 = st.columns([1, 1])
                if c1.button("답변 생성", type="primary", use_container_width=True):
                    st.session_state.processing_mode = "db"
                    st.session_state.processing_meta = {"question": question, "category": category, "context": selected_docs}
                    del st.session_state.pending_inquiry
                    st.rerun()
                if c2.button("웹 검색 (Google)", use_container_width=True):
                    st.session_state.processing_mode = "web"
                    st.session_state.processing_meta = {"question": question, "category": category, "context": []}
                    del st.session_state.pending_inquiry
                    st.rerun()

    # 8. [Phase 3: Generation]
    if "processing_mode" in st.session_state:
        meta = st.session_state.processing_meta
        
        with st.chat_message("assistant"):
            st_status = st.status("Generating Response...", expanded=True)
            full_resp = ""
            logs = []
            
            try:
                # 스트리밍 요청
                res = requests.post(f"{API_BASE_URL}/inquiry/generate/stream", json={
                    "store_id": 1,
                    "question": meta["question"],
                    "category": meta["category"],
                    "mode": st.session_state.processing_mode,
                    "context_data": meta["context"]
                }, stream=True)
                
                final_obj = None
                for line in res.iter_lines():
                    if line:
                        try:
                            d = json.loads(line.decode('utf-8'))
                            if "step" in d and d["step"] != "done":
                                msg = d.get("message", "")
                                st_status.write(f"🔹 {msg}")
                                logs.append(d)
                            if "final_answer" in d:
                                final_obj = d["final_answer"]
                        except: continue
                
                st_status.update(label="Complete!", state="complete", expanded=False)
                
                if final_obj:
                    # JSON 직렬화
                    full_resp = json.dumps(final_obj) if isinstance(final_obj, (dict, list)) else final_obj
                    display_ai_message(full_resp)
                    st.session_state.messages.append({
                        "role": "assistant", 
                        "content": full_resp, 
                        "logs": logs
                    })
                else:
                    st.error("Failed to generate answer.")
            except Exception as e:
                st.error(f"Error: {e}")
        
        del st.session_state.processing_mode
        del st.session_state.processing_meta
        st.rerun()

    # Sidebar
    with st.sidebar:
        st.caption("Developed with LangGraph")
        if st.button("Reset Conversation", use_container_width=True):
            st.session_state.messages = []
            st.rerun()
