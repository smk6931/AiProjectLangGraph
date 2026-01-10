from langgraph.graph import StateGraph, END
from app.inquiry.inquiry_schema import InquiryState
from app.inquiry.nodes.router import router_node
from app.inquiry.nodes.sales import diagnosis_node
from app.inquiry.nodes.retrieval import manual_node, policy_node, web_search_node
from app.inquiry.nodes.answer import answer_node_v2
from app.inquiry.nodes.save import save_node

# [Archive] 
# 이 코드는 초기 LangGraph 완전 자동화 아키텍처 예시입니다.
# 현재는 Human-in-the-Loop(UI 검증)을 위해 API 단계에서 분리하여 실행하지만,
# 향후 완전 자동화 모드로 전환 시 이 그래프 구조를 재사용할 수 있습니다.

def create_inquiry_graph_archive():
    """
    [Archived] LangGraph 생성 - Hybrid Search & Fallback Logic 적용
    """
    graph = StateGraph(InquiryState)
    
    # 노드 등록
    graph.add_node("router", router_node)
    graph.add_node("sales", diagnosis_node)
    graph.add_node("manual", manual_node)
    graph.add_node("policy", policy_node)
    graph.add_node("web_search", web_search_node)
    graph.add_node("answer", answer_node_v2) 
    graph.add_node("save", save_node)
    
    # 엔트리 포인트
    graph.set_entry_point("router")
    
    # Conditional Edge
    def route_question(state: InquiryState) -> str:
        return state["category"]
    
    graph.add_conditional_edges(
        "router",
        route_question,
        {
            "sales": "sales",
            "manual": "manual",
            "policy": "policy"
        }
    )
    
    # 검색 품질 평가
    def evaluate_search_result(state: InquiryState) -> str:
        meta = state.get("search_meta", {})
        min_dist = meta.get("min_distance", 1.0)
        THRESHOLD = 0.65
        return "retry_web" if min_dist > THRESHOLD else "proceed"

    # Edge 연결
    graph.add_conditional_edges("manual", evaluate_search_result, {"proceed": "answer", "retry_web": "web_search"})
    graph.add_conditional_edges("policy", evaluate_search_result, {"proceed": "answer", "retry_web": "web_search"})
    
    graph.add_edge("sales", "answer")
    graph.add_edge("web_search", "answer")
    graph.add_edge("answer", "save")
    graph.add_edge("save", END)
    
    return graph.compile()

# Test Runner (Optional)
if __name__ == "__main__":
    print("✅ LangGraph definition loaded successfully.")
