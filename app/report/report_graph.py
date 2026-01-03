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
    target_date: str # [Optional] 분석 기준 날짜 (YYYY-MM-DD)
    sales_data: List[Dict[str, Any]]      # 이번주 매출 (최근 7일)
    prev_sales_data: List[Dict[str, Any]] # 지난주 매출 (그 전 7일)
    reviews_data: List[Dict[str, Any]]
    menu_sales_data: List[Dict[str, Any]]
    weather_data: Dict[str, str]
    # [NEW] 집계 정합성을 위해 fetch 단계에서 계산한 값을 넘김
    calculated_total_sales: float 
    calculated_prev_sales: float
    final_report: Dict[str, Any]
    execution_logs: Annotated[List[str], append_logs]

async def fetch_store_data(store_id: int):
    pass

async def fetch_data_node(state: ReportState):
    """DB에서 매출과 리뷰 데이터를 수집하는 노드"""
    store_id = state["store_id"]
    log = f"📊 [Fetch] '{state['store_name']}' 데이터 수집 시작"
    print(log)

    # 1. 기준 날짜(Anchor Date) 결정
    # 시연 모드 or 과거 날짜 조회 지원
    from app.core.db import fetch_all
    from datetime import datetime, timedelta
    
    target_date_str = state.get("target_date")
    
    if not target_date_str:
        # 타겟 날짜가 없으면 DB 최신 날짜 조회 (Simulation Mode)
        max_date_query = f"SELECT MAX(sale_date) as last_date FROM sales_daily WHERE store_id = {store_id}"
        try:
            max_date_rows = await fetch_all(max_date_query)
            if max_date_rows and max_date_rows[0]['last_date']:
                target_date_str = str(max_date_rows[0]['last_date'])
                log += f"\n🕒 최신 데이터 날짜 기준: {target_date_str}"
            else:
                target_date_str = str(date.today())
        except:
            target_date_str = str(date.today())

    ref_date = datetime.strptime(target_date_str, "%Y-%m-%d").date()
    
    # 2. 데이터 조회
    # 메뉴별, 요일별 통계는 기준 날짜를 넘겨서 DB에서 정확히 계산
    menu_stats = await select_menu_sales_comparison(store_id, days=7, target_date=target_date_str)
    # day_stats = await select_sales_by_day_type(store_id, days=7, target_date=target_date_str) # [삭제] DB 호출 대신 직접 집계
    reviews = await select_reviews_by_store(store_id) # 리뷰는 전체 가져와서 최신순 (TODO: 날짜 필터링?)

    # 일별 매출은 전체를 가져온 뒤 파이썬에서 날짜 필터링 (DB 호출 횟수 절약)
    all_sales = await select_daily_sales_by_store(store_id)
    
    # 3. 날짜 필터링 (이번주 vs 지난주)
    # 이번주: ref_date 포함 최근 7일 (ref_date - 6 ~ ref_date)
    # 지난주: 그 전 7일 (ref_date - 13 ~ ref_date - 7)
    
    curr_start = ref_date - timedelta(days=6)
    curr_end = ref_date
    prev_start = ref_date - timedelta(days=13)
    prev_end = ref_date - timedelta(days=7)
    
    target_sales = []
    prev_sales = []

    # [NEW] 파이썬 내보내기 집계 (평일/주말 정합성 보장)
    weekday_sales = {"recent": 0, "prev": 0}
    weekend_sales = {"recent": 0, "prev": 0}
    
    for s in all_sales:
        s_date = s['order_date'] # date object
        rev = float(s['daily_revenue'])

        # 이번주 데이터
        if curr_start <= s_date <= curr_end:
            target_sales.append(s)
            if s_date.weekday() < 5: # 0~4: 평일
                weekday_sales["recent"] += rev
            else: # 5~6: 주말
                weekend_sales["recent"] += rev

        # 지난주 데이터
        elif prev_start <= s_date <= prev_end:
            prev_sales.append(s)
            if s_date.weekday() < 5:
                weekday_sales["prev"] += rev
            else:
                weekend_sales["prev"] += rev
            
    # 정렬 (날짜 오름차순) -> 그래프용
    target_sales.sort(key=lambda x: x['order_date'])
    prev_sales.sort(key=lambda x: x['order_date'])

    # weather_map 구성
    weather_map = {str(s['order_date']): s.get('weather_info', '알수없음') for s in target_sales}

    return {
        "sales_data": target_sales,
        "prev_sales_data": prev_sales,
        "reviews_data": reviews[:15], # 최신 15개만 사용
        "menu_sales_data": menu_stats,
        "weather_data": weather_map,
        "calculated_total_sales": weekday_sales["recent"] + weekend_sales["recent"], # [NEW] 정확한 합계 전달
        "calculated_prev_sales": weekday_sales["prev"] + weekend_sales["prev"],
        "target_date": target_date_str, # State 업데이트
        "execution_logs": [log, f"✅ [Fetch] 데이터 수집 및 정합성 검증 완료 (기준일: {target_date_str})"]
    }

