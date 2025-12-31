"""
프랜차이즈 가맹점 문의 응답 에이전트 (LangGraph)

Router 기반 병렬 처리:
1. 질문 의도 분류 (매출/매뉴얼/정책)
2. 카테고리별 데이터 소스 검색 (SQL/RAG)
3. 종합 답변 생성
4. DB 저장
"""

from typing import TypedDict, List, Dict, Any, Annotated
from langgraph.graph import StateGraph, END
from app.clients.genai import genai_generate_text
from app.core.db import fetch_all
from app.inquiry.inquiry_service import save_inquiry
import json
from datetime import datetime, timedelta

# ===== 데이터 검색용 파라미터 추출 함수 =====
async def extract_search_params(question: str):
    """
    질문에서 검색 조건(지점명, 기간 등)을 추출
    """
    prompt = f"""
    질문을 분석하여 데이터 검색 조건을 JSON으로 추출하세요.
    
    질문: "{question}"
    
    [추출 규칙]
    1. target_store_name: 질문에 '강남점', '해운대' 등 지점명이나 '서울', '부산' 등 지역명이 있으면 추출 (없으면 null)
    2. days: 조회 기간 (일수). 
       - "어제" -> 1
       - "지난주", "일주일" -> 7
       - "최근 3일" -> 3
       - "이번달", "30일" -> 30
       - 언급 없으면 기본값 7
    3. need_reviews: 리뷰 데이터가 필요한지 여부 (true/false)

    [출력 예시]
    {{
        "target_store_name": "해운대",
        "days": 7,
        "need_reviews": true
    }}
    """
    try:
        response = await genai_generate_text(prompt)
        # JSON 파싱 트릭 (마크다운 코드블럭 제거)
        clean_text = response.replace("```json", "").replace("```", "").strip()
        parsed = json.loads(clean_text)
        if isinstance(parsed, dict):
            return parsed
        else:
            return {"target_store_name": None, "days": 7, "need_reviews": False}
    except:
        return {"target_store_name": None, "days": 7, "need_reviews": False}


# ===== Step 1: State 정의 =====
class InquiryState(TypedDict):
    """에이전트 상태 관리"""
    store_id: int
    question: str
    category: str  # Router가 분류한 카테고리
    
    # 각 노드에서 수집한 데이터
    sales_data: Dict[str, Any]
    manual_data: List[str]
    policy_data: List[str]
    
    # 최종 결과
    final_answer: str
    inquiry_id: int
    diagnosis_result: str # 새로 추가 (진단 결과 요약)


# ===== Step 2: Router Node (질문 분류) =====
async def router_node(state: InquiryState) -> InquiryState:
    """
    질문을 분석하여 카테고리 분류
    - sales: 매출, 성과, 통계 관련
    - manual: 기기 사용법, 레시피, 기술 지원
    - policy: 운영 규정, 고객 응대, 본사 정책
    """
    question = state["question"]
    
    prompt = f"""
다음 질문을 분석하여 카테고리를 정확히 하나만 선택하세요.

질문: {question}

카테고리:
- sales: 매출, 판매량, 통계, 순 등 숫자 데이터 관련
- manual: 기기 사용법, 청소 방법, 고장 수리
- policy: 운영 규정, 고객 응대, 환불 정책, 복장 규정

JSON 형식으로만 답변:
{{"category": "sales|manual|policy"}}
"""
    
    result = await genai_generate_text(prompt)
    parsed = json.loads(result)
    
    state["category"] = parsed["category"]
    print(f"🔍 [Router] 질문 카테고리: {parsed['category']}")
    
    return state


