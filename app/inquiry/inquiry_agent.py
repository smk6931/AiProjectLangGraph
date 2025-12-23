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
    1. target_store_name: 질문에 '강남점', '해운대' 등 지점명이 있으면 추출 (없으면 null)
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
        return json.loads(clean_text)
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
- sales: 매출, 판매량, 통계, 순위 등 숫자 데이터 관련
- manual: 기기 사용법, 청소 방법, 레시피, 고장 수리
- policy: 운영 규정, 고객 응대, 환불 정책, 복장 규정

JSON 형식으로만 답변:
{{"category": "sales|manual|policy"}}
"""
    
    result = await genai_generate_text(prompt)
    parsed = json.loads(result)
    
    state["category"] = parsed["category"]
    print(f"🔍 [Router] 질문 카테고리: {parsed['category']}")
    
    return state


# ===== Step 3: Sales Data Node (매출/날씨/리뷰 통합 조회) =====
async def sales_node(state: InquiryState) -> InquiryState:
    """매출/주문/날씨/리뷰 데이터 조회 (스마트 분석)"""
    if state["category"] != "sales":
        return state
        
    print(f"📊 [Sales] 데이터 조회 시작: {state['question']}")
    
    # 1. 검색 조건 추출 (LLM)
    params = await extract_search_params(state['question'])
    print(f"   👉 검색 조건: {params}")
    
    target_store_id = state["store_id"]
    days = params.get("days", 7)
    
    # 2. 지점명으로 store_id 찾기 (만약 질문에 지점명이 있다면)
    if params.get("target_store_name"):
        store_query = f"SELECT store_id, store_name FROM stores WHERE store_name LIKE '%{params['target_store_name']}%' LIMIT 1"
        try:
            store_res = await fetch_all(store_query)
            if store_res:
                target_store_id = store_res[0]["store_id"]
                print(f"   👉 지점 변경: {params['target_store_name']} -> ID {target_store_id}")
        except Exception as e:
            print(f"   ⚠️ 지점 검색 실패: {e}")

    # 3. 날짜 계산
    try:
        days = int(days)
    except:
        days = 7
        
    start_date = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")

    # 4. 매출 & 날씨 데이터 조회
    sales_query = f"""
        SELECT sale_date, total_sales, total_orders, weather_info 
        FROM sales_daily 
        WHERE store_id = {target_store_id} 
          AND sale_date >= '{start_date}'
        ORDER BY sale_date DESC
    """
    sales_rows = await fetch_all(sales_query)
    
    # 데이터 포맷팅 (JSON 구조로 반환하여 Answer Node가 활용하기 좋게)
    recent_sales_data = []
    
    sales_text = f"=== 최근 {days}일 매출/날씨 데이터 (지점ID: {target_store_id}) ===\n"
    if not sales_rows:
        sales_text += "데이터 없음\n"
    
    for row in sales_rows:
        w_info = row['weather_info'] if row.get('weather_info') else "날씨정보없음"
        
        # JSON용 데이터
        recent_sales_data.append({
            "date": str(row["sale_date"]),
            "sales": float(row["total_sales"]),
            "orders": row["total_orders"],
            "weather": w_info
        })
        
        # LLM 참고용 텍스트
        sales_text += f"- {row['sale_date']}: 매출 {row['total_sales']:,.0f}원, 주문 {row['total_orders']}건 ({w_info})\n"

    # 5. 리뷰 데이터 조회 (필요 시)
    review_summary = ""
    if params.get("need_reviews", False) or "리뷰" in state["question"]:
         review_query = f"""
            SELECT rating, review_text, created_at 
            FROM reviews 
            WHERE store_id = {target_store_id} 
              AND created_at >= '{start_date}'
            ORDER BY created_at DESC 
            LIMIT 5
         """
         review_rows = await fetch_all(review_query)
         review_summary = f"\n=== 최근 리뷰 (관련도 높음) ===\n"
         for row in review_rows:
             review_summary += f"- ⭐{row['rating']} : {row['review_text']} ({row['created_at']})\n"
             
         sales_text += review_summary

    # state에 저장
    state["sales_data"] = {
        "summary_text": sales_text,  # LLM이 읽을 텍스트
        "recent_sales": recent_sales_data, # 차트 그릴 데이터
        "reviews": review_summary
    }
    
    print(f"📊 [Sales] 데이터 조회 완료 (기간: {days}일, 지점ID: {target_store_id})")
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
    # WHERE 조건 없이 전체 매뉴얼에서 의미적으로 가장 유사한 문서 검색
    query = f"""
    SELECT title, content, category,
           embedding <=> '{question_vector}'::vector AS distance
    FROM manuals
    ORDER BY distance
    LIMIT 3
    """
    
    rows = await fetch_all(query)
    state["manual_data"] = [
        f"[{row['title']}]\n{row['content']}"
        for row in rows
    ]
    
    print(f"📖 [Manual] {len(rows)}건의 매뉴얼 검색 완료 (Vector Search)")
    return state


# ===== Step 5: Policy RAG Node (정책 검색) =====
async def policy_node(state: InquiryState) -> InquiryState:
    """운영 정책 매뉴얼 검색 (Policies 테이블 조회)"""
    if state["category"] != "policy":
        return state
    
    question = state["question"]
    
    # OpenAI Embeddings로 질문 벡터화
    from langchain_openai import OpenAIEmbeddings
    embeddings_model = OpenAIEmbeddings(model="text-embedding-3-small")
    question_vector = embeddings_model.embed_query(question)
    
    # pgvector 유사도 검색 (policies 테이블)
    query = f"""
    SELECT title, content, category,
           embedding <=> '{question_vector}'::vector AS distance
    FROM policies
    ORDER BY distance
    LIMIT 3
    """
    
    rows = await fetch_all(query)
    state["policy_data"] = [
        f"[{row['title']}]\n{row['content']}"
        for row in rows
    ]
    
    print(f"📜 [Policy] {len(rows)}건의 정책 문서 검색 완료 (Policies Table)")
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


# ===== Step 6 (Enhanced): Answer Synthesis Node (개선된 답변 생성) =====
async def answer_node_v2(state: InquiryState) -> InquiryState:
    """수집한 데이터를 바탕으로 최종 답변 생성 (스마트 분석 포함)"""
    question = state["question"]
    category = state["category"]
    
    # 카테고리별 컨텍스트 구성
    context = ""
    raw_json_data = "[]"

    if category == "sales":
        # sales_node에서 만든 요약 텍스트 사용
        sales_data = state.get("sales_data", {})
        context = sales_data.get("summary_text", "데이터 없음")
        
        # JSON 데이터 삽입을 위해 임시 저장
        # (주의: LLM이 이 데이터를 변형하지 않고 그대로 'data' 필드에 넣도록 유도)
        try:
            raw_json_data = json.dumps(sales_data.get("recent_sales", []), ensure_ascii=False)
        except:
            raw_json_data = "[]"
        
    elif category == "manual":
        context = "\n\n".join(state.get("manual_data", []))
    elif category == "policy":
        context = "\n\n".join(state.get("policy_data", []))
    
    prompt = f"""
    당신은 프랜차이즈 본사의 노련한 AI 데이터 분석가입니다.
    사용자의 질문에 대해 제공된 데이터를 깊이 있게 분석하여 답변하세요.
    
    [분석 가이드]
    1. 매출/주문량의 추세를 분석하고 상승/하락 원인을 추론하세요.
    2. 데이터에 '날씨' 정보가 있다면 매출에 미친 영향을 언급하세요.
    3. '리뷰' 데이터가 있다면 고객 반응과 매출의 연관성을 분석하세요.
    4. 단순히 숫자만 나열하지 말고, "의견"과 "제안"을 포함하세요.

    **중요: 반드시 아래 JSON 형식을 엄격히 지켜서 답변하세요.**
    
    [Category: sales 일 때]
    {{
      "type": "sales",
      "summary": "분석 결과 요약 (날씨/리뷰 언급 필수)",
      "data": {raw_json_data if category == 'sales' else '[]'} 
    }}
    
    [Category: manual 또는 policy 일 때]
    {{
      "type": "general",
      "title": "관련 매뉴얼/규정 제목",
      "content": "핵심 내용 요약 및 상세 설명 (Markdown 형식, 줄바꿈은 \\n 사용)"
    }}
    
    질문: {question}
    카테고리: {category}
    
    [분석할 데이터]
    {context}
    """
    
    answer = await genai_generate_text(prompt)
    state["final_answer"] = answer
    
    print(f"✅ [Answer V2] 답변 생성 완료 ({len(answer)}자)")
    return state


def create_inquiry_graph():
    """
    LangGraph 생성 - Conditional Edge 기반 선택적 실행
    """
    graph = StateGraph(InquiryState)
    
    # 노드 등록
    graph.add_node("router", router_node)
    graph.add_node("sales", sales_node)
    graph.add_node("manual", manual_node)
    graph.add_node("policy", policy_node)
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
    
    # 각 데이터 수집 노드 → Answer (단일 경로)
    graph.add_edge("sales", "answer")
    graph.add_edge("manual", "answer")
    graph.add_edge("policy", "answer")
    
    # Answer → Save → END
    graph.add_edge("answer", "save")
    graph.add_edge("save", END)
    
    return graph.compile()


# ===== 실행 함수 =====
async def process_inquiry(store_id: int, question: str) -> Dict[str, Any]:
    """
    질문 처리 메인 함수
    
    Args:
        store_id: 매장 ID
        question: 질문 내용
    
    Returns:
        답변 및 메타데이터
    """
    graph = create_inquiry_graph()
    
    initial_state = InquiryState(
        store_id=store_id,
        question=question,
        category="",
        sales_data={},
        manual_data=[],
        policy_data=[],
        final_answer="",
        inquiry_id=0
    )
    
    result = await graph.ainvoke(initial_state)
    
    return {
        "inquiry_id": result["inquiry_id"],
        "category": result["category"],
        "answer": result["final_answer"]
    }
