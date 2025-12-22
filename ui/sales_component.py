import streamlit as st
import pandas as pd
import altair as alt
from datetime import date
from api_utils import get_api


@st.dialog("📊 지점 매출 상세 현황", width="large")
def show_sales_dialog(store_id, store_name):
    """
    모달(다이얼로그) 창으로 매출 현황을 보여주는 컴포넌트
    """
    st.write(f"### {store_name}")
    st.divider()

    # 상단 탭 구성
    tab1, tab2 = st.tabs(["📊 매출 현황", "🤖 AI 전략 리포트"])

    with tab1:
        # 일별 매출 요약 데이터 가져오기
        sales_data = get_api(f"/order/store/{store_id}/daily_sales")

        if sales_data:
            df_sales = pd.DataFrame(sales_data)
            df_sales['order_date'] = pd.to_datetime(
                df_sales['order_date']).dt.date

            if 'daily_revenue' in df_sales.columns:
                df_sales['daily_revenue'] = pd.to_numeric(
                    df_sales['daily_revenue'])

            # 날짜 선택기를 먼저 정의하여 선택된 날짜 정보를 가져옴 (차트에서 강조하기 위함)
            max_date = df_sales['order_date'].max()
            min_date = df_sales['order_date'].min()

            # 레이아웃 구성
            col_top1, col_top2 = st.columns([2, 1])
            with col_top2:
                st.write("📅 **조회 날짜 선택**")
                selected_date = st.date_input(
                    "날짜 선택",
                    value=max_date,
                    min_value=min_date,
                    max_value=max_date,
                    key=f"modal_date_{store_id}",
                    label_visibility="collapsed"
                )

            # 1. 매출 그래프 (Altair를 사용하여 커스텀)
            st.write("📈 **일별 매출 추이**")

            # 강조 색상 설정을 위한 컬럼 추가
            chart_df = df_sales.copy()
            chart_df['is_selected'] = chart_df['order_date'] == selected_date
            chart_df['order_date_str'] = chart_df['order_date'].astype(str)

            # Altair 차트 생성
            bar_chart = alt.Chart(chart_df).mark_bar().encode(
                x=alt.X('order_date_str:N', title='날짜',
                        axis=alt.Axis(labelAngle=0)),
                y=alt.Y('daily_revenue:Q', title='매출액(원)'),
                color=alt.condition(
                    alt.datum.is_selected,
                    alt.value('#FF4B4B'),  # 선택된 날짜 (빨간색 강조)
                    alt.value('#1f77b4')   # 기본 색상 (파란색)
                ),
                tooltip=[
                    alt.Tooltip('order_date_str:N', title='날짜'),
                    alt.Tooltip('daily_revenue:Q', title='매출액', format=',.0f')
                ]
            ).properties(width='container', height=300)

            st.altair_chart(bar_chart, width='stretch')

            st.divider()

            # 2. 날짜별 상세 내역
            orders_data = get_api(f"/order/store/{store_id}")
            if orders_data:
                df_orders = pd.DataFrame(orders_data)
                df_orders['ordered_at'] = pd.to_datetime(
                    df_orders['ordered_at'])
                mask = (df_orders['ordered_at'].dt.date == selected_date)
                df_day = df_orders[mask]

                if not df_day.empty:
                    st.write(f"🛒 **{selected_date} 주문 목록**")
                    display_df = df_day[['menu_name', 'quantity',
                                        'total_price', 'ordered_at']].copy()
                    display_df['ordered_at'] = display_df['ordered_at'].dt.strftime(
                        '%H:%M')
                    display_df.columns = ['메뉴명', '수량', '금액', '주문시간']

                    m1, m2, m3 = st.columns(3)
                    m1.metric("선택 날짜", str(selected_date))
                    m2.metric("총 주문", f"{len(df_day)}건")
                    m3.metric("총 매출", f"{int(df_day['total_price'].sum()):,}원")

                    st.dataframe(display_df, width='stretch',
                                 hide_index=True)
                else:
                    st.info(f"{selected_date} 에는 주문 내역이 없습니다.")
        else:
            st.warning("데이터가 없거나 불러올 수 없습니다.")

    with tab2:
        st.write("### 🤖 AI 지점 경영 전략 리포트")
        st.write("지점의 매출과 고객 리뷰를 분석하여 AI 컨설턴트가 최적의 운영 전략을 제안합니다.")

        # 최신 리포트 불러오기
        report_data = get_api(f"/report/latest/{store_id}")

        # 모드 선택 UI 추가
        st.write("---")
        gen_mode = st.radio(
            "🚀 생성 모드 선택",
            ["순차적 실행 (Fixed DAG)", "자율 에이전트 (Autonomous Agent)"],
            help="순차적 실행은 정해진 단계(수집->분석->검증)를 따르고, 자율 에이전트는 AI가 스스로 도구를 선택하여 업무를 완수합니다.",
            horizontal=True
        )
        mode_key = "sequential" if "순차적" in gen_mode else "autonomous"

        col_btn1, col_btn2 = st.columns([1, 2])
        if col_btn1.button("✨ 새 리포트 생성", key=f"gen_report_{store_id}"):
            with st.spinner(f"AI가 {gen_mode} 모드로 데이터를 분석 중입니다..."):
                import requests
                from api_utils import API_BASE_URL
                params = {"store_name": store_name, "mode": mode_key}
                resp = requests.post(
                    f"{API_BASE_URL}/report/generate/{store_id}", params=params)

                if resp.status_code == 200:
                    result = resp.json()
                    
                    # 캐시 여부에 따른 메시지 차이화
                    if result.get("cached"):
                        st.info("⚡ 오늘 이미 생성된 리포트가 있어 캐시(Memory)에서 즉시 불러왔습니다.")
                        st.toast("캐시 데이터 로드 완료!", icon="⚡")
                    else:
                        st.success(f"새로운 리포트가 {gen_mode} 모드로 생성되었습니다!")
                        st.toast("AI 리포트 생성 완료!", icon="✨")

                    # 실행 로그 보여주기
                    if "logs" in result and result["logs"]:
                        with st.expander("📜 AI 실행 로그 확인", expanded=not result.get("cached")):
                            for log in result["logs"]:
                                st.code(log)

                    st.session_state[f"last_logs_{store_id}"] = result.get("logs", [])
                    st.rerun()
                else:
                    st.error("리포트 생성에 실패했습니다.")

        if report_data:
            st.divider()
            
            # 출처(Source)에 따른 배지 표시
            source = report_data.get("source", "db")
            if source == "cache":
                st.write(f"✅ **리포트 정보** : {report_data['report_date']} :blue-background[⚡ CACHE (0.1ms)]")
            else:
                st.write(f"✅ **리포트 정보** : {report_data['report_date']} :gray-background[📁 DATABASE]")

            # --- 신규: 데이터 분석 근거 시각화 ---
            # DB에서 불러올 경우 risk_assessment 안에 metrics가 들어있으므로 이를 확인
            risk_data = report_data.get("risk_assessment", {}) or {}
            metrics = report_data.get("metrics") or risk_data.get("metrics")
            evidence = report_data.get("data_evidence") or risk_data.get("data_evidence")

            if metrics:
                st.markdown("#### 📊 데이터 분석 근거")
                m_col1, m_col2, m_col3 = st.columns(3)
                
                total_rev = metrics.get('total_rev', 0)
                trend = metrics.get('trend_percent', 0)
                rating = metrics.get('avg_rating', 0)
                
                m_col1.metric("총 매출 (7일)", f"{int(total_rev):,}원")
                m_col2.metric("매출 변동 추세", f"{trend:+.1f}%", delta=f"{trend:.1f}%")
                m_col3.metric("평균 리뷰 평점", f"{rating:.1f} / 5.0")
                
                # --- 신규: 분석에 사용된 로우 데이터(Raw Data) 시각화 ---
                source_data = report_data.get("source_data") or risk_data.get("source_data")
                if source_data and "recent_sales" in source_data:
                    with st.expander("📝 분석에 사용된 기초 데이터 확인 (메뉴/요인별)", expanded=False):
                        st.write("AI가 분석의 근거로 활용한 세부 데이터를 확인하세요.")
                        
                        t1, t2, t3 = st.tabs(["📊 매출/날씨 통합", "🍔 메뉴별 분석", "📅 요일/시간 분석"])
                        
                        with t1:
                            st.write("**[최근 7일 매출 및 기상 상황]**")
                            df_source_sales = pd.DataFrame(source_data["recent_sales"])
                            
                            # 컬럼명 매핑
                            col_map = {"date": "날짜", "revenue": "매출액(원)", "rev": "매출액(원)", "weather": "날씨"}
                            df_source_sales = df_source_sales.rename(columns=col_map)
                            
                            # 컬럼 순서 정리 (날짜, 날씨, 매출액 순)
                            cols = [c for c in ["날짜", "날씨", "매출액(원)"] if c in df_source_sales.columns]
                            st.dataframe(df_source_sales[cols], hide_index=True, use_container_width=True)

                        with t2:
                            col_m1, col_m2 = st.columns(2)
                            with col_m1:
                                st.write("**🔥 잘 팔리는 메뉴 (Top 5)**")
                                if "top_selling_menus" in source_data:
                                    df_top = pd.DataFrame(source_data["top_selling_menus"])
                                    if not df_top.empty:
                                        st.dataframe(df_top[["menu", "recent_rev", "change_pct"]].rename(columns={"menu":"메뉴","recent_rev":"매출","change_pct":"증감%"}), hide_index=True)
                                    else:
                                        st.write("- 데이터 없음 -")
                            
                            with col_m2:
                                st.write("**📉 급감한 메뉴 (Worst 5)**")
                                if "worst_dropping_menus" in source_data:
                                    df_worst = pd.DataFrame(source_data["worst_dropping_menus"])
                                    if not df_worst.empty:
                                        st.dataframe(df_worst[["menu", "change_pct", "prev_rev"]].rename(columns={"menu":"메뉴","change_pct":"하락%","prev_rev":"이전매출"}), hide_index=True)
                                    else:
                                        st.write("- 데이터 없음 -")

                        with t3:
                            st.write("**[평일 vs 주말 매출 변동]**")
                            if "day_analysis" in source_data:
                                df_day = pd.DataFrame(source_data["day_analysis"])
                                if not df_day.empty:
                                    # 보기 좋게 전처리
                                    df_day = df_day[["type", "recent", "prev", "trend"]]
                                    df_day.columns = ["구분", "최근매출", "이전매출", "변동률(%)"]
                                    st.dataframe(df_day, hide_index=True, use_container_width=True)
                            else:
                                st.info("요일별 분석 데이터가 없습니다.")
                # --------------------------------------------------

                if evidence:
                    with st.expander("🧐 AI가 분석한 세부 근거 보기"):
                        st.write(f"**매출 분석:** {evidence.get('sales_analysis')}")
                        st.write(f"**리뷰 분석:** {evidence.get('review_analysis')}")
            # -------------------------------

            st.markdown("#### 📝 종합 분석 요약")
            st.success(report_data['summary'])

            st.markdown("#### 💡 마케팅 및 프로모션 전략")
            st.write(report_data['marketing_strategy'])

            st.markdown("#### 🛠️ 현장 운영 개선 제안")
            st.write(report_data['operational_improvement'])

            # 위험 요소 시각화
            risk = report_data.get('risk_assessment', {})
            if risk:
                st.markdown("#### ⚠️ 리스크 진단")
                risk_score = risk.get('risk_score', 0)
                st.progress(risk_score / 100, text=f"위험 지수: {risk_score}점")

                cols = st.columns(len(risk.get('main_risks', [])) or 1)
                for i, r_text in enumerate(risk.get('main_risks', [])):
                    cols[i].warning(r_text)

                st.error(f"**긴급 제언:** {risk.get('suggestion', 'N/A')}")
        else:
            st.warning("아직 생성된 리포트가 없습니다. 상단의 버튼을 눌러 AI 리포트를 생성해보세요.")

    if st.button("닫기"):
        st.rerun()