# ===== Step 3: Diagnosis Node (상세 메뉴/원인 분석) =====
async def diagnosis_node(state: InquiryState) -> InquiryState:
    """매출 등락의 원인을 '메뉴 단위'로 상세 분석 (Deep Dive Analysis)"""
    if state["category"] != "sales":
        return state
        
    print(f"🕵️‍♀️ [Diagnosis] 상세 원인 분석 시작: {state['question']}")
    
    # 1. 검색 조건 추출
    params = await extract_search_params(state['question'])
    target_store_id = state["store_id"]
    days = params.get("days", 7)
    
    # [Smart Store Matcher] 로직은 유지 (생략 가능하면 생략하되, 기존 로직 보호를 위해 store_id 확보 중요)
    # ... (지점 매칭 로직은 위에서 이미 완료되었다고 가정하고 생략하거나 간단히 유지) ...

    # 2. 날짜 설정 (최근 데이터 기준)
    # (실제 서비스에선 datetime.now() 사용, 여기선 시뮬레이션용 하드코딩 유지 가능성 있음)
    start_date_str = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
    
    # =========================================================================
    # [CORE CHANGE] 단순 일별 집계 -> '메뉴별/카테고리별 상세 분석'으로 전환
    # =========================================================================
    
    # (1) 많이 팔린 메뉴 & 안 팔린 메뉴 분석 (기간 자동 확장 로직)
    async def fetch_menu_stats(search_days):
        s_date = (datetime.now() - timedelta(days=search_days)).strftime("%Y-%m-%d")
        q = f"""
            SELECT 
                m.name as menu_name,
                m.category,
                COALESCE(SUM(oi.quantity), 0) as total_qty,
                COALESCE(SUM(oi.price * oi.quantity), 0) as total_rev
            FROM order_items oi
            JOIN orders o ON oi.order_id = o.order_id
            JOIN menus m ON oi.menu_id = m.menu_id
            WHERE o.store_id = {target_store_id}
              AND o.order_date >= '{s_date}'
            GROUP BY m.name, m.category
            ORDER BY total_qty DESC
        """
        try:
            return await fetch_all(q), s_date
        except Exception as e:
            print(f"⚠️ 상세 쿼리 실패({e})")
            return [], s_date

    # 1차 시도 (요청된 기간)
    menu_rows, real_start_date = await fetch_menu_stats(days)
    
    # 데이터가 없으면 기간을 늘려서 재시도 (7일 -> 30일 -> 90일)
    if not menu_rows and days < 30:
        print(f"⚠️ [Diagnosis] {days}일 데이터 없음 -> 30일로 확장 재검색")
        days = 30
        menu_rows, real_start_date = await fetch_menu_stats(30)
        
    if not menu_rows:
        print(f"❌ [Diagnosis] 30일 데이터도 없음 -> 분석 불가")
        state["sales_data"] = {
            "summary_text": f"⚠️ 최근 {days}일간 해당 지점({state['store_name'] if state.get('store_name') else target_store_id})의 주문 데이터가 없습니다.\n데이터가 입력되었는지 확인해주세요.",
            "diagnosis_result": "데이터 없음"
        }
        return state

    # (2) 데이터 가공 (Pandas 활용)
    import pandas as pd
    df = pd.DataFrame(menu_rows)
    
    # 1. Top 5 Best Sellers
    top_5 = df.head(5).to_dict('records')
    
    # 2. Worst 5 (판매량 0인건 안나올 수 있으니 하위권 조회)
    worst_5 = df.sort_values(by='total_qty').head(5).to_dict('records')
    
    # 3. 카테고리별 매출 비중
    cat_group = df.groupby('category')['total_rev'].sum().reset_index()
    category_summary = cat_group.to_dict('records')
    
    # 4. 전체 요약 통계
    total_revenue = df['total_rev'].sum()
    total_qty = df['total_qty'].sum()
    
    # (3) [Insight Generation] 분석 텍스트 생성
    # LLM에게 덩어리로 던져줄 텍스트 구성
    analysis_context = f"=== 🕵️ 매장 상세 분석 리포트 (기간: {real_start_date} ~ 현재) ===\n"
    analysis_context += f"지점ID: {target_store_id}\n"
    analysis_context += f"총 매출: {total_revenue:,.0f}원 / 총 판매량: {total_qty}건\n\n"
    
    analysis_context += "🔥 [Best Selling - 인기 메뉴 Top 5]\n"
    for i, item in enumerate(top_5):
        analysis_context += f"{i+1}. {item['menu_name']} ({item['category']}): {item['total_qty']}개 판매 ({item['total_rev']:,.0f}원)\n"
        
    analysis_context += "\n❄️ [Low Performance - 부진 예상 메뉴]\n"
    for item in worst_5:
        analysis_context += f"- {item['menu_name']}: 단 {item['total_qty']}개 판매\n"
        
    analysis_context += "\n🍰 [Category Share - 카테고리별 매출]\n"
    for item in category_summary:
        share = (item['total_rev'] / total_revenue * 100) if total_revenue > 0 else 0
        analysis_context += f"- {item['category']}: {item['total_rev']:,.0f}원 ({share:.1f}%)\n"
    
    analysis_context += "\n[Data Source Verification]\n"
    analysis_context += "위 데이터는 실제 POS/주문 시스템에서 집계된 'Fact'입니다. 이 수치를 기반으로만 답변하세요."

    # state에 저장
    state["sales_data"] = {
        "summary_text": analysis_context, # 상세 분석 내용
        "raw_top_5": top_5,
        "diagnosis_result": f"총 매출 {total_revenue:,.0f}원 (상세 분석 완료)"
    }
    
    print(f"   ✅ 상세 분석 완료: Best({top_5[0]['menu_name']}), Total({total_revenue:,.0f})")
    
    return state


