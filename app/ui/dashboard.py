# app/ui/dashboard.py
import streamlit as st
import pandas as pd
import pydeck as pdk

def dashboard_page():
    st.title("🚀 Dashboard")
    st.write(f"환영합니다 👋 {st.session_state.get('user_email')}")

    st.divider()
    st.subheader("🗺️ 전국 매장 현황 (임시 데이터)")

    # 1️⃣ 임시 매장 데이터
    stores = pd.DataFrame([
        {"store_id": 1, "store_name": "서울점", "city": "서울", "lat": 37.5665, "lon": 126.9780},
        {"store_id": 2, "store_name": "부산점", "city": "부산", "lat": 35.1796, "lon": 129.0756},
        {"store_id": 3, "store_name": "대구점", "city": "대구", "lat": 35.8714, "lon": 128.6014},
        {"store_id": 4, "store_name": "강원점", "city": "강원", "lat": 37.8228, "lon": 128.1555},
    ])

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

    # 3️⃣ 매장 선택 UI (지도 클릭 보조용)
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

    if st.button("로그아웃"):
        st.session_state.clear()
        st.session_state.page = "login"
        st.rerun()