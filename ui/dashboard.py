# app/ui/dashboard.py
import streamlit as st
import pandas as pd
import pydeck as pdk
import requests

API_BASE_URL = "http://127.0.0.1:8080"

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

    # DataFrame 변환 (API 응답은 JSON 리스트이므로 바로 변환 가능)
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
