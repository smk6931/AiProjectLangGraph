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


# ===== Step 3: Diagnosis Node (매출 진단 & 원인 분석) =====
async def diagnosis_node(state: InquiryState) -> InquiryState:
    """매출 하락 원인 진단 및 종합 분석 (Sales + Weather + Reviews)"""
    if state["category"] != "sales":
        return state
        
    print(f"🕵️‍♀️ [Diagnosis] 매출 진단 시작: {state['question']}")
    
    # 1. 검색 조건 추출
    params = await extract_search_params(state['question'])
    target_store_id = state["store_id"]
    days = params.get("days", 7)
    
    # ---------------------------------------------------------
    # [Smart Store Matcher] 지점명/지역명 매칭 로직 강화
    # ---------------------------------------------------------
    start_search_name = params.get("target_store_name")
    
    if start_search_name:
        print(f"   🔎 지점 검색 시도: '{start_search_name}'")
        
        # 1. 전체 매장 리스트 가져오기 (데이터 양이 적으므로 전체 로드 후 매칭이 정확함)
        all_stores_query = "SELECT store_id, store_name, city FROM stores"
        all_stores = await fetch_all(all_stores_query)
        
        # 2. 매칭 점수 계산 (Python 로직)
        # 키워드가 store_name이나 city에 포함되면 매칭 후보
        best_match = None
        best_score = 0
        
        # 검색어 정제 ("점", "지점" 등 제거)
        keyword = start_search_name.replace("지점", "").replace("점", "").strip()
        
        for store in all_stores:
            score = 0
            s_name = store['store_name']
            s_city = store['city']
            
            # (1) 정확히 포함되는 경우
            if keyword in s_name: score += 3
            if keyword in s_city: score += 2
            
            # (2) 부분 일치 (2글자 이상 겹침) - 간단한 로직
            # 실제로는 difflib 등을 쓸 수도 있지만, 여기선 포함 여부가 젤 확실함
            
            if score > best_score:
                best_score = score
                best_match = store
                
        # 3. 결과 반영
        if best_match and best_score > 0:
            target_store_id = best_match["store_id"]
            state["store_id"] = target_store_id
            print(f"   ✅ 지점 매칭 성공: '{start_search_name}' -> {best_match['store_name']} (ID {target_store_id})")
        else:
            print(f"   ❌ 지점 매칭 실패: '{start_search_name}' (DB에 유사한 지점이 없음)")
            # 매칭 실패 시, 엉뚱한 지점(기본값) 데이터를 보여주면 안됨.
            # 명확히 "찾을 수 없음"을 답변하도록 유도해야 함.
            state["sales_data"] = {
                "summary_text": f"죄송합니다. '{start_search_name}'에 해당하는 지점을 찾을 수 없습니다. (검색된 키워드: {keyword})",
                "recent_sales": [],
                "store_name": "알 수 없음",
                "diagnosis_result": "지점 식별 불가"
            }
            return state
            
    # ---------------------------------------------------------
    
    # 날짜 계산 (비교 분석을 위해 2배 기간 조회)
    try:
        days = int(days)
    except:
        days = 7
        
    end_date = datetime.now()
    start_date = (end_date - timedelta(days=days)).strftime("%Y-%m-%d")
    prev_start_date = (end_date - timedelta(days=days*2)).strftime("%Y-%m-%d")

    # 2. 매출 & 날씨 데이터 조회 (현재 기간 vs 직전 기간)
    # 직전 기간까지 포함해서 넉넉하게 조회
    sales_query = f"""
        SELECT sale_date, total_sales, total_orders, weather_info 
        FROM sales_daily 
        WHERE store_id = {target_store_id} 
          AND sale_date >= '{prev_start_date}'
        ORDER BY sale_date DESC
    """
    sales_rows = await fetch_all(sales_query)
    
    # 데이터 분리 (이번 기간 vs 지난 기간)
    current_period = []
    prev_period = []
    
    import pandas as pd
    threshold_date = pd.to_datetime(start_date).date()
    
    for row in sales_rows:
        try:
            row_date = row["sale_date"] # date 객체라고 가정
        except:
            row_date = datetime.strptime(str(row["sale_date"]), "%Y-%m-%d").date()
            
        if row_date >= threshold_date:
            current_period.append(row)
        else:
            prev_period.append(row)
            
    # 매출 증감율 계산
    curr_total = sum([r['total_sales'] for r in current_period])
    prev_total = sum([r['total_sales'] for r in prev_period])
    
    growth_rate = 0
    if prev_total > 0:
        growth_rate = ((curr_total - prev_total) / prev_total) * 100
        
    print(f"   📉 매출 분석: 이번 {days}일 {curr_total:,.0f}원 vs 지난 {days}일 {prev_total:,.0f}원 (변동률: {growth_rate:.1f}%)")

    # 3. 데이터 포맷팅
    sales_text = f"=== 매출 진단 리포트 (지점ID: {target_store_id}) ===\n"
    sales_text += f"기간: 최근 {days}일 ({start_date} ~ Today)\n"
    sales_text += f"매출 변동: {curr_total:,.0f}원 (전분기 대비 {growth_rate:+.1f}% {'상승' if growth_rate >=0 else '하락'})\n"
    
    recent_sales_data = []
    for row in current_period:
        w_info = row['weather_info'] if row.get('weather_info') else "날씨정보없음"
        recent_sales_data.append({
            "date": str(row["sale_date"]),
            "sales": float(row["total_sales"]),
            "orders": row["total_orders"],
            "weather": w_info
        })
        sales_text += f"- {row['sale_date']}: {row['total_sales']:,.0f}원 / {row['total_orders']}건 ({w_info})\n"

    # 4. 리뷰 데이터 조회 (매출 하락 시 또는 진단 요청 시 무조건 조회)
    # 매출이 떨어졌거나(-), 질문에 '원인', '진단', '이유' 등이 포함되면 리뷰를 깊게 파봄
    need_deep_dive = growth_rate < 0 or any(x in state["question"] for x in ["원인", "이유", "진단", "분석", "문제"])
    
    # [삭제됨: 기존의 단술 지점 검색 로직 제거]
    # 위에서 이미 Smart Store Matcher로 처리했으므로 여기서는 제거함.

    # 3. 날짜 계산 (이 주석은 원래 코드의 잔재일 수 있으므로 무시)
    
    review_summary = ""
    if need_deep_dive or params.get("need_reviews", False):
         print("   🧐 매출 부진/진단 요청 감지 -> 리뷰 정밀 분석 수행")
         review_query = f"""
            SELECT rating, review_text, created_at 
            FROM reviews 
            WHERE store_id = {target_store_id} 
              AND created_at >= '{prev_start_date}'
            ORDER BY created_at DESC 
            LIMIT 10
         """
         review_rows = await fetch_all(review_query)
         review_summary = f"\n=== 고객 리뷰 분석 (매출 영향 요인) ===\n"
         if not review_rows:
             review_summary += "특이한 리뷰 없음.\n"
         else:
             for row in review_rows:
                 review_summary += f"- {row['created_at']} (⭐{row['rating']}): {row['review_text']}\n"
                 
         sales_text += review_summary

    # state에 저장
    state["sales_data"] = {
        "summary_text": sales_text,
        "recent_sales": recent_sales_data,
        "reviews": review_summary,
        "diagnosis_result": f"매출 {growth_rate:.1f}% 변동"
    }
    
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


