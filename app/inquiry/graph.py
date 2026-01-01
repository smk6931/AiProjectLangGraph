from langgraph.graph import StateGraph, END
from app.inquiry.state import InquiryState
from app.inquiry.nodes.router import router_node
from app.inquiry.nodes.diagnosis import diagnosis_node
from app.inquiry.nodes.retrieval import retrieval_node
from app.inquiry.nodes.answer import answer_node

# 1. 그래프 초기화
workflow = StateGraph(InquiryState)

# 2. 노드 등록 (일꾼 배치)
workflow.add_node("router", router_node)
workflow.add_node("diagnosis", diagnosis_node)
workflow.add_node("retrieval", retrieval_node)
workflow.add_node("answer", answer_node)

# 3. 엣지 연결 (업무 흐름 정의)
# 시작 -> Router
workflow.set_entry_point("router")

# Router -> (조건부 분기) -> Diagnosis or Retrieval
def route_decision(state: InquiryState):
    category = state.get("category", "general")
    if category == "sales":
        return "diagnosis"
    elif category in ["manual", "policy"]:
        return "retrieval"
    else:
        return "answer" # General 질문은 바로 답변

workflow.add_conditional_edges(
    "router",
    route_decision,
    {
        "diagnosis": "diagnosis",
        "retrieval": "retrieval",
        "answer": "answer"
    }
)

# Diagnosis/Retrieval -> Answer (결과 취합)
workflow.add_edge("diagnosis", "answer")
workflow.add_edge("retrieval", "answer")

# Answer -> END (종료)
workflow.add_edge("answer", END)

# 4. 컴파일 (실행 가능한 앱 생성)
inquiry_app = workflow.compile()
