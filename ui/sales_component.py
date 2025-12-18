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
        # 해당 날짜 주문 가져오기
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

                # 가로로 요약 지표 먼저 표시
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

    if st.button("닫기"):
        st.rerun()
