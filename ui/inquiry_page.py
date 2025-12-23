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
        raw_badge = category.upper() # 예: SALES
        
        with head_col1:
            if summary:
                st.info(f"📢 {summary}")
        with head_col2:
             st.caption(f"🏷️ 분류: {raw_badge}")

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
            tab1, tab2 = st.tabs(["📈 매출 추이", "📄 상세 데이터"])
            
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
            # AI 답변인 경우 커스텀 렌더링 함수 사용
            if msg["role"] == "assistant" and msg.get("category") != "system":
                # 여기서는 raw_category를 넘겨서 뱃지까지 내부에서 처리
                display_answer(msg.get("raw_category", "general"), msg["content"])
            else:
                st.markdown(msg["content"])

    # 2. 사용자 입력 처리
    if prompt := st.chat_input("질문을 입력하세요... (예: 지난달 매출 어때?, 라떼 거품이 안 나요)"):
        # 사용자 메시지 표시 & 저장
        with st.chat_message("user"):
            st.markdown(prompt)
        st.session_state.messages.append({"role": "user", "content": prompt})

        # 3. AI 응답 처리 (API 호출)
        with st.chat_message("assistant"):
            message_placeholder = st.empty()
            message_placeholder.markdown("🔍 AI가 매뉴얼과 데이터를 검색 중입니다...")
            
            try:
                # API 호출 (임시 store_id=1)
                store_id = 1 
                
                response = requests.post(f"{API_BASE_URL}/inquiry/ask", json={
                    "store_id": store_id,
                    "question": prompt
                })
                
                if response.status_code == 200:
                    result = response.json()["data"]
                    answer = result["answer"]
                    category = result["category"]
                    
                    # 기존 placeholder 지우고 새로 렌더링
                    message_placeholder.empty()
                    
                    # 렌더링 함수 호출
                    display_answer(category, answer)
                    
                    # 기록에 저장
                    st.session_state.messages.append({
                        "role": "assistant", 
                        "content": answer, 
                        "category": category,
                        "raw_category": category 
                    })
                else:
                    error_msg = f"오류 발생: {response.text}"
                    message_placeholder.error(error_msg)
                    
            except Exception as e:
                message_placeholder.error(f"연결 오류: {str(e)}")

    # 사이드바 팁
    with st.sidebar:
        st.info("💡 **Tip**")
        st.markdown("- 지난달 매출 어때?")
        st.markdown("- 커피 머신 오류")
        st.markdown("- 환불 규정")
        
        if st.button("🗑️ 대화 초기화"):
            st.session_state.messages = []
            st.rerun()
