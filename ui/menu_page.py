import streamlit as st
import pandas as pd
from api_utils import get_api


def menu_page():
    st.title("🍴 메뉴 관리")
    st.write("데이터베이스에 등록된 전체 메뉴 목록입니다.")

    menu_data = get_api("/menu/get")

    if menu_data:
        # DataFrame으로 변환
        df = pd.DataFrame(menu_data)

        # 컬럼 한글화
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
            df_display = df_display[df_display["카테고리"].isin(category_filter)]

        # 데이터 테이블 표시
        st.dataframe(df_display, use_container_width=True)

        # 상세 요약 통계
        st.divider()
        st.subheader("📊 메뉴 통계")
        col1, col2, col3 = st.columns(3)
        col1.metric("전체 메뉴 수", len(df))

        avg_price = df['list_price'].mean(
        ) if 'list_price' in df and not df['list_price'].isnull().all() else 0
        col2.metric("평균 가격", f"{avg_price:,.0f}원")

        seasonal_count = len(df[df['is_seasonal'] == True]
                             ) if 'is_seasonal' in df else 0
        col3.metric("시즌 메뉴 수", seasonal_count)
    else:
        st.info("메뉴 데이터를 불러올 수 없습니다.")
