import streamlit as st


def render_session_state_viewer():
    """
    st.session_state의 내용을 토글 버튼으로 보여주거나 숨기는 디버그 컴포넌트
    """
    # 세션 상태에 토글 여부 저장
    if "show_session_debug" not in st.session_state:
        st.session_state.show_session_debug = False

    st.divider()

    # 토글 버튼 (Flip-Flop)
    cols = st.columns([1, 4])
    with cols[0]:
        if st.button("🛠️"):
            st.session_state.show_session_debug = not st.session_state.show_session_debug
            st.rerun()

    # 표시 영역
    if st.session_state.show_session_debug:
        with st.expander("🔍 Current Session State Data", expanded=True):
            # 딕셔너리 형태로 변환하여 JSON 출력
            state_dict = {k: v for k, v in st.session_state.items()
                          if k != "show_session_debug"}
            st.json(state_dict)

            # 정보성 텍스트
            st.caption("이 패널은 개발 중에만 활성화하여 세션 상태를 추적할 수 있습니다.")
