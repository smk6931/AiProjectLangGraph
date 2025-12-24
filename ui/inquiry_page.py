import streamlit as st
import requests
import json
import pandas as pd
import altair as alt

API_BASE_URL = "http://localhost:8080"

def display_answer(category, answer_text):
    """
    카테고리와 답변 텍스트(JSON)를 받아서
    맞춤형 UI로 렌더링하는 함수
    """
    try:
        data = json.loads(answer_text)
    except json.JSONDecodeError:
        st.markdown(answer_text)
        return

    # 응답 타입 확인 (없으면 기존 방식이나 카테고리로 추측)
    res_type = data.get("type", category)

    # 1. 📊 매출 관련 UI
    if res_type == "sales" or category == "sales":
        # 상단: 요약 멘트 & 분류 뱃지 (컬럼 분리)
        head_col1, head_col2 = st.columns([3, 1])
        
        summary = data.get("summary", data.get("매출_분석", ""))
        store_name = data.get("store_name", "") # 지점명 가져오기
        raw_badge = category.upper()
        
        with head_col1:
            if summary:
                st.info(f"📢 {summary}")
        with head_col2:
             badge_text = f"📍 {store_name}\n({raw_badge})" if store_name else f"🏷️ {raw_badge}"
             st.caption(badge_text)

        # 데이터 처리
        raw_data = data.get("data", data.get("최근_매출_데이터", []))
        
        if raw_data:
            df = pd.DataFrame(raw_data)
            
            # 컬럼명 통일 (한글/영문 대응)
            df.rename(columns={"날짜": "date", "매출": "sales", "주문_수": "orders"}, inplace=True)
            
            # 읽기 좋게 날짜 정렬
            if "date" in df.columns:
                df["date"] = pd.to_datetime(df["date"])
                df = df.sort_values("date")
            
            # 데이터 타입 변환
            if "sales" in df.columns: df["sales"] = pd.to_numeric(df["sales"])
            if "orders" in df.columns: df["orders"] = pd.to_numeric(df["orders"])
            
            # 메트릭 표시
            col1, col2 = st.columns(2)
            with col1:
                total_sales = df["sales"].sum() if "sales" in df.columns else 0
                st.metric("기간 총 매출", f"{total_sales:,.0f}원")
            with col2:
                total_orders = df["orders"].sum() if "orders" in df.columns else 0
                st.metric("기간 총 주문 수", f"{total_orders:,}건")

            # 탭으로 차트와 표 분리
            chart_tab_label = f"📈 {store_name} 매출 추이" if store_name else "📈 매출 추이"
            tab1, tab2 = st.tabs([chart_tab_label, "📄 상세 데이터"])
            
            with tab1:
                if "date" in df.columns and "sales" in df.columns:
                    # Altair 차트: 날짜 가로 정렬 (labelAngle=0)
                    chart = alt.Chart(df).mark_line(point=True).encode(
                        x=alt.X('date', title='날짜', axis=alt.Axis(format='%m-%d', labelAngle=0)), 
                        y=alt.Y('sales', title='매출(원)'),
                        tooltip=['date', 'sales', 'orders']
                    ).interactive()
                    st.altair_chart(chart, use_container_width=True)
                else:
                    st.warning("차트를 그리기 위한 데이터가 부족합니다.")
            
            with tab2:
                # 날짜를 다시 문자열로 (보기 좋게)
                display_df = df.copy()
                if "date" in display_df.columns:
                    display_df["date"] = display_df["date"].dt.strftime('%Y-%m-%d')
                st.dataframe(display_df, use_container_width=True)

    # 2. 📝 일반 답변 (매뉴얼/규정)
    else:
        # 상단: 제목 & 분류 뱃지
        title = data.get("title", "")
        head_col1, head_col2 = st.columns([3, 1])
        
        with head_col1:
            if title:
                st.subheader(f"📌 {title}")
        with head_col2:
            st.caption(f"🏷️ 분류: {category.upper()}")

        content = data.get("content", data.get("answer", ""))
        
        # Markdown 렌더링
        clean_content = str(content).replace("\\n", "\n")
        st.markdown(clean_content)