# ===== Step 5.5: Web Search Node (외부 검색) =====
# ===== Step 5.5: Web Search Node (외부 검색) =====
async def web_search_node(state: InquiryState) -> InquiryState:
    """내부 DB 검색 실패 시 외부 웹 검색 수행 (Tavily AI Search + Self-Correction)"""
    question = state["question"]
    print(f"🌐 [Tavily Search] 내부 문서 부족 -> 외부 검색 전환: {question}")
    
    # 🔑 Tavily API 키 입력
    TAVILY_API_KEY = "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"
    
    # if TAVILY_API_KEY == "YOUR_TAVILY_KEY":
    #     state["manual_data"] = ["❌ Tavily API 키가 설정되지 않았습니다."]
    #     return state

    try:
        from tavily import TavilyClient
        tavily = TavilyClient(api_key=TAVILY_API_KEY)
        
        # 1차 검색 시도 (구체적 쿼리)
        target_query = f"카페 프랜차이즈 {question}"
        response = tavily.search(query=target_query, search_depth="basic", max_results=5)
        raw_results = response.get('results', [])
        
        # 🔄 Self-Correction: 검색 결과가 없으면 쿼리 단순화 후 재시도
        if not raw_results:
            print(f"🔄 [Self-Correction] '{target_query}' 결과 없음 -> '{question}' 으로 재검색")
            # 접두사 제거하고 질문 자체로 검색
            response = tavily.search(query=question, search_depth="basic", max_results=5)
            raw_results = response.get('results', [])
        
        # 결과 포맷팅
        formatted_list = []
        for item in raw_results:
            title = item.get('title', '제목 없음')
            url = item.get('url', '#')
            content = item.get('content', '')
            formatted_list.append(f"Title: {title}\nLink: {url}\nSnippet: {content}\n")
        
        if not formatted_list:
             state["manual_data"] = ["Tavily 검색 결과가 없습니다. (재검색 포함)"]
        else:
             formatted_results = "[외부 웹 검색 결과 (Tavily)]\n" + "\n---\n".join(formatted_list)
             state["manual_data"] = [formatted_results]
        
        state["search_meta"] = {"source": "web_search", "min_distance": 0.0}
        
    except Exception as e:
        print(f"❌ Tavily 검색 실패: {e}")
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


