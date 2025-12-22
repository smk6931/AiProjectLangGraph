import os
import json
from typing import Annotated, TypedDict, List
from datetime import date

# LangChain & LangGraph 관련 임포트
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage
from langchain_core.tools import tool
from langgraph.graph import StateGraph, END
from langgraph.prebuilt import ToolNode
from langgraph.graph.message import add_messages

# 기존 프로젝트 서비스 및 모델 임포트
from app.core.db import SessionLocal
from app.report.report_schema import StoreReport
from app.order.order_service import select_daily_sales_by_store, select_menu_sales_comparison, select_sales_by_day_type
from app.review.review_service import select_reviews_by_store
from app.clients.weather import fetch_weather_data

# 1. 상태(State) 정의: "에이전트가 들고 다닐 공유 메모장"


class AgentState(TypedDict):
    # add_messages: 새로운 메시지가 생기면 기존 리스트에 자동으로 합쳐줍니다.
    messages: Annotated[List[BaseMessage], add_messages]
    store_id: int
    store_name: str

# 2. 도구(Tools) 정의: "에이전트가 손발처럼 사용할 기능들"

@tool
async def fetch_store_data(store_id: int):
    """지점의 최근 매출과 리뷰 데이터를 수집하고 주요 지표를 계산합니다."""
    print(f"🛠️ [Tool] {store_id}번 지점 데이터 분석 중...")
    sales = await select_daily_sales_by_store(store_id)
    reviews = await select_reviews_by_store(store_id)
    menu_stats = await select_menu_sales_comparison(store_id, days=7)
    day_stats = await select_sales_by_day_type(store_id, days=7)

    # 기본 수치 계산
    total_rev = sum(float(s['daily_revenue']) for s in sales)
    avg_rating = sum(r['rating'] for r in reviews) / len(reviews) if reviews else 0
    
    # 최근 3일 vs 이전 4일 비교 (여전히 유지하지만, 메뉴 분석은 7일 기준)
    recent_3 = sum(float(s['daily_revenue']) for s in sales[:3]) / 3 if len(sales) >= 3 else 0
    prev_4 = sum(float(s['daily_revenue']) for s in sales[3:7]) / 4 if len(sales) >= 7 else total_rev/7
    trend = ((recent_3 - prev_4) / prev_4 * 100) if prev_4 > 0 else 0

    # 메뉴별 증감 분석 (매출 기준 내림차순 정렬된 상태)
    # 1. Top Selling (매출액 상위)
    top_selling = []
    # 2. Top Dropping (감소폭 하위 - 역성장)
    # 계산을 위해 모든 리스트 변환
    processed_menus = []
    for m in menu_stats:
        rec_rev = float(m['recent_revenue'])
        prev_rev = float(m['prev_revenue'])
        change_pct = ((rec_rev - prev_rev) / prev_rev * 100) if prev_rev > 0 else (100 if rec_rev > 0 else 0)
        
        item = {
            "menu": m['menu_name'],
            "cat": m['category'],
            "recent_rev": rec_rev,
            "prev_rev": prev_rev,
            "change_pct": round(change_pct, 1)
        }
        processed_menus.append(item)
    
    # 매출액 기준 정렬
    sorted_by_rev = sorted(processed_menus, key=lambda x: x['recent_rev'], reverse=True)
    top_selling = sorted_by_rev[:5]

    # 감소율 기준 정렬 (하락폭이 큰 순서 -> change_pct가 작은 순서)
    # 단, 이전 매출이 있었던 항목 중에서만 따지는게 의미가 있음 (prev_rev > 0)
    dropping_candidates = [m for m in processed_menus if m['prev_rev'] > 0]
    sorted_by_drop = sorted(dropping_candidates, key=lambda x: x['change_pct']) # 오름차순 (예: -50%, -10%, +5%)
    worst_dropping = sorted_by_drop[:5]

    # 요일별(평일/주말) 분석
    day_analysis = []
    for d in day_stats:
        r_rev = float(d['recent_revenue'])
        p_rev = float(d['prev_revenue'])
        d_trend = ((r_rev - p_rev) / p_rev * 100) if p_rev > 0 else 0
        day_analysis.append({
            "type": d['day_type'],
            "recent": r_rev,
            "prev": p_rev,
            "trend": round(d_trend, 1)
        })

    # 매출 리스트에 날씨 정보 (DB에서 이미 가져옴)
    recent_sales_with_weather = []
    # sales는 날짜 오름차순(ASC)이므로, 최근 7일 데이터는 리스트의 뒤쪽 데이터입니다.
    # sales[-7:] = [D-6, D-5, ... D-day]
    # recent_3 (최근 3일): sales[-3:]
    # prev_4 (그전 4일): sales[-7:-3]
    
    # I will fix this logic to be correct for ASC sorted data.
    
    target_sales = sales[-7:] if len(sales) >= 7 else sales
    
    recent_sales_with_weather = []
    # 차트 표시를 위해 날짜 오름차순 유지
    
    for s in target_sales:
        d_str = str(s['order_date'])
        recent_sales_with_weather.append({
            "date": d_str,
            "rev": float(s['daily_revenue']),
            "weather": s.get('weather_info', "알수없음")
        })
        
    # 전체 기간에 대한 통계 계산
    
    total_rev = sum(float(s['daily_revenue']) for s in target_sales) # Let's focus on recent 7 days for the report metrics to be consistent with text "Recent 7 days"
    avg_rev = total_rev / len(target_sales) if target_sales else 0
    
    # Trend: Recent 3 vs Prev 4 within the 7 days window
    if len(target_sales) >= 7:
        # sales are ASC: [0,1,2,3, 4,5,6]
        # recent 3: 4,5,6 -> sales[4:]
        # prev 4: 0,1,2,3 -> sales[:4]
        rec_slice = target_sales[4:]
        prev_slice = target_sales[:4]
        
        recent_3_sum = sum(float(s['daily_revenue']) for s in rec_slice)
        recent_3_avg = recent_3_sum / 3
        
        prev_4_sum = sum(float(s['daily_revenue']) for s in prev_slice)
        prev_4_avg = prev_4_sum / 4
        
        trend = ((recent_3_avg - prev_4_avg) / prev_4_avg * 100) if prev_4_avg > 0 else 0
    else:
         trend = 0

    data_summary = {
        "metrics": {
            "total_rev": total_rev,
            "avg_rev": avg_rev,
            "trend_percent": trend,
            "avg_rating": avg_rating
        },
        "recent_sales": recent_sales_with_weather,
        "top_reviews": [{"rate": r['rating'], "text": r['review_text']} for r in reviews[:10]],
        "top_selling_menus": top_selling,
        "worst_dropping_menus": worst_dropping,
        "day_analysis": day_analysis
    }
    return json.dumps(data_summary, ensure_ascii=False)


