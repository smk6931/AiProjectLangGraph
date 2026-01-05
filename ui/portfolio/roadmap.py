import streamlit as st

def render_roadmap():
    st.header("12. 🚀 Future Roadmap")
    st.caption("From Linear Chain to Autonomous Agent")

    st.markdown("### 🔮 Next Step: Self-Correction Loop")
    st.write("현재는 에러가 나면 멈추지만(Linear), 앞으로는 **스스로 고치는(Loop)** 구조로 갑니다.")

    st.graphviz_chart("""
    digraph Loop {
        rankdir=LR;
        node [shape=box, style=filled, fillcolor="white"];
        
        Start -> Generate;
        Generate -> Validate [label="검증"];
        
        Validate -> End [label="성공(OK)", color="green"];
        Validate -> Refine [label="실패(Fail)", color="red"];
        
        Refine [label="Refine Prompt\n(피드백 반영)", fillcolor="#ffcccc"];
        Refine -> Generate [label="재시도(Retry)"];
    }
    """)

    st.info("""
    **Expectation**:
    사람의 개입 없이도 AI가 포맷 에러, 데이터 누락을 스스로 인지하고 수정하여
    **'완전 자율 운영(Autonomous Operation)'** 달성.
    """)