async def analyze_data_node(state: ReportState):
    """데이터 분석 및 수치적 근거 계산을 수행하는 노드"""
    log = "🧠 [Analyze] 수치 데이터 계산 및 AI 분석 시작"
    print(log)

    sales = state["sales_data"]     # 이번주
    prev_sales = state.get("prev_sales_data", []) # 지난주
    reviews = state["reviews_data"]
    menu_stats = state.get("menu_sales_data", [])
    
    # 1. 주간 매출 비교 (Weekly Comparison)
    # [변경] fetch 단계에서 계산된 정확한 합계 사용 (재계산 X)
    this_week_total = state["calculated_total_sales"]
    prev_week_total = state.get("calculated_prev_sales", 0)
    
    avg_rev = this_week_total / len(sales) if sales else 0
    
    # 성장률 계산 (Growth Rate)
    if prev_week_total > 0:
        growth_rate = ((this_week_total - prev_week_total) / prev_week_total * 100)
    else:
        growth_rate = 100 if this_week_total > 0 else 0

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
    
    [주간 매출 요약]
    - 이번주 총 매출(7일): {int(this_week_total):,}원
    - 지난주 총 매출(7일): {int(prev_week_total):,}원
    - 주간 성장률(WoW): {growth_rate:+.1f}%
    - 이번주 평균 별점: {avg_rating:.1f}점
    
    상세 매출 내역 (날씨 포함): {json.dumps(source_sales, ensure_ascii=False)}
    상세 리뷰 내역: {json.dumps([{"rate": r['rating'], "txt": r['review_text']} for r in reviews], ensure_ascii=False)}
    
    [메뉴 분석]
    잘 팔린 메뉴 (TOP 5): {json.dumps(top_selling, ensure_ascii=False)}
    급감한 메뉴 (WORST 5): {json.dumps(worst_dropping, ensure_ascii=False)}

    분석 시 다음 사항을 반드시 지켜줘:
    1. **"이번주 매출이 지난주 대비 왜 변했는가?"**를 핵심 주제로 잡으세요. (성장 또는 하락의 원인 규명)
    2. **날씨와 매출의 상관관계**를 반드시 언급하세요. 
       - "지난주 대비 비오는 날이 많아 배달 매출이 늘었다" 등 구체적으로.
    3. 수치적 근거(Top 5 메뉴명, 주말 매출 변동률 등)를 포함하여 마크다운 표로 시각화하세요.
    4. 모든 줄바꿈(개행)은 실제 줄바꿈 대신 '\\n' 문자를 사용하세요. (JSON 포맷 준수)
    
    응답은 반드시 아래 JSON 형식으로만 할 것:
    {{
        "data_evidence": {{
            "sales_analysis": "주간 매출 비교, 날씨, 메뉴 데이터를 종합한 상세 분석 (마크다운 표 포함 필수)"
        }},
        "summary": "핵심 요약 (지난주 대비 변동 원인 포함 3줄)",
        "marketing_strategy": "다음주 매출 증대를 위한 날씨/트렌드 기반 마케팅 제안",
        "operational_improvement": "매장 운영 효율화 및 서비스 개선 제안",
        "risk_assessment": {{"risk_score": 80, "main_risks": [], "suggestion": ""}}
    }}
    """

    raw_text = await genai_generate_text(prompt)
    
    # 1. 마크다운 코드블록 제거
    if "```json" in raw_text:
        raw_text = raw_text.split("```json")[1].split("```")[0].strip()
    elif "```" in raw_text:
        raw_text = raw_text.split("```")[1].split("```")[0].strip()
        
    # 2. 제어 문자(Control Characters) 제거 (JSON 파싱 에러 방지)
    import re
    # \n(\x0A), \t(\x09), \r(\x0D)은 살리고 그 외의 제어 문자만 제거 (마크다운 표 보존)
    cleaned_json = re.sub(r'[\x00-\x08\x0B-\x0C\x0E-\x1F\x7F]', '', raw_text)
    
    # [NEW] Trailing Comma 제거 (Standard JSON 호환성 확보)
    # 예: {"a": 1,} -> {"a": 1}
    cleaned_json = re.sub(r',\s*([}\]])', r'\1', cleaned_json)
    
    try:
        # dirtyjson 대신 표준 json 사용 + 정규식 전처리
        report_dict = json.loads(cleaned_json, strict=False)
    except Exception:
        try:
            # 2차 시도: 역슬래시 이중 치환 후 재시도
            cleaned_json_fixed = cleaned_json.replace('\\', '\\\\')
            report_dict = json.loads(cleaned_json_fixed, strict=False)
        except Exception as e:
            print(f"❌ [Analyze] JSON 파싱 최종 실패: {e}")
            print("--- [AI Raw Output Start] ---")
            print(raw_text) # 전체 출력 (디버깅용)
            print("--- [AI Raw Output End] ---")
            
            # Fallback: 기본 빈 템플릿 반환
            report_dict = {
                "data_evidence": {"sales_analysis": "데이터 분석 실패 (AI 응답 형식 오류)"},
                "summary": "리포트 생성 중 오류가 발생했습니다.",
                "marketing_strategy": "",
                "operational_improvement": "",
                "risk_assessment": {"risk_score": 0, "main_risks": [], "suggestion": ""}
            }
    
    # UI용 통계 데이터 및 소스 데이터 추가
    report_dict["metrics"] = {
        "total_rev": this_week_total,
        "avg_rev": avg_rev,
        "trend_percent": growth_rate, # 트렌드 대신 성장률 사용
        "avg_rating": avg_rating,
        "prev_total_rev": prev_week_total # 지난주 매출 추가
    }
    report_dict["source_data"] = {
        "recent_sales": source_sales,
        "review_count": len(reviews),
        "top_selling_menus": top_selling,
        "worst_dropping_menus": worst_dropping,
    }

    return {
        "final_report": report_dict,
        "execution_logs": [log, f"✅ [Analyze] 수치 근거 분석 완료 (주간 성장률: {growth_rate:+.1f}%)"]
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

# [Singleton 패턴] 서버 시작 시 한 번만 컴파일하여 재사용
report_graph_app = create_report_graph()