# ===== Step 4: Manual RAG Node (매뉴얼 검색) =====
async def manual_node(state: InquiryState) -> InquiryState:
    """매뉴얼 DB에서 관련 문서 검색 (Vector Search)"""
    if state["category"] != "manual":
        return state
    
    question = state["question"]
    
    # OpenAI Embeddings로 질문 벡터화
    from langchain_openai import OpenAIEmbeddings
    embeddings_model = OpenAIEmbeddings(model="text-embedding-3-small")
    question_vector = embeddings_model.embed_query(question)
    
    # pgvector 유사도 검색 (코사인 거리 기준 Top 3)
    # distance가 0에 가까울수록 유사함
    query = f"""
    SELECT title, content, category,
           embedding <=> '{question_vector}'::vector AS distance
    FROM manuals
    ORDER BY distance
    LIMIT 3
    """
    
    rows = await fetch_all(query)
    
    # 검색 결과 및 최소 거리 저장
    min_distance = 1.0 # 기본값 (불일치)
    if rows:
        min_distance = min([r['distance'] for r in rows])
        
    state["manual_data"] = [
        f"[{row['title']}] (유사도: {1 - row['distance']:.2f})\n{row['content']}"
        for row in rows
    ]
    # 상태에 검색 품질 점수(거리) 저장 (임시 필드 활용 또는 state 확장 필요하지만, 여기선 meta dict 같은걸 쓰거나 간단히 전역 변수처럼 처리)
    # 여기서는 state에 직접 저장하기 위해 TypedDict를 무시하고 런타임에 추가하거나, 미리 정의해야함.
    # 편의상 sales_data 내부에 메타데이터로 숨기거나, 새로운 필드를 추가하는게 정석.
    # 간단히 existing field인 'diagnosis_result'를 다용도 메타 필드로 활용해 꼼수를 부리거나, 
    # 정석대로 State 클래스 수정이 필요함. 여기선 State 수정 없이 sales_data 딕셔너리에 'search_quality' 키를 넣어 전달.
    
    if "search_meta" not in state: state["search_meta"] = {}
    state["search_meta"] = {"min_distance": min_distance, "source": "manual_db"}
    
    print(f"📖 [Manual] 검색 완료 (Min Distance: {min_distance:.4f})")
    return state


