import streamlit as st
import pandas as pd
import altair as alt
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
            df_sales['order_date'] = pd.to_datetime(df_sales['order_date']).dt.date

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

            st.altair_chart(bar_chart, use_container_width=True)

            st.divider()

            # 2. 날짜별 상세 내역
            orders_data = get_api(f"/order/store/{store_id}")
            if orders_data:
                df_orders = pd.DataFrame(orders_data)
                df_orders['ordered_at'] = pd.to_datetime(df_orders['ordered_at'])
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

                    st.dataframe(display_df, use_container_width=True,
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
        
        col_btn1, col_btn2 = st.columns([1, 2])
        if col_btn1.button("✨ 새 리포트 생성", key=f"gen_report_{store_id}"):
            with st.spinner("AI가 데이터를 분석 중입니다..."):
                import requests
                from api_utils import API_BASE_URL
                # POST 요청은 api_utils에 아직 없으므로 직접 호출 (나중에 보완 가능)
                resp = requests.post(f"{API_BASE_URL}/report/generate/{store_id}", params={"store_name": store_name})
                if resp.status_code == 200:
                    st.success("새로운 리포트가 생성되었습니다!")
                    st.rerun()
                else:
                    st.error("리포트 생성에 실패했습니다.")

        if report_data:
            st.divider()
            st.info(f"📅 **리포트 생성일:** {report_data['report_date']}")
            
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
