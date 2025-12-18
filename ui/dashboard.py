# app/ui/dashboard.py
import streamlit as st
import pandas as pd
import plotly.express as px
from sales_component import show_sales_dialog
from api_utils import get_api


def dashboard_page():
    st.title("🚀 Dashboard")
    st.write(f"환영합니다 👋 {st.session_state.get('user_email')}")

    st.divider()

    # 1️⃣ 데이터 로드
    stores_data = get_api("/store/get")
    if not stores_data:
        st.warning("매장 데이터를 불러올 수 없습니다.")
        return
    stores = pd.DataFrame(stores_data)

    # 2️⃣ 지점 현황 지도 (Plotly 활용)
    st.subheader("🗺️ 전국 매장 현황 (지점을 클릭하세요!)")

    # Plotly Scatter Map 생성
    fig = px.scatter_mapbox(
        stores,
        lat="lat",
        lon="lon",
        hover_name="store_name",
        hover_data={"city": True, "lat": False,
                    "lon": False, "store_id": True},
        color_discrete_sequence=["#FF4B4B"],
        zoom=6,
        height=500
    )

    # 지도 스타일 설정 (고급스러운 어두운 테마)
    fig.update_layout(
        mapbox_style="carto-darkmatter",
        margin={"r": 0, "t": 0, "l": 0, "b": 0},
        clickmode='event+select',
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color="white")
    )

    # 지도 출력 및 선택 이벤트 감지 (마우스 휠 줌 활성화)
    selected_points = st.plotly_chart(
        fig, 
        use_container_width=True, 
        on_select="rerun",
        config={'scrollZoom': True, 'displayModeBar': False}
    )

    # 3️⃣ 지도 클릭 이벤트 처리
    if selected_points and "selection" in selected_points:
        points = selected_points["selection"]["points"]
        if points:
            # 클릭된 첫 번째 점의 데이터 추출
            point_data = points[0]
            # Plotly fig의 custom_data나 hover_data 순서에 따라 인덱스로 접근
            # 여기서는 stores 데이터에서 index를 찾아 처리하는 것이 안전함
            point_index = point_data.get("point_index")
            if point_index is not None:
                store_row = stores.iloc[point_index]

                # 클릭 즉시 매출 다이얼로그 호출
                show_sales_dialog(
                    store_row['store_id'], store_row['store_name'])

    st.divider()

    # 4️⃣ 기존 선택 박스 (보조용)
    st.write("💡 지도에서 점을 클릭하거나 아래 리스트에서 선택하여 정보를 확인할 수 있습니다.")
    col_sel, col_btn = st.columns([3, 1])

    with col_sel:
        selected_store_name = st.selectbox(
            "매장을 선택하세요",
            stores["store_name"]
        )
        store_row_manual = stores[stores["store_name"]
                                  == selected_store_name].iloc[0]

    with col_btn:
        st.write("")  # 간격 맞춤
        if st.button("📊 상세 보기", use_container_width=True, type="primary"):
            show_sales_dialog(
                store_row_manual['store_id'], store_row_manual['store_name'])

    st.info(
        f"📍 현재 선택박스 기준: **{store_row_manual['store_name']}** ({store_row_manual['city']})")

    st.divider()