# ===== Step 5: Policy RAG Node (정책 검색) =====
async def policy_node(state: InquiryState) -> InquiryState:
    """운영 정책 매뉴얼 검색 (Policies 테이블 조회)"""
    if state["category"] != "policy":
        return state
    
    question = state["question"]
    
    from langchain_openai import OpenAIEmbeddings
    embeddings_model = OpenAIEmbeddings(model="text-embedding-3-small")
    question_vector = embeddings_model.embed_query(question)
    
    query = f"""
    SELECT title, content, category,
           embedding <=> '{question_vector}'::vector AS distance
    FROM policies
    ORDER BY distance
    LIMIT 3
    """
    
    rows = await fetch_all(query)
    
    min_distance = 1.0
    if rows:
        min_distance = min([r['distance'] for r in rows])
        
    state["policy_data"] = [
        f"[{row['title']}] (유사도: {1 - row['distance']:.2f})\n{row['content']}"
        for row in rows
    ]
    
    state["search_meta"] = {"min_distance": min_distance, "source": "policy_db"}
    
    print(f"📜 [Policy] 검색 완료 (Min Distance: {min_distance:.4f})")
    return state


# ===== Step 5.5: Web Search Node (외부 검색 - Google Grounding) =====
async def web_search_node(state: InquiryState) -> InquiryState:
    """내부 DB 검색 실패 시 외부 웹 검색 수행 (Google Gemini Grounding)"""
    question = state["question"]
    print(f"🌐 [Google Grounding] 내부 문서 부족 -> 구글 검색 수행: {question}")
    
    try:
        from app.clients.genai import genai_generate_with_grounding
        
        # 구글 검색 Grounding을 통한 답변 생성
        grounded_response = await genai_generate_with_grounding(question)
        
        # 결과 저장
        state["manual_data"] = [f"[Google 검색 결과 기반 답변]\n{grounded_response}"]
        state["search_meta"] = {"source": "web_search", "min_distance": 0.0}
        
    except Exception as e:
        print(f"❌ Google Grounding 실패: {e}")
        state["manual_data"] = [f"외부 검색 연결에 실패했습니다. (Error: {str(e)})"]
        
    return state


# ===== Step 6: Answer Synthesis Node (답변 생성) =====
async def answer_node(state: InquiryState) -> InquiryState:
    """수집한 데이터를 바탕으로 최종 답변 생성"""
    question = state["question"]
    category = state["category"]
    
    # 카테고리별 컨텍스트 구성
    context = ""
    if category == "sales":
        context = f"매출 데이터:\n{json.dumps(state.get('sales_data', {}), ensure_ascii=False, indent=2)}"
    elif category == "manual":
        context = "\n\n".join(state.get("manual_data", []))
    elif category == "policy":
        context = "\n\n".join(state.get("policy_data", []))
    
    prompt = f"""
당신은 프랜차이즈 본사의 친절한 AI 매니저입니다.
질문에 대해 아래 자료를 바탕으로 답변하세요.

**중요: 반드시 아래 JSON 형식을 엄격히 지켜서 답변하세요.**

[Category: sales 일 때]
{{
  "type": "sales",
  "summary": "매출 추이와 특이사항에 대한 친절한 요약 멘트 (3문장 이내)",
  "data": [
      {{ "date": "YYYY-MM-DD", "sales": 150000, "orders": 25 }},
      ... (데이터 그대로 복사)
  ]
}}

[Category: manual 또는 policy 일 때]
{{
  "type": "general",
  "title": "관련 매뉴얼/규정 제목",
  "content": "핵심 내용 요약 및 상세 설명 (Markdown 형식, 줄바꿈은 \\n 사용)"
}}

질문: {question}
카테고리: {category}

참고 자료:
{context}
"""
    
    answer = await genai_generate_text(prompt)
    state["final_answer"] = answer
    
    print(f"✅ [Answer] 답변 생성 완료 ({len(answer)}자)")
    return state


