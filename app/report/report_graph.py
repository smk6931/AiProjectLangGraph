import json
from typing import Annotated, TypedDict, List, Dict, Any
from datetime import date
from langgraph.graph import StateGraph, END
from app.core.db import SessionLocal
from app.report.report_schema import StoreReport
from app.order.order_service import select_daily_sales_by_store, select_menu_sales_comparison, select_sales_by_day_type
from app.review.review_service import select_reviews_by_store
from app.clients.genai import genai_generate_text
from app.clients.weather import fetch_weather_data

from langgraph.graph.message import add_messages

# 리스트를 덮어쓰지 않고 추가하기 위한 리듀서 함수
def append_logs(left: List[str], right: List[str]) -> List[str]:
    return left + right

# 1. 그래프 상태(State) 정의
class ReportState(TypedDict):
    store_id: int
    store_name: str
    sales_data: List[Dict[str, Any]]
    reviews_data: List[Dict[str, Any]]
    menu_sales_data: List[Dict[str, Any]]
    day_sales_data: List[Dict[str, Any]]
    weather_data: Dict[str, str]  # 날씨 데이터 { "2024-01-01": "맑음" }
    final_report: Dict[str, Any]
    execution_logs: Annotated[List[str], append_logs]


async def fetch_store_data(store_id: int):
    # This is report_autonomous.py tool, but I am editing report_graph.py nodes.
    # report_graph.py doesn't use @tool. It uses fetch_data_node.
    pass

async def fetch_data_node(state: ReportState):
    """DB에서 매출과 리뷰 데이터를 수집하는 노드"""
    store_id = state["store_id"]
    log = f"📊 [Fetch] '{state['store_name']}' 데이터 수집 시작"
    print(log)

    sales = await select_daily_sales_by_store(store_id)
    reviews = await select_reviews_by_store(store_id)
    menu_stats = await select_menu_sales_comparison(store_id, days=7)
    day_stats = await select_sales_by_day_type(store_id, days=7)

    # 날씨 데이터는 sales에 이미 포함되어 있음.
    # sales는 ASC 정렬 (과거 -> 현재)
    # 최근 7일치만 잘라서 사용
    target_sales = sales[-7:] if len(sales) >= 7 else sales
    
    # weather_map 구성 (기존 코드 호환성 유지)
    weather_map = {str(s['order_date']): s.get('weather_info', '알수없음') for s in target_sales}

    return {
        "sales_data": target_sales,  # 최근 7일
        "reviews_data": reviews[:15],  # 최근 리뷰 15개
        "menu_sales_data": menu_stats, # 메뉴별 판매 데이터
        "day_sales_data": day_stats,   # 요일별(평일/주말) 분석 데이터
        "weather_data": weather_map,   # 날씨 데이터 (분석 노드에서 사용)
        "execution_logs": [log, f"✅ [Fetch] 데이터 수집 완료 (날씨 정보 포함)"]
    }

