import streamlit as st
import pandas as pd
from api_utils import get_api


def review_page():
    st.title("💬 리뷰 관리")
    st.write("지점별 리뷰를 확인하고 분석할 수 있는 페이지입니다.")
    st.divider()

    # 1. 지점 데이터 로드
    stores_data = get_api("/store/get")
    if not stores_data:
        st.warning("매장 데이터를 불러올 수 없습니다.")
        return

    stores = pd.DataFrame(stores_data)

    # 2. 매장 선택
    selected_store_name = st.selectbox(
        "리뷰를 확인할 매장을 선택하세요",
        stores["store_name"]
    )
    store_row = stores[stores["store_name"] == selected_store_name].iloc[0]
    store_id = int(store_row['store_id'])

    st.info(f"📍 **{selected_store_name}**의 리뷰 목록입니다.")

    # 3. 리뷰 데이터 로드
    reviews_data = get_api(f"/review/store/{store_id}")

    if not reviews_data:
        st.info("해당 지점에 등록된 리뷰가 없습니다.")
        return

    df_reviews = pd.DataFrame(reviews_data)
    df_reviews['created_at'] = pd.to_datetime(df_reviews['created_at'])
    if 'ordered_at' in df_reviews.columns:
        df_reviews['ordered_at'] = pd.to_datetime(df_reviews['ordered_at'])

    # 통계 요약
    col1, col2, col3 = st.columns(3)
    avg_rating = df_reviews['rating'].mean()
    col1.metric("평균 평점", f"{avg_rating:.1f} / 5.0")
    col2.metric("총 리뷰 수", f"{len(df_reviews)}건")

    high_rating_ratio = (
        len(df_reviews[df_reviews['rating'] >= 4]) / len(df_reviews)) * 100
    col3.metric("긍정 리뷰 비율", f"{high_rating_ratio:.1f}%")

    st.divider()

    # 4. 리뷰 목록 표시 (카드 형태나 리스트)
    for _, row in df_reviews.iterrows():
        with st.container():
            # 평점에 따른 별 모양 표시
            stars = "⭐" * int(row['rating'])

            # 배달 앱 아이콘/텍스트
            delivery = f"[{row['delivery_app']}]" if row['delivery_app'] else "[방문]"

            st.markdown(f"### {stars} {row['rating']}.0")
            st.write(
                f"**메뉴:** {row['menu_name']} | **작성일:** {row['created_at'].strftime('%Y-%m-%d %H:%M')}")

            # 실제 주문 데이터와의 연결성 표시
            if pd.notnull(row['ordered_at']):
                st.caption(
                    f"🔗 실제 주문일: {row['ordered_at'].strftime('%Y-%m-%d %H:%M')}")

            st.info(row['review_text'])
            st.divider()