# ===== Step 7: Save Node (DB 저장) =====
async def save_node(state: InquiryState) -> InquiryState:
    """질문과 답변을 DB에 저장"""
    inquiry_id = save_inquiry(
        store_id=state["store_id"],
        category=state["category"],
        question=state["question"],
        answer=state["final_answer"]
    )
    
    state["inquiry_id"] = inquiry_id
    print(f"💾 [Save] DB 저장 완료 (ID: {inquiry_id})")
    
    return state


# ===== Step 6: Answer Synthesis Node (답변 생성 - Analytical) =====
async def answer_node_v2(state: InquiryState) -> InquiryState:
    """수집한 데이터를 바탕으로 '표(Table)' 중심의 심층 분석 보고서 생성"""
    question = state["question"]
    category = state["category"]
    
    # 1. 컨텍스트 구성
    context_text = ""
    if category == "sales":
        if "sales_data" in state and state["sales_data"]:
             context_text = state["sales_data"].get("summary_text", "")
    else:
        # manual / policy 데이터 통합
        docs = state.get("manual_data", []) + state.get("policy_data", [])
        context_text = "\n\n".join(docs)
    
    # 2. 시스템 프롬프트 (Markdown Table 강제 -> 상황에 따라 유연하게)
    system_prompt = (
        "당신은 프랜차이즈 수석 데이터 분석가(Chief Analyst)입니다. "
        "제공된 [분석용 데이터]를 기반으로 팩트에 입각한 인사이트를 제공하세요.\n\n"
        
        "[작성 규칙 - Strict Rules]\n"
        "1. **No Hallucination (거짓말 금지)**: [분석용 데이터]에 없는 내용은 절대 지어내지 마세요. 데이터가 없으면 솔직하게 '데이터가 없습니다'라고 말하세요.\n"
        "2. **Markdown Table**: 데이터가 충분히 존재할 때만 표를 작성하세요. 데이터가 없는데 억지로 표를 만들지 마세요.\n"
        "3. **화폐 단위**: 반드시 **원(KRW)**을 사용하세요. (달러/USD 사용 금지)\n"
        "4. **메뉴 이름**: '커피', '빵' 같이 뭉뚱그리지 말고, 데이터에 있는 정확한 메뉴명(예: 아이스 아메리카노)을 사용하세요.\n"
        "5. **원인 분석**: 추측이 아니라 데이터에 근거한 분석만 수행하세요."
    )
    
    # 메시지 구성
    from langchain_core.messages import SystemMessage, HumanMessage
    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=f"질문: {question}\n\n[분석용 데이터]\n{context_text}")
    ]
    
    # 3. LLM 호출
    from langchain_openai import ChatOpenAI
    llm = ChatOpenAI(model="gpt-4o", temperature=0)
    response = await llm.ainvoke(messages)
    
    # 4. 결과 저장 (JSON 파싱 로직 제거 -> 순수 텍스트 저장)
    state["final_answer"] = response.content
    
    print(f"✅ [Analyst Answer] 분석 보고서 생성 완료")
    return state


# ===== Step 7: Save Node (DB 저장) =====
async def save_node(state: InquiryState) -> InquiryState:
    """질문과 답변을 DB에 저장"""
    inquiry_id = save_inquiry(
        store_id=state["store_id"],
        category=state["category"],
        question=state["question"],
        answer=state["final_answer"]
    )
    
    state["inquiry_id"] = inquiry_id
    print(f"💾 [Save] DB 저장 완료 (ID: {inquiry_id})")
    
    return state


