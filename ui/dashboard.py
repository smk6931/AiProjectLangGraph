# app/ui/dashboard.py
import streamlit as st
import pandas as pd
import plotly.express as px
from sales_component import show_sales_dialog
from api_utils import get_api

def dashboard_page():
    # Premium Gradient Header
    st.markdown("<h1> Dashboard</h1>", unsafe_allow_html=True)
    st.caption(f"환영합니다, {st.session_state.get('user_email')}님 | 실시간 매장 모니터링")

    st.divider()

    # 1️⃣ 데이터 로드
    stores_data = get_api("/store/get")
    if not stores_data:
        st.warning("매장 데이터를 불러올 수 없습니다.")
        return
    stores = pd.DataFrame(stores_data)

    # 2️⃣ 지점 현황 지도 & 리스트 (2단 레이아웃)
    st.subheader("전국 매장 현황")

    col_map, col_list = st.columns([3, 1])

    with col_map:
        # Plotly Scatter Map 생성
        fig = px.scatter_mapbox(
            stores,
            lat="lat",
            lon="lon",
            text="city",  # 텍스트로 표시할 컬럼 (예: 서울, 부산)
            hover_name="store_name",
            hover_data={"city": True, "lat": False,
                        "lon": False, "store_id": True},
            color_discrete_sequence=["#FF4B4B"],
            zoom=6,
            height=600  # 세로로 긴 지도 비율에 맞춤
        )

        # 텍스트 스타일 및 마커 설정
        fig.update_traces(
            mode='markers+text',
            textposition='top right',
            textfont=dict(size=11, color="white"),
            marker=dict(size=12)
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

    # 3️⃣ 우측 매장 리스트
    with col_list:
        st.write("#### 🏪 매장 선택")
        st.caption("목록에서 선택하거나 지도를 클릭하세요.")
        
        selected_store_name = st.selectbox(
            "매장 목록",
            stores["store_name"],
            label_visibility="collapsed"
        )
        
        store_row_manual = stores[stores["store_name"] == selected_store_name].iloc[0]
        
        st.info(f"📍 **{store_row_manual['city']}**\n\n{store_row_manual['store_name']}")
        
        if st.button("📊 상세 보기", type="primary", use_container_width=True):
             show_sales_dialog(store_row_manual['store_id'], store_row_manual['store_name'])

    # 4️⃣ 지도 클릭 이벤트 처리
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