# ===== Step 6: Answer Synthesis Node (답변 생성 - Structured) =====
async def answer_node_v2(state: InquiryState) -> InquiryState:
    """수집한 데이터를 바탕으로 구조화된 JSON 답변 생성"""
    question = state["question"]
    category = state["category"]
    
    # 1. 컨텍스트 구성
    context_text = ""
    is_web_search = state.get("search_meta", {}).get("source") == "web_search"
    
    if category == "sales":
        if "sales_data" in state and state["sales_data"]:
             context_text = f"매출 진단 결과:\n{state['sales_data'].get('diagnosis_result', '')}\n\n상세 데이터:\n{state['sales_data'].get('summary_text', '')}"
    else:
        # manual / policy 데이터 통합
        docs = state.get("manual_data", []) + state.get("policy_data", [])
        context_text = "\n\n".join(docs)
    
    # 2. 시스템 프롬프트 (JSON 강제)
    system_prompt = (
        "당신은 프랜차이즈 매장 관리 전문가 AI입니다. "
        "질문에 대해 수집된 컨텍스트를 바탕으로 답변을 작성하세요. "
        "반드시 아래 **JSON 포맷**으로만 답변해야 합니다. 마크다운(` ```json `)을 쓰지 말고 순수 JSON 문자열만 출력하세요.\n\n"
        "{\n"
        '  "summary": "핵심 내용을 1~2문장으로 요약 (명확하게)",\n'
        '  "detail": "상세한 답변 내용 (마크다운 포맷 활용 가능, 줄바꿈은 \\n 사용)",\n'
        '  "action_items": ["구체적인 실행 제안 1", "구체적인 실행 제안 2", ...],\n'
        '  "sources": ["참고한 자료 출처 또는 근거 (URL이 있다면 포함)"]\n'
        "}\n\n"
        "매출 분석 질문인 경우, 단순 수치 나열보다 '전략적 제안(Action Items)'에 집중하세요."
        "웹 검색 결과인 경우, 출처(URL)를 `sources` 필드에 반드시 포함하세요."
    )
    
    # 메시지 구성
    from langchain_core.messages import SystemMessage, HumanMessage
    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=f"질문: {question}\n\n[컨텍스트 데이터]\n{context_text}")
    ]
    
    # 3. LLM 호출
    from langchain_openai import ChatOpenAI
    llm = ChatOpenAI(model="gpt-4o", temperature=0)
    response = await llm.ainvoke(messages)
    
    # 4. JSON 파싱 및 저장
    try:
        import json
        content = response.content.strip()
        
        # 마크다운 코드블록 제거
        if content.startswith("```json"):
            content = content[7:]
        elif content.startswith("```"):
             content = content[3:]
        if content.endswith("```"):
            content = content[:-3]
        
        content = content.strip()
        
        # 유효성 검사
        parsed_json = json.loads(content) 
        state["final_answer"] = json.dumps(parsed_json, ensure_ascii=False) # 다시 문자열로 저장 (파싱 성공 확인)
        
    except Exception as e:
        print(f"JSON Parsing Error: {e}")
        # 실패 시 텍스트 포맷을 JSON으로 강제 래핑
        fallback = {
            "summary": "AI 답변",
            "detail": response.content, # 원본 텍스트
            "action_items": [],
            "sources": []
        }
        state["final_answer"] = json.dumps(fallback, ensure_ascii=False)

    print(f"✅ [Structured Answer] 답변 생성 완료")
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
        
        # 임계값 설정 (0.45 이상이면 관련성 낮음으로 판단)
        THRESHOLD = 0.45
        
        if min_dist > THRESHOLD:
            print(f"⚠️ [Search Check] 문서 유사도 낮음 ({min_dist:.4f} > {THRESHOLD}) -> Web Search 전환")
            return "retry_web"
        else:
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
 