def create_inquiry_graph():
    """
    LangGraph 생성 - Hybrid Search & Fallback Logic 적용
    """
    graph = StateGraph(InquiryState)
    
    # 노드 등록
    graph.add_node("router", router_node)
    graph.add_node("sales", diagnosis_node) # 이름은 sales로 유지하되 함수는 diagnosis로 교체
    graph.add_node("manual", manual_node)
    graph.add_node("policy", policy_node)
    graph.add_node("web_search", web_search_node) # ✨ 신규 노드
    graph.add_node("answer", answer_node_v2) # V2 사용
    graph.add_node("save", save_node)
    
    # 엔트리 포인트
    graph.set_entry_point("router")
    
    # 🔥 핵심: Conditional Edge (에이전트가 자율적으로 경로 선택)
    def route_question(state: InquiryState) -> str:
        """
        Router 노드의 분류 결과에 따라 다음 실행할 노드를 결정
        
        Returns:
            "sales" | "manual" | "policy"
        """
        category = state["category"]
        print(f"🔀 [Conditional Edge] '{category}' 노드로 라우팅")
        return category
    
    # Router → 조건부 분기 (3개 중 1개만 실행)
    graph.add_conditional_edges(
        "router",
        route_question,
        {
            "sales": "sales",
            "manual": "manual",
            "policy": "policy"
        }
    )
    
    # ✨ 검색 결과 평가 및 분기 로직 (핵심)
    def evaluate_search_result(state: InquiryState) -> str:
        """검색 품질을 평가하여 Web Search 여부 결정"""
        meta = state.get("search_meta", {})
        min_dist = meta.get("min_distance", 1.0)
        
        # [Tuning] 임계값 완화 (0.45 -> 0.65)
        # Distance가 0.65(유사도 35%) 이하여도 내부 문서를 믿고 답변하도록 설정
        THRESHOLD = 0.65
        
        if min_dist > THRESHOLD:
            print(f"⚠️ [Search Check] 문서 유사도 매우 낮음 ({min_dist:.4f} > {THRESHOLD}) -> Web Search 전환")
            return "retry_web"
        else:
            print(f"✅ [Search Check] 내부 문서 채택 (Distance: {min_dist:.4f})")
            return "proceed"

    # Manual/Policy -> 평가 -> (Web Search OR Answer)
    graph.add_conditional_edges(
        "manual",
        evaluate_search_result,
        {
            "proceed": "answer",
            "retry_web": "web_search"
        }
    )
    
    graph.add_conditional_edges(
        "policy",
        evaluate_search_result,
        {
            "proceed": "answer",
            "retry_web": "web_search"
        }
    )
    
    # Sales는 Web Search 불필요 (데이터 분석이므로)
    graph.add_edge("sales", "answer")
    
    # Web Search -> Answer
    graph.add_edge("web_search", "answer")
    
    # Answer → Save → END
    graph.add_edge("answer", "save")
    graph.add_edge("save", END)
    
    return graph.compile()


# ===== [Phase 1] 검색 및 진단 실행 함수 =====
async def run_search_check(store_id: int, question: str) -> Dict[str, Any]:
    """
    1단계: 질문 분류 -> DB 검색 -> 유사도 평가 결과 반환
    """
    # 1. State 초기화
    state = InquiryState(
        store_id=store_id,
        question=question,
        category="",
        sales_data={},
        manual_data=[],
        policy_data=[],
        final_answer="",
        inquiry_id=0,
        diagnosis_result=""
    )
    
    # 2. Router 실행
    state = await router_node(state)
    category = state["category"]
    
    # 3. 카테고리별 검색 실행
    top_doc = None
    min_dist = 1.0 # 기본값 초기화
    search_results = []
    
    if category == "sales":
        # 매출은 사용자가 선택할 필요 없이 무조건 데이터 분석
        state = await diagnosis_node(state)
        # 매출은 유사도 개념이 아니므로 100% 신뢰로 간주
        min_dist = 0.0
        top_doc = {"title": "매출 데이터 분석", "content": state["sales_data"]["summary_text"]}
        
    elif category == "manual":
        # 매뉴얼 검색 실행
        state = await manual_node(state)
        docs = state.get("manual_data", [])
        
        # 메타데이터 추출 (manual_node가 변경된 상태라 가정)
        meta = state.get("search_meta", {})
        min_dist = meta.get("min_distance", 1.0)
        
        if docs:
            # 첫 번째 문서 파싱: "[제목] (유사도: 0.xx)\n내용"
            first_line = docs[0].split("\n")[0]
            content_preview = docs[0][len(first_line)+1:]
            top_doc = {"title": first_line, "content": content_preview[:200] + "..."}
            search_results = docs # 전체 결과 저장해서 전달

    elif category == "policy":
        # 정책 검색 실행
        state = await policy_node(state)
        docs = state.get("policy_data", [])
        
        meta = state.get("search_meta", {})
        min_dist = meta.get("min_distance", 1.0)
        
        if docs:
            first_line = docs[0].split("\n")[0]
            content_preview = docs[0][len(first_line)+1:]
            top_doc = {"title": first_line, "content": content_preview[:200] + "..."}
            search_results = docs

    return {
        "category": category,
        "min_distance": min_dist,
        "similarity_score": round((1 - min_dist) * 100, 1), # 0~100 점수
        "top_document": top_doc,
        "context_data": search_results if category != "sales" else [] # 매출 데이터는 별도로 처리되므로 context에서 제외하거나 포함 가능
    }