@tool
async def save_strategic_report(
    store_id: int,
    summary: str,
    marketing_strategy: str,
    operational_improvement: str,
    data_evidence_json: str,
    metrics_json: str,
    source_data_json: str = None,
    risk_score: int = 50
):
    """
    분석 결과를 바탕으로 최종 리포트를 DB에 저장합니다.
    - data_evidence_json: 분석의 근거가 되는 수치 및 문구 (JSON)
    - metrics_json: 계산된 핵심 지표 (JSON)
    - source_data_json: 분석에 사용된 기초 데이터 (최근 매출 등)
    """
    print(f"🛠️ [Tool] 리포트 저장 중 (ID: {store_id})")

    risk_info = {
        "risk_score": risk_score,
        "metrics": json.loads(metrics_json) if isinstance(metrics_json, str) else metrics_json,
        "data_evidence": json.loads(data_evidence_json) if isinstance(data_evidence_json, str) else data_evidence_json
    }
    
    if source_data_json:
        risk_info["source_data"] = json.loads(source_data_json) if isinstance(source_data_json, str) else source_data_json

    db_report = StoreReport(
        store_id=store_id,
        report_date=date.today(),
        report_type="AI_AUTONOMOUS_REPORT",
        summary=summary,
        marketing_strategy=marketing_strategy,
        operational_improvement=operational_improvement,
        risk_assessment=risk_info
    )

    with SessionLocal() as session:
        session.query(StoreReport).filter_by(
            store_id=store_id, report_date=date.today()).delete()
        session.add(db_report)
        session.commit()

    return "성공적으로 저장되었습니다. 이제 업무를 종료하세요."

# 3. 노드(Node) 정의: "실제로 일하는 작업자"


async def call_model(state: AgentState):
    """AI가 현재 상황을 보고 판단하여 행동(말하기 또는 툴 사용)을 결정하는 노드"""
    print("🤖 [Agent] 생각 중...")

    llm = ChatGoogleGenerativeAI(
        model="gemini-2.0-flash",
        google_api_key=os.getenv("GEMINI_API_KEY"),
        temperature=0
    )
    # AI에게 사용할 수 있는 도구들을 연결해줍니다.
    llm_with_tools = llm.bind_tools([fetch_store_data, save_strategic_report])

    # 처음 시작할 때 시스템 지침(SystemMessage)을 넣어줍니다.
    messages = state.get("messages", [])
    if not messages:
        sys_msg = SystemMessage(content=(
            f"당신은 '{state['store_name']}' 지점의 경영 전문가입니다.\n"
            "1. fetch_store_data로 매출, 날씨, 메뉴, 요일별 데이터를 모두 수집하세요.\n"
            "2. **'외부 요인(날씨) 분석'**을 반드시 포함해야 합니다.\n"
            "   - '비오는 날 매출 하락'은 정상 참작(Normal)이지만, **'맑은 날인데도 평소보다 매출이 급감'**했다면 이를 '심각한 위기(Critical Crisis)'로 진단하세요.\n"
            "   - 예: '12월 20일은 맑았음에도 불구하고 지난주 동요일 대비 매출이 30% 하락했습니다. 이는 내부 운영 문제입니다.'\n"
            "3. 기존의 메뉴/요일 분석(무엇이/언제 안 팔렸나)도 계속 진행하세요.\n"
            "4. 리포트 작성 시 수치적 근거(날씨 포함)를 명확히 제시하고 마크다운 표를 활용하세요."
        ))
        start_msg = HumanMessage(content="업무를 시작해 주세요.")
        messages = [sys_msg, start_msg]

    response = await llm_with_tools.ainvoke(messages)

    # 결과를 메모장(State)에 업데이트합니다.
    return {"messages": [response]}

# 4. 그래프(Graph) 구성: "일의 순서도 그리기"


def create_simple_autonomous_graph():
    # 메모장(State)을 사용하는 워크플로우 생성
    workflow = StateGraph(AgentState)

    # 작업자(Node) 등록
    workflow.add_node("agent", call_model)
    workflow.add_node("tools", ToolNode(
        [fetch_store_data, save_strategic_report]))

    # 시작점 설정
    workflow.set_entry_point("agent")

    workflow.add_conditional_edges( "agent",
        lambda stategraph: "tools" if stategraph["messages"][-1].tool_calls else "end",
        {
            "tools": "tools",
            "end": END
        }
    )

    workflow.add_edge("tools", "agent")

    return workflow.compile()

        # def should_continue(state: AgentState):
    #     last_message = state["messages"][-1]
    #     if last_message.tool_calls:
    #         return "tools"  
    #     return "end"       
