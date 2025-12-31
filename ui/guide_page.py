import streamlit as st
import pandas as pd
from api_utils import get_api

def guide_page():
    st.title("📚 매장 운영 가이드")
    st.markdown("매장 운영에 필요한 **매뉴얼**과 **사내 규정**을 조회할 수 있습니다.")

    # 탭 생성
    tab1, tab2 = st.tabs(["🛠️ 업무 매뉴얼", "📋 사내 규정 (Policy)"])

    # --- TAB 1: 매뉴얼 ---
    with tab1:
        st.subheader("업무 매뉴얼 조회")
        
        # 검색창
        search_query_manual = st.text_input("🔍 매뉴얼 검색 (키워드 입력)", key="manual_search")
        
        api_res = get_api("/manual/get")
        
        if api_res:
            df_manual = pd.DataFrame(api_res)
            
            # 검색 필터
            if search_query_manual:
                mask = df_manual.apply(lambda x: search_query_manual in str(x['title']) or search_query_manual in str(x['content']), axis=1)
                df_manual = df_manual[mask]
            
            if not df_manual.empty:
                # 카테고리별 그룹핑
                categories = df_manual['category'].unique()
                
                for cat in categories:
                    st.markdown(f"### 📂 {cat}")
                    cat_items = df_manual[df_manual['category'] == cat]
                    
                    for _, row in cat_items.iterrows():
                        with st.expander(f"**{row['title']}**"):
                            st.write(row['content'])
                            st.caption(f"Last Updated: {row.get('updated_at', row.get('created_at', ''))}")
            else:
                st.info("검색 결과가 없습니다.")
        else:
            st.warning("매뉴얼 데이터를 불러올 수 없습니다.")

    # --- TAB 2: 사내 규정 ---
    with tab2:
        st.subheader("사내 규정 및 정책")
        
        # 검색창
        search_query_policy = st.text_input("🔍 규정 검색 (키워드 입력)", key="policy_search")
        
        api_res_poly = get_api("/policy/get")
        
        if api_res_poly:
            df_policy = pd.DataFrame(api_res_poly)
            
            # 검색 필터
            if search_query_policy:
                mask = df_policy.apply(lambda x: search_query_policy in str(x['title']) or search_query_policy in str(x['content']), axis=1)
                df_policy = df_policy[mask]
            
            if not df_policy.empty:
                # 카테고리별 그룹핑
                categories = df_policy['category'].unique()
                
                for cat in categories:
                    st.markdown(f"### 🛡️ {cat}")
                    cat_items = df_policy[df_policy['category'] == cat]
                    
                    for _, row in cat_items.iterrows():
                        with st.expander(f"**{row['title']}**"):
                            # 규정은 좀 더 강조된 UI
                            st.info(row['content'], icon="ℹ️")
            else:
                st.info("검색 결과가 없습니다.")
        else:
            st.warning("규정 데이터를 불러올 수 없습니다.")