# ===== [Phase 2] 최종 답변 생성 스트리밍 =====
async def run_final_answer_stream(store_id: int, question: str, category: str, mode: str, context_data: list):
    """
    2단계: 사용자 선택(DB/Web)에 따라 답변 생성
    mode: 'db' (기존 데이터 사용) | 'web' (웹 검색 수행)
    """
    
    # 가상 State 복원
    state = InquiryState(
        store_id=store_id, 
        question=question, 
        category=category,
        sales_data={}, manual_data=[], policy_data=[], final_answer="", inquiry_id=0, diagnosis_result=""
    )
    
    # 매출은 이미 1단계에서 분석이 끝났어야 하나, 
    # 흐름상 여기서 다시 돌리거나 캐시된 데이터를 받아야 함.
    # 간단하게 구현하기 위해 매출은 다시 diagnosis_node를 태우고,
    # 나머지는 context_data를 활용하거나 web search를 함.
    
    yield json.dumps({"step": "init", "message": f"🚀 {mode.upper()} 모드로 답변 생성 시작..."}) + "\n"

    if category == "sales":
        # 매출은 Web Search 대상이 아님 -> 바로 분석
        yield json.dumps({"step": "sales", "message": "📉 매출 데이터 분석 중..."}) + "\n"
        state = await diagnosis_node(state)
        
        # 진단 결과 전송
        details = {
            "type": "analysis", 
            "summary": state["sales_data"].get("diagnosis_result"),
            "sales_summary": state["sales_data"].get("summary_text", "")[:100] + "..."
        }
        yield json.dumps({"step": "sales", "message": "✅ 분석 완료", "details": details}) + "\n"
        
    else:
        # manual / policy
        if mode == "web":
            # 웹 검색 노드 실행
            yield json.dumps({"step": "web_search", "message": "🌐 외부 웹 검색 수행 중..."}) + "\n"
            state = await web_search_node(state)
            
            # 웹 검색 결과 전송
            web_res = state["manual_data"][0] if state["manual_data"] else ""
            details = {"type": "web_result", "content": web_res}
            yield json.dumps({"step": "web_search", "message": "✅ 외부 정보 수집 완료", "details": details}) + "\n"
            
        else:
            # DB 모드: 클라이언트가 보낸 context_data(검색 결과)를 state에 복원
            # 1단계에서 찾은걸 그대로 씀
            key = "manual_data" if category == "manual" else "policy_data"
            state[key] = context_data
            
            yield json.dumps({"step": "check", "message": "📚 내부 DB 데이터 활용"}) + "\n"

    # 최종 답변 생성
    yield json.dumps({"step": "answer", "message": "✍️ 답변 작성 중..."}) + "\n"
    state = await answer_node_v2(state)
    
    # DB 저장
    yield json.dumps({"step": "save", "message": "💾 기록 저장 중..."}) + "\n"
    state = await save_node(state)
    
    yield json.dumps({
        "step": "done",
        "message": "처리가 완료되었습니다.",
        "final_answer": state["final_answer"],
        "category": state["category"]
    }) + "\n"
 