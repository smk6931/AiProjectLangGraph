# app/ui/dashboard.py
import streamlit as st
import pandas as pd
import pydeck as pdk
import requests
from datetime import datetime

# URL을 localhost로 통일 (포트 8080)
API_BASE_URL = "http://localhost:8080"


def dashboard_page():
    st.title("🚀 Dashboard")
    st.write(f"환영합니다 👋 {st.session_state.get('user_email')}")

    st.divider()
    st.subheader("🗺️ 전국 매장 현황")

    # 1️⃣ API로 매장 데이터 조회
    try:
        response = requests.get(f"{API_BASE_URL}/store/get")
        if response.status_code == 200:
            stores_data = response.json()
        elif response.status_code == 404:
            st.warning("데이터가 없습니다.")
            return
        else:
            st.error(f"데이터 조회 실패: {response.status_code}")
            return
    except Exception as e:
        st.error(f"API 연결 실패: {e} (백엔드 서버가 켜져 있는지 확인하세요)")
        return

    if not stores_data:
        st.warning("데이터가 없습니다.")
        return

    # DataFrame 변환
    stores = pd.DataFrame(stores_data)

    # 2️⃣ 지도 레이어
    layer = pdk.Layer(
        "ScatterplotLayer",
        data=stores,
        get_position="[lon, lat]",
        get_radius=6000,
        get_fill_color=[255, 80, 80],
        pickable=True,
    )

    view_state = pdk.ViewState(
        latitude=36.5,
        longitude=127.8,
        zoom=6,
        pitch=0,
    )

    st.pydeck_chart(
        pdk.Deck(
            layers=[layer],
            initial_view_state=view_state,
            tooltip={
                "text": "{store_name}\n{city}"
            },
        )
    )

    # 3️⃣ 매장 선택 UI
    st.subheader("🏪 매장 선택")
    selected_store = st.selectbox(
        "매장을 선택하세요",
        stores["store_name"]
    )

    store_row = stores[stores["store_name"] == selected_store].iloc[0]

    st.info(f"""
    📍 선택된 매장: **{store_row['store_name']}**  
    🏙️ 지역: {store_row['city']}
    """)

    st.subheader("🧠 AI 지점 분석 (더미)")
    if st.button("AI 판단 실행"):
        st.success(
            f"""
            🔎 분석 결과:
            - {store_row['store_name']}은 최근 리뷰 기준  
              **배달 지연 관련 불만 비중이 높을 가능성**이 있습니다.
            - 본사 권장 조치: **운영 점검 우선 대상**
            """
        )

    st.divider()

    # 4️⃣ 지점 매출 현황
    st.subheader(f"📊 {store_row['store_name']} 매출 현황")

    try:
        # 일별 매출 요약 데이터 가져오기
        sales_resp = requests.get(
            f"{API_BASE_URL}/order/store/{store_row['store_id']}/daily_sales")

        if sales_resp.status_code == 200:
            sales_data = sales_resp.json()

            if sales_data:
                df_sales = pd.DataFrame(sales_data)
                df_sales['order_date'] = pd.to_datetime(df_sales['order_date'])

                # 수치 데이터 타입 변환 (차트 라이브러리 호환성)
                if 'daily_revenue' in df_sales.columns:
                    df_sales['daily_revenue'] = pd.to_numeric(
                        df_sales['daily_revenue'])

                # 매출 차트 (막대 그래프)
                chart_df = df_sales.set_index('order_date')[['daily_revenue']]
                st.bar_chart(chart_df)

                # 날짜 선택 및 상세 조회
                st.write("📅 **일별 상세 내역 조회**")
                # datetime.to_pydatetime()은 Series에서는 dt.date 등을 사용해야 함
                max_date = df_sales['order_date'].max().date()
                min_date = df_sales['order_date'].min().date()

                selected_date = st.date_input(
                    "날짜를 선택하세요",
                    value=max_date,
                    min_value=min_date,
                    max_value=max_date
                )

                # 해당 지점의 주문 상세 정보 가져오기
                orders_resp = requests.get(
                    f"{API_BASE_URL}/order/store/{store_row['store_id']}")

                if orders_resp.status_code == 200:
                    df_orders = pd.DataFrame(orders_resp.json())
                    if not df_orders.empty:
                        df_orders['ordered_at'] = pd.to_datetime(
                            df_orders['ordered_at'])

                        # 선택 날짜 필터링
                        mask = (
                            df_orders['ordered_at'].dt.date == selected_date)
                        df_day = df_orders[mask]

                        if not df_day.empty:
                            # 화면 표시용 가공
                            display_df = df_day[[
                                'menu_name', 'quantity', 'total_price', 'ordered_at']].copy()
                            display_df['ordered_at'] = display_df['ordered_at'].dt.strftime(
                                '%H:%M')
                            display_df.columns = ['메뉴명', '수량', '금액', '주문시간']

                            st.dataframe(
                                display_df, use_container_width=True, hide_index=True)

                            # 일일 요약 지표
                            m1, m2 = st.columns(2)
                            m1.metric("총 주문", f"{len(df_day)}건")
                            m2.metric(
                                "총 매출", f"{int(df_day['total_price'].sum()):,}원")
                        else:
                            st.info(f"{selected_date} 에는 주문 내역이 없습니다.")
            else:
                st.warning("이 지점은 아직 주문 데이터가 생성되지 않았습니다.")
        else:
            st.error(f"매출 데이터를 가져오지 못했습니다. (Status: {sales_resp.status_code})")

    except Exception as e:
        st.error(f"데이터 처리 중 오류 발생: {e}")

    st.divider()