def inquiry_page():
    st.title("🤖 AI 프랜차이즈 매니저 (SOS)")
    st.markdown("매장 운영 중 궁금한 점이나 긴급 상황을 물어보세요. AI가 매뉴얼과 데이터를 분석해 즉시 답변합니다.")

    # 세션 상태에 채팅 기록 저장소 초기화
    if "messages" not in st.session_state:
        st.session_state.messages = []
        
        # 첫 인사 메시지
        st.session_state.messages.append({
            "role": "assistant",
            "content": "안녕하세요 점주님! 무엇을 도와드릴까요?\n- 매출 분석\n- 기기 고장/관리\n- 고객 응대/규정", 
            "category": "system"
        })

    # 1. 채팅 기록 표시
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            # (1) 과정 로그 출력 (저장된 기록이 있을 경우)
            if "logs" in msg:
                # 과거 기록은 기본적으로 접어두기 (expanded=False) -> 요청에 따라 True로 변경
                with st.status("✅ 분석 과정 기록", expanded=True, state="complete") as status:
                    for log in msg["logs"]:
                        st.write(f"🔹 {log['message']}")
                        # 웹 검색 결과 상세 표시
                        if log.get('details') and log['details'].get('type') == 'web_result':
                            with st.expander("🌐 웹 검색 결과 확인", expanded=True): # 검색 결과도 항상 펼쳐 보이게
                                st.write(log['details']['content'])

            # (2) 최종 AI 답변 출력
            # (2) 최종 AI 답변 출력
            if msg["content"]:
                try:
                    import json
                    # JSON 파싱 시도
                    data = json.loads(msg["content"])
                    
                    # 1. 요약 (Highlight)
                    if data.get("summary"):
                        st.info(f"**요약**: {data['summary']}", icon="💡")
                    
                    # 2. 상세 내용
                    if data.get("detail"):
                        st.markdown(data["detail"])
                        
                    # 3. Action Items (체크리스트 스타일)
                    if data.get("action_items") and isinstance(data["action_items"], list):
                        st.divider()
                        st.subheader("✅ 제안하는 조치사항")
                        for item in data["action_items"]:
                            st.markdown(f"- {item}")
                            
                    # 4. 출처
                    if data.get("sources") and isinstance(data["sources"], list):
                        st.caption("📚 참고 자료:")
                        for src in data["sources"]:
                            st.caption(f"- {src}")

                    # 5. 데이터 시각화 (그래프)
                    if data.get("type") == "sales" and data.get("data"):
                        st.markdown("---")
                        st.subheader("📊 매출 트렌드")
                        try:
                            import pandas as pd
                            df = pd.DataFrame(data["data"])
                            # 컬럼명 유연하게 찾기 (date, sales 포함된 컬럼)
                            date_col = next((c for c in df.columns if 'date' in c), None)
                            sales_col = next((c for c in df.columns if 'sales' in c), None)
                            
                            if date_col and sales_col:
                                df[date_col] = pd.to_datetime(df[date_col])
                                # 차트 그리기
                                st.line_chart(df.set_index(date_col)[sales_col])
                            else:
                                st.dataframe(df)
                        except Exception as e:
                            st.caption(f"데이터 시각화 오류: {e}")

                except (json.JSONDecodeError, TypeError):
                    # JSON 형식이 아니거나 파싱 실패 시 기존 방식(일반 텍스트) 사용
                    if msg["role"] == "assistant" and msg.get("category") != "system":
                         display_answer(msg.get("raw_category", "general"), msg["content"])
                    else:
                         st.markdown(msg["content"])

    # 2. 사용자 입력 처리
    if prompt := st.chat_input("질문을 입력하세요..."):
        # 사용자 메시지 저장
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
                        
                        # 검사 결과 세션에 저장 (다음 인터랙션을 위해)
                        st.session_state.pending_inquiry = {
                            "question": prompt,
                            "check_data": check_data
                        }
                        st.rerun() # UI 갱신을 위해 리런
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
        
        # 메시지 컨테이너 생성
        with st.chat_message("assistant"):
            st.info(f"🤔 **'{cat}'** 관련 질문이군요.")
            
            # 매출 카테고리는 바로 진행 (유사도 검사 불필요)
            if cat == "sales":
                st.write("매출 데이터를 분석하여 진단 리포트를 생성합니다.")
                
                sc1, sc2 = st.columns([2, 1])
                with sc1:
                    if st.button("🚀 분석 시작", type="primary", use_container_width=True):
                        st.session_state.processing_mode = "db" # 매출은 무조건 db/algo
                        st.session_state.processing_meta = {
                            "question": question,
                            "category": cat,
                            "context": []
                        }
                        del st.session_state.pending_inquiry # 대기 상태 해제
                        st.rerun()
                with sc2:
                    if st.button("❌ 종료", use_container_width=True):
                        del st.session_state.pending_inquiry
                        st.rerun()
                        
            else:
                # 매뉴얼/정책: 유사도 결과 보여주기
                st.markdown(f"**검색된 가장 유사한 문서** (유사도: `{score}%`)")
                
                if top_doc:
                    with st.expander(f"📄 {top_doc.get('title', '제목 없음')}", expanded=True):
                        st.write(top_doc.get('content', '내용 없음'))
                else:
                    st.warning("관련된 문서를 찾지 못했습니다.")

                col1, col2, col3 = st.columns([2, 2, 1])
                
                # 버튼 제공
                with col1:
                    # 유사도가 높으면 Primary, 낮으면 Secondary
                    btn_type = "primary" if score >= 60 else "secondary"
                    if st.button("✅ 이 정보로 답변", type=btn_type, use_container_width=True):
                        st.session_state.processing_mode = "db"
                        st.session_state.processing_meta = {
                            "question": question,
                            "category": cat,
                            "context": data.get("context_data", [])
                        }
                        del st.session_state.pending_inquiry
                        st.rerun()
                        
                with col2:
                    # 유사도가 낮으면 Primary
                    btn_type = "primary" if score < 60 else "secondary"
                    if st.button("🌐 웹 검색", type=btn_type, use_container_width=True):
                        st.session_state.processing_mode = "web"
                        st.session_state.processing_meta = {
                            "question": question,
                            "category": cat,
                            "context": [] # 웹 검색은 컨텍스트 필요 없음
                        }
                        del st.session_state.pending_inquiry
                        st.rerun()
                
                with col3:
                    if st.button("❌ 종료", use_container_width=True):
                        del st.session_state.pending_inquiry
                        st.rerun()

    # 5. [Phase 3] 최종 답변 생성 (선택 완료 후)
    if "processing_mode" in st.session_state:
        mode = st.session_state.processing_mode
        
        # 저장해둔 메타데이터 불러오기
        meta = st.session_state.get("processing_meta", {})
        question = meta.get("question", "")
        category = meta.get("category", "manual")
        context = meta.get("context", [])
        
        with st.chat_message("assistant"):
            # 과정을 보여줄 status 컨테이너
            status_container = st.status(f"🚀 {mode.upper()} 모드로 답변 생성 중...", expanded=True)
            
            try:
                response = requests.post(
                    f"{API_BASE_URL}/inquiry/generate/stream",
                    json={
                        "store_id": 1,
                        "question": question,
                        "category": category,
                        "mode": mode,
                        "context_data": context
                    },
                    stream=True
                )
                
                final_result = {}
                execution_logs = [] # 로그 저장을 위한 리스트 초기화
                
                if response.status_code == 200:
                    for line in response.iter_lines():
                        if line:
                            try:
                                decoded = line.decode('utf-8')
                                data = json.loads(decoded)
                                
                                step = data.get("step")
                                msg = data.get("message")
                                details = data.get("details")
                                
                                # 1. 실시간 UI 업데이트
                                status_container.write(f"🔹 {msg}")
                                if details and details.get("type") == "web_result":
                                     with status_container.expander("🌐 웹 검색 결과"):
                                         st.write(details.get("content"))
                                
                                # 2. 로그 데이터 수집 (히스토리 저장용)
                                execution_logs.append({
                                    "step": step,
                                    "message": msg,
                                    "details": details
                                })
                                
                                if data.get("final_answer"):
                                    final_result["answer"] = data["final_answer"]
                                    final_result["category"] = category
                                    
                            except: continue
                            
                    status_container.update(label="✅ 분석 및 답변 생성 완료!", state="complete", expanded=True)
                    
                    # 결과 출력 및 저장
                    if "answer" in final_result:
                        answer = final_result["answer"]
                        # Structured UI 렌더링 (스트리밍 완료 후)
                        try:
                            import json
                            data = json.loads(answer)
                            
                            # 1. 요약
                            if data.get("summary"):
                                st.info(f"**요약**: {data['summary']}", icon="💡")
                            
                            # 2. 상세 내용
                            if data.get("detail"):
                                st.markdown(data["detail"])
                                
                            # 3. Action Items
                            if data.get("action_items") and isinstance(data["action_items"], list):
                                st.divider()
                                st.subheader("✅ 제안하는 조치사항")
                                for item in data["action_items"]:
                                    st.markdown(f"- {item}")
                                    
                            # 4. 출처
                            if data.get("sources") and isinstance(data["sources"], list):
                                st.caption("📚 참고 자료:")
                                for src in data["sources"]:
                                    st.caption(f"- {src}")

                            # 5. 차트
                            if data.get("type") == "sales" and data.get("data"):
                                st.markdown("---")
                                st.subheader("📊 매출 트렌드")
                                try:
                                    import pandas as pd
                                    df = pd.DataFrame(data["data"])
                                    date_col = next((c for c in df.columns if 'date' in c), None)
                                    sales_col = next((c for c in df.columns if 'sales' in c), None)
                                    if date_col and sales_col:
                                        df[date_col] = pd.to_datetime(df[date_col])
                                        st.line_chart(df.set_index(date_col)[sales_col])
                                    else:
                                        st.dataframe(df)
                                except Exception as e:
                                    st.caption(f"데이터 시각화 오류: {e}")

                        except:
                            # 실패 시 기존 함수 사용
                            display_answer(category, answer)
                        
                        # 세션에 메시지 저장 (로그 포함)
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
                
        # 처리 완료 후 상태 초기화 (UI 리프레시)
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