async def analyze_data_node(state: ReportState):
    """데이터 분석 및 수치적 근거 계산을 수행하는 노드"""
    log = "🧠 [Analyze] 수치 데이터 계산 및 AI 분석 시작"
    print(log)

    sales = state["sales_data"]
    reviews = state["reviews_data"]
    menu_stats = state.get("menu_sales_data", [])
    day_stats = state.get("day_sales_data", [])
    weather_map = state.get("weather_data", {})

    # 수치 데이터 직접 계산 (sales는 이미 최근 7일치만 들어옴)
    total_rev = sum(float(s['daily_revenue']) for s in sales)
    avg_rev = total_rev / len(sales) if sales else 0
    
    # Trend Calculation (Recent 3 vs Prev 4)
    # sales is ASC [old ... new]
    if len(sales) >= 7:
        rec_val = sum(float(s['daily_revenue']) for s in sales[4:]) / 3  # Last 3
        prev_val = sum(float(s['daily_revenue']) for s in sales[:4]) / 4 # First 4
        trend = ((rec_val - prev_val) / prev_val * 100) if prev_val > 0 else 0
    else:
        trend = 0
        
    avg_rating = sum(r['rating'] for r in reviews) / len(reviews) if reviews else 0

    # 메뉴별 증감 분석 (매출 기준 내림차순 정렬된 상태)
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
    
    # 1. Top Selling (매출액 상위)
    top_selling = sorted(processed_menus, key=lambda x: x['recent_rev'], reverse=True)[:5]

    # 2. Top Dropping (감소폭 하위) - 역성장 메뉴
    dropping_candidates = [m for m in processed_menus if m['prev_rev'] > 0]
    worst_dropping = sorted(dropping_candidates, key=lambda x: x['change_pct'])[:5]

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

    # UI용 원본 데이터 요약 (날짜, 매출만) + 날씨 추가
    source_sales = []
    for s in sales:
        d_str = str(s['order_date'])
        source_sales.append({
            "date": d_str,
            "revenue": float(s['daily_revenue']),
            "weather": s.get('weather_info', "알수없음")
        })

    prompt = f"""
    프랜차이즈 경영 전문가로서 다음 데이터를 분석하고 **수치적 근거**를 바탕으로 해결책을 제시해줘.
    매장: {state['store_name']}
    총 매출(7일): {total_rev:,.0f}원 | 일평균: {avg_rev:,.0f}원 | 추세: {trend:+.1f}% | 평점: {avg_rating:.1f}
    
    상세 매출 내역 (날씨 포함): {json.dumps(source_sales, ensure_ascii=False)}
    상세 리뷰 내역: {json.dumps([{"rate": r['rating'], "txt": r['review_text']} for r in reviews], ensure_ascii=False)}
    
    [메뉴 분석]
    잘 팔린 메뉴 (TOP 5): {json.dumps(top_selling, ensure_ascii=False)}
    급감한 메뉴 (WORST 5): {json.dumps(worst_dropping, ensure_ascii=False)}

    [요일/시간 분석]
    평일 vs 주말 매출 변동: {json.dumps(day_analysis, ensure_ascii=False)}

    분석 시 다음 사항을 반드시 지켜줘:
    1. **"무엇이, 언제, 외부에 의해 안 팔렸나?"** 다각도로 분석하세요.
    2. **날씨와 매출의 상관관계**를 반드시 언급하세요. 
       - "비가 왔음에도 매출이 선방했다" (긍정) 또는 "날씨가 맑았는데도 매출이 급감했다" (부정) 등.
    3. 수치적 근거(Top 5 메뉴명, 주말 매출 변동률 등)를 포함하여 마크다운 표로 시각화하세요.
    
    응답은 반드시 아래 JSON 형식으로만 할 것:
    {{
        "data_evidence": {{
            "sales_analysis": "날씨, 메뉴, 요일별 데이터를 종합한 상세 매출 분석 (마크다운 표 포함 필수)",
            "review_analysis": "평점과 리뷰 결합 분석"
        }},
        "summary": "종합 분석 요약 (3줄)",
        "marketing_strategy": "외부 요인(날씨 등)을 고려한 마케팅 제안",
        "operational_improvement": "운영 개선 제안",
        "risk_assessment": {{"risk_score": 80, "main_risks": [], "suggestion": ""}}
    }}
    """

    report_json = await genai_generate_text(prompt)
    if "```json" in report_json:
        report_json = report_json.split("```json")[1].split("```")[0].strip()
    elif "```" in report_json:
        report_json = report_json.split("```")[1].split("```")[0].strip()

    report_dict = json.loads(report_json)
    
    # UI용 통계 데이터 및 소스 데이터 추가
    report_dict["metrics"] = {
        "total_rev": total_rev,
        "avg_rev": avg_rev,
        "trend_percent": trend,
        "avg_rating": avg_rating
    }
    report_dict["source_data"] = {
        "recent_sales": source_sales,
        "review_count": len(reviews),
        "top_selling_menus": top_selling,
        "worst_dropping_menus": worst_dropping,
        "day_analysis": day_analysis
    }

    return {
        "final_report": report_dict,
        "execution_logs": [log, f"✅ [Analyze] 수치 근거 분석 완료 (추세: {trend:+.1f}%)"]
    }

async def save_report_node(state: ReportState):
    """최종 리포트를 DB에 저장하는 노드"""
    log = "💾 [Save] 분석 결과 DB 저장 중"
    report_dict = state["final_report"]

    # 메트릭 및 소스 정보를 risk_assessment 내부에 병합하여 영구 저장
    risk_info = report_dict.get('risk_assessment', {})
    risk_info['metrics'] = report_dict.get('metrics')
    risk_info['data_evidence'] = report_dict.get('data_evidence')
    risk_info['source_data'] = report_dict.get('source_data')  # 원본 데이터 추가 저장

    db_report = StoreReport(
        store_id=state["store_id"],
        report_date=date.today(),
        report_type="AI_GRAPH_REPORT",
        summary=report_dict['summary'],
        marketing_strategy=report_dict['marketing_strategy'],
        operational_improvement=report_dict['operational_improvement'],
        risk_assessment=risk_info
    )

    with SessionLocal() as session:
        session.query(StoreReport).filter_by(
            store_id=state["store_id"],              
            report_date=date.today()).delete()
        session.add(db_report)
        session.commit()

    return {
        "execution_logs": [log, "🏁 [Complete] 프로세스 종료"]
    }

def create_report_graph():
    workflow = StateGraph(ReportState)
    workflow.add_node("fetch_data", fetch_data_node)
    workflow.add_node("analyze_data", analyze_data_node)
    workflow.add_node("save_report", save_report_node)

    workflow.set_entry_point("fetch_data")
    workflow.add_edge("fetch_data", "analyze_data")
    workflow.add_edge("analyze_data", "save_report")
    workflow.add_edge("save_report", END)

    return workflow.compile()
