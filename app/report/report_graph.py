import json
from typing import Annotated, TypedDict, List, Dict, Any
from datetime import date
from langgraph.graph import StateGraph, END
from app.core.db import SessionLocal
from app.report.report_schema import StoreReport
from app.order.order_service import select_daily_sales_by_store
from app.review.review_service import select_reviews_by_store
from app.clients.genai import genai_generate_text

# 1. 그래프 상태(State) 정의
class ReportState(TypedDict):
    store_id: int
    store_name: str
    sales_data: List[Dict[str, Any]]
    reviews_data: List[Dict[str, Any]]
    raw_report_json: str
    final_report: Dict[str, Any]

# 2. 노드(Node) 함수들 정의

async def fetch_data_node(state: ReportState):
    """DB에서 매출과 리뷰 데이터를 수집하는 노드"""
    store_id = state["store_id"]
    print(f"🔍 [Node: Fetch] {state['store_name']} 데이터 수집 중...")
    
    sales = await select_daily_sales_by_store(store_id)
    reviews = await select_reviews_by_store(store_id)
    
    return {
        "sales_data": sales[:7], # 최근 7일
        "reviews_data": reviews[:15] # 최근 리뷰 15개
    }

async def analyze_data_node(state: ReportState):
    """수집된 데이터를 LLM으로 분석하는 작업을 수행하는 노드"""
    print(f"🧠 [Node: Analyze] AI 전략 분석 시작...")
    
    sales_summary = [{"date": str(s['order_date']), "rev": float(s['daily_revenue'])} for s in state["sales_data"]]
    review_summary = [{"rate": r['rating'], "txt": r['review_text']} for r in state["reviews_data"]]

    prompt = f"""
    프랜차이즈 경영 전문가로서 다음 데이터를 분석해줘.
    매장: {state['store_name']}
    매출현황: {json.dumps(sales_summary)}
    리뷰현황: {json.dumps(review_summary, ensure_ascii=False)}

    응답은 반드시 아래 JSON 형식으로만 할 것:
    {{
        "summary": "종합 분석 요약 (3줄)",
        "marketing_strategy": "마케팅 제안",
        "operational_improvement": "운영 개선 제안",
        "risk_assessment": {{"risk_score": 80, "main_risks": [], "suggestion": ""}}
    }}
    """
    
    report_json = await genai_generate_text(prompt)
    
    # JSON 정제
    if "```json" in report_json:
        report_json = report_json.split("```json")[1].split("```")[0].strip()
    elif "```" in report_json:
        report_json = report_json.split("```")[1].split("```")[0].strip()

    return {"raw_report_json": report_json}

async def save_report_node(state: ReportState):
    """최종 리포트를 DB에 저장하는 노드"""
    print(f"💾 [Node: Save] 분석 결과 DB 저장 중...")
    
    report_dict = json.loads(state["raw_report_json"])
    
    db_report = StoreReport(
        store_id=state["store_id"],
        report_date=date.today(),
        report_type="AI_GRAPH_REPORT",
        summary=report_dict['summary'],
        marketing_strategy=report_dict['marketing_strategy'],
        operational_improvement=report_dict['operational_improvement'],
        risk_assessment=report_dict['risk_assessment']
    )
    
    with SessionLocal() as session:
        session.query(StoreReport).filter_by(store_id=state["store_id"], report_date=date.today()).delete()
        session.add(db_report)
        session.commit()
    
    return {"final_report": report_dict}

# 3. 그래프 구성
def create_report_graph():
    workflow = StateGraph(ReportState)

    # 노드 추가
    workflow.add_node("fetch_data", fetch_data_node)
    workflow.add_node("analyze_data", analyze_data_node)
    workflow.add_node("save_report", save_report_node)

    # 엣지 연결 (순서 정의)
    workflow.set_entry_point("fetch_data")
    workflow.add_edge("fetch_data", "analyze_data")
    workflow.add_edge("analyze_data", "save_report")
    workflow.add_edge("save_report", END)

    return workflow.compile()

# 실행용 전역 변수
report_app = create_report_graph()
