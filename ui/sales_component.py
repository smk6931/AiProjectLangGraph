import streamlit as st
import pandas as pd
import altair as alt
from datetime import date
from api_utils import get_api
# 스타일 임포트
try:
    from styles import show_metric_card
except ImportError:
    from ui.styles import show_metric_card


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
            
            # --- [NEW] 월간 매출 합계 (진실 규명 섹션) ---
            # 선택된 '월(Month)'의 전체 매출을 계산해서 보여줌
            if selected_date:
                sel_year = selected_date.year
                sel_month = selected_date.month
                
                # 해당 월 데이터 필터링
                mask_month = (df_sales['order_date'].astype(str).str.startswith(f"{sel_year}-{sel_month:02d}"))
                df_month = df_sales[mask_month]
                
                month_total_rev = df_month['daily_revenue'].sum() if not df_month.empty else 0
                month_total_orders = df_month['total_orders'].sum() if 'total_orders' in df_month.columns else 0
                
                with col_top1:
                    st.info(f"💰 **{sel_year}년 {sel_month}월 총 매출**: {int(month_total_rev):,}원 (주문 {int(month_total_orders):,}건)")
            # ---------------------------------------------

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
                    show_metric_card(m1, "선택 날짜", str(selected_date))
                    show_metric_card(m2, "총 주문", f"{len(df_day)}건")
                    show_metric_card(m3, "총 매출", f"{int(df_day['total_price'].sum()):,}원")

                    st.dataframe(display_df, width='stretch',
                                 hide_index=True)
                else:
                    st.info(f"{selected_date} 에는 주문 내역이 없습니다.")
        else:
            st.warning("데이터가 없거나 불러올 수 없습니다.")

    with tab2:
        st.write("### 🤖 AI 지점 경영 전략 리포트")
        st.write("지점의 매출과 고객 리뷰를 분석하여 AI 컨설턴트가 최적의 운영 전략을 제안합니다.")

        # 주차별 분석을 위한 날짜 옵션 생성
        # sales_data는 tab1에서 이미 로드됨 (get_api)
        report_target_date = None
        
        if 'df_sales' in locals() and not df_sales.empty:
            max_d = df_sales['order_date'].max() # DB 상 최신 날짜 (예: 12월 30일)
            min_d = df_sales['order_date'].min()
            
            # [Fix] 사용자 요청: 12월 4일부터 31일까지 1주 단위 강제 고정
            # 1주차: 12.04 ~ 12.10
            # 2주차: 12.11 ~ 12.17
            # 3주차: 12.18 ~ 12.24
            # 4주차: 12.25 ~ 12.31
            
            # [Dynamic] 데이터가 존재하는 기간을 기준으로 '월요일~일요일' 주차 자동 생성
            week_options = {}
            default_ix = 0
            
            # 타겟 날짜 (이전 탭에서 선택된 날짜)
            target_obj = selected_date if 'selected_date' in locals() and selected_date else None
            
            # 동적 주차 리스트 생성
            dynamic_weeks = []
            
            from datetime import timedelta
            
            curr_start = min_d
            current_month = curr_start.month
            week_num = 1
            
            # 데이터 끝 날짜까지 루프
            while curr_start <= max_d:
                # 월이 바뀌었는지 체크하여 주차 번호 리셋
                if curr_start.month != current_month:
                    current_month = curr_start.month
                    week_num = 1
                
                # 이번 주 일요일 찾기 (월=0, ... 일=6)
                days_left = 6 - curr_start.weekday()
                curr_end_ideal = curr_start + timedelta(days=days_left)
                
                # 실제 데이터 범위 내에서 끊기 (max_d를 넘어가면 max_d까지만)
                real_end = min(curr_end_ideal, max_d)
                
                # [User Rule] 5주차는 제외하고 1~4주차만 표시
                if week_num <= 4:
                    dynamic_weeks.append((curr_start, real_end, current_month, week_num))
                
                # 다음 루프 준비 (다음주 월요일)
                curr_start = curr_end_ideal + timedelta(days=1)
                week_num += 1

            # 최신 주차가 위로 오도록 역순 정렬하여 옵션 생성
            for i, (s_date, e_date, month, w_num) in enumerate(reversed(dynamic_weeks)):
                label = f"{s_date.year}년 {month}월 {w_num}주차 ({s_date.strftime('%m.%d')} ~ {e_date.strftime('%m.%d')})"
                # 리포트 API에는 해당 주차의 마지막 날짜(데이터 기준)를 전송
                week_options[label] = str(e_date)
                
                # 디폴트 선택 로직 (선택된 날짜가 포함된 주차 자동 선택)
                if target_obj and s_date <= target_obj <= e_date:
                    default_ix = i

            # UI: 주차 선택 박스
            st.markdown("##### 📅 분석 바운더리(기간) 설정")
            
            options_list = list(week_options.keys())
            
            selected_label = st.selectbox(
                "분석할 주차를 선택하세요", 
                options=options_list,
                index=default_ix if default_ix < len(options_list) else 0,
                key=f"report_week_select_{store_id}",
                label_visibility="collapsed"
            )
            report_target_date = week_options[selected_label]
            
        # 최신 리포트 불러오기 (혹은 선택된 날짜의 리포트 조회가 필요하다면 API 수정 필요하지만, 일단 최신 조회 유지)
        # TODO: 리포트 조회 API도 target_date를 받으면 좋음. 지금은 생성만 target_date 지원.
        report_data = get_api(f"/report/latest/{store_id}")

        col_btn1, col_btn2 = st.columns([1, 2])
        if col_btn1.button("✨ 선택 기간 리포트 생성", key=f"gen_report_{store_id}"):
            with st.spinner(f"AI가 {report_target_date} 기준 데이터를 분석 중입니다..."):
                import requests
                from api_utils import API_BASE_URL
                
                params = {
                    "store_name": store_name, 
                    "mode": "sequential",
                    "target_date": report_target_date # [NEW] 선택된 날짜 전달
                }
                
                resp = requests.post(
                    f"{API_BASE_URL}/report/generate/{store_id}", params=params)

                if resp.status_code == 200:
                    result = resp.json()
                    
                    # 캐시/생성 성공 메시지
                    if result.get("cached"):
                        st.info("⚡ 이전에 생성된 리포트가 있어 즉시 불러왔습니다.")
                    else:
                        st.success(f"{report_target_date} 기준 리포트가 생성되었습니다!")
                        st.toast("AI 리포트 생성 완료!", icon="✨")

                    # 실행 로그 보여주기
                    if "logs" in result and result["logs"]:
                        with st.expander("📜 AI 실행 로그 확인", expanded=True):
                            for log in result["logs"]:
                                st.code(log)

                    st.session_state[f"last_logs_{store_id}"] = result.get("logs", [])
                    # 바로 보여주기 위해 변수 업데이트
                    report_data = result.get("report") 
                else:
                    st.error("리포트 생성에 실패했습니다.")

        # [NEW] 리포트 초기화 버튼
        if col_btn2.button("🗑️ 리포트 초기화", key=f"reset_report_{store_id}"):
            import requests
            from api_utils import API_BASE_URL
            try:
                resp = requests.delete(f"{API_BASE_URL}/report/reset/{store_id}")
                if resp.status_code == 200:
                    st.toast("리포트 데이터가 초기화되었습니다.", icon="🗑️")
                    st.rerun() # 새로고침해서 초기화된 상태 반영
                else:
                    st.error("초기화 실패")
            except Exception as e:
                st.error(f"Error: {e}")

        if report_data:
            st.divider()
            
            # report_date는 보통 문자열(YYYY-MM-DD)로 옴
            from datetime import datetime, timedelta
            
            # 출처(Source) 변수 복구
            source = report_data.get("source", "db")
            
            try:
                # [수정] 사용자가 선택한 날짜(report_target_date)를 기준으로 기간 표시
                # report_target_date는 위에서 이미 정의됨 (예: "2025-12-10")
                if report_target_date:
                    end_date = datetime.strptime(report_target_date, "%Y-%m-%d")
                    start_date = end_date - timedelta(days=6)
                    
                    header_text = f"{end_date.year}년 {end_date.month}월 {end_date.day}일 기준 주차 ({start_date.strftime('%m.%d')} ~ {end_date.strftime('%m.%d')})"
                    
                    # 1. 메인 헤더로 기간 표시
                    st.subheader(f"📑 {header_text}")
                else:
                    # 선택된 날짜가 없는 경우(최초 로딩 등) DB 데이터 사용 Fallback
                    st.subheader(f"📑 리포트 정보: {report_data.get('report_date')}")
                
                # 2. 출처 배지 (작게)
                if source == "cache":
                    st.caption(f":blue-background[⚡ CACHE] 데이터 기반 분석")
                else:
                    st.caption(f":gray-background[📁 DATABASE] 데이터 기반 분석")
                    
            except Exception:
                # 날짜 파싱 실패 시 원본 그대로 출력 (header_text 사용 불가)
                 st.subheader(f"📑 리포트 정보: {report_data.get('report_date')}")

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
                
                show_metric_card(m_col1, "총 매출 (7일)", f"{int(total_rev):,}원")
                show_metric_card(m_col2, "매출 변동 추세", f"{trend:+.1f}%", delta=f"{trend:.1f}%")
                show_metric_card(m_col3, "평균 리뷰 평점", f"{rating:.1f} / 5.0")
                
                # --- 신규: 분석에 사용된 로우 데이터(Raw Data) 시각화 ---
                source_data = report_data.get("source_data") or risk_data.get("source_data")
                if source_data and "recent_sales" in source_data:
                    with st.expander("📝 Raw Data Analysis (Source)", expanded=False):
                        st.write("AI가 분석의 근거로 활용한 세부 데이터를 확인하세요.")
                        
                        t1, t2 = st.tabs(["📊 매출/날씨 통합", "🍔 메뉴별 분석"])
                        
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
                # --------------------------------------------------

                if evidence:
                    with st.expander("🧐 AI가 분석한 세부 근거 보기"):
                        # [FIX] 마크다운 테이블/헤더가 깨지지 않도록 줄바꿈 추가
                        st.markdown(f"**매출 분석:**\n\n{evidence.get('sales_analysis')}")

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
