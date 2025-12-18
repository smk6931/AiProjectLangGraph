import streamlit as st
import pandas as pd
import requests

API_BASE_URL = "http://127.0.0.1:8080"

def menu_page():
    st.title("🍴 메뉴 관리")
    st.write("데이터베이스에 등록된 전체 메뉴 목록입니다.")

    try:
        response = requests.get(f"{API_BASE_URL}/menu/get")
        if response.status_code == 200:
            menu_data = response.json()
            if not menu_data:
                st.warning("등록된 메뉴가 없습니다.")
                return

            # DataFrame으로 변환
            df = pd.DataFrame(menu_data)

            # 컬럼 한글화 (선택 사항)
            column_mapping = {
                "menu_id": "ID",
                "menu_name": "메뉴명",
                "category": "카테고리",
                "cost_price": "원가",
                "list_price": "정가",
                "main_ingredient": "주재료",
                "is_seasonal": "시즌여부",
                "description": "설명"
            }

            # 존재하는 컬럼만 매핑
            df_display = df.rename(
                columns={k: v for k, v in column_mapping.items() if k in df.columns})

            # 필터링 UI
            cols = st.columns(2)
            with cols[0]:
                category_filter = st.multiselect(
                    "카테고리 선택", options=df_display["카테고리"].unique())

            if category_filter:
                df_display = df_display[df_display["카테고리"].isin(
                    category_filter)]

            # 데이터 테이블 표시
            st.dataframe(df_display, use_container_width=True)

            # 상세 요약 통계
            st.divider()
            st.subheader("📊 메뉴 통계")
            col1, col2, col3 = st.columns(3)
            col1.metric("전체 메뉴 수", len(df))
            col2.metric("평균 가격", f"{df['list_price'].mean():,.0f}원" if 'list_price' in df and not df['list_price'].isnull(
            ).all() else "N/A")
            col3.metric("시즌 메뉴 수", len(
                df[df['is_seasonal'] == True]) if 'is_seasonal' in df else 0)

        else:
            st.error(f"데이터 조회 실패: {response.status_code}")
    except Exception as e:
        st.error(f"API 연결 실패: {e} (백엔드 서버가 켜져 있는지 확인하세요)")
