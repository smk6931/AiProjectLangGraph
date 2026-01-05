import streamlit as st

def render_planning():
    st.header("2. 🎯 Planning Intent")
    st.caption("기획 의도 & 시장 분석")

    st.markdown("### 🛑 The Problem: 사장님들은 'Why'를 모른다")
    
    # 문제 상황 연출 (Chat UI 스타일)
    with st.chat_message("user", avatar="👨‍🍳"):
        st.write("오늘 매출이 평소보다 30%나 떨어졌네... 왜 이러지? 날씨 때문인가? 아니면 알바가 실수를 했나?")
    
    with st.chat_message("assistant", avatar="📠"):
        st.write("POS기: (묵묵부답) .. 오늘의 매출: 300,000원")

    st.error("""
    **Pain Point**: 
    자영업자의 90%는 POS에 찍히는 '결과(숫자)'만 볼 뿐, **'원인'을 분석할 시간도 능력도 부족합니다.**
    배달 앱, 발주 사이트, POS가 다 따로 놀아서 데이터를 합치는 것조차 일입니다.
    """)

    st.divider()

    st.markdown("### ✅ The Solution: AI가 '떠먹여 주는' 분석")
    
    col1, col2 = st.columns(2)
    with col1:
        st.image("https://images.unsplash.com/photo-1551288049-bebda4e38f71?q=80&w=1000&auto=format&fit=crop", caption="Legacy: 복잡한 엑셀 작업", use_container_width=True)
    with col2:
        st.success("**AI Manager**")
        st.markdown("""
        1. **Automation**: 새벽에 AI가 어제 데이터를 자동 수집
        2. **Reasoning**: "비가 와서 배달이 늘었네요"라고 Human-like 분석
        3. **Action**: "내일은 재료를 10% 덜 준비하세요"라고 전략 제안
        """)

    st.info("""
    **Business Opportunity**:
    무인 매장 트렌드가 가속화되면서, **'원격으로 매장을 똑똑하게 관리해주는 AI'**에 대한 니즈는 폭발적으로 성장하고 있습니다.
    """)
