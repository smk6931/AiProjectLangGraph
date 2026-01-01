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
from datetime import datetime, timedelta, date    
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage

# ===== 데이터 검색용 파라미터 추출 함수 (Upgrade) =====
async def extract_search_params(question: str):
    """
    질문 분석 -> 분석 대상(매장들) & 필요한 데이터 소스(테이블) 결정
    """
    prompt = f"""
    당신은 데이터베이스 전문가입니다. 질문을 분석하여 아래 정보를 JSON으로 추출하세요.
    
    질문: "{question}"
    
    [추출 규칙]
    
    1. target_store_codes: 분석 대상 매장 코드 리스트 (배열, 1개 이상)
       - 단일 지점 요청 시에도 리스트로 반환: "부산점" -> ["BUSAN"]
       - "서울", "강남" -> ["SEOUL"]
       - "부산", "서면" -> ["BUSAN"]
       - "강원", "속초" -> ["GANGWON"]
       - "서울하고 부산 비교해줘" -> ["SEOUL", "BUSAN"]
       - "전체", "모든", "전 지점" 또는 언급 없음 -> ["ALL"]
       
    2. required_tables: 질문에 답변하기 위해 조회해야 할 테이블 리스트 (복수 선택 가능)
       - "orders": 메뉴 판매량, 인기/비인기 메뉴 식별 (What)
       - "sales_daily": 매출 추이, 날씨 정보 포함 (External Factor)
       - "reviews": 판매/매출의 '원인(Why)' 분석, 고객 반응, 맛 평가 (이유/분석 요청 시 필수 포함)
       
    [테이블 선택 가이드]
    - "왜 매출이 줄었어?" -> ["sales_daily", "reviews"] (추이 + 원인)
    - "안 팔린 메뉴와 이유" -> ["orders", "reviews"] (메뉴 + 원인)
    - "그냥 매출 보여줘" -> ["sales_daily"]
       
    [출력 예시]
    {{
        "target_store_codes": ["SEOUL", "BUSAN"],
        "required_tables": ["sales_daily", "reviews"],
        "reason": "서울과 부산 지점의 매출 추이를 비교하고 고객 리뷰를 분석하기 위함"
    }}
    """
    try:
        response = await genai_generate_text(prompt)
        clean_text = response.replace("```json", "").replace("```", "").strip()
        parsed = json.loads(clean_text)
        return parsed
    except:
        return {"target_store_codes": ["ALL"], "required_tables": ["sales_daily", "orders"], "reason": "Error parsing"}


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
- sales: 매출 데이터 분석이 필요한 질문 (매출액, 판매량, 인기 메뉴, 데이터 기반 의사결정)
- manual: 기기 사용법, 청소 방법, 고장 수리, 조리법 등 매뉴얼 검색
- policy: 운영 규정, 고객 응대, 환불 정책, 근태 관리 등 정책 검색 

JSON 형식으로만 답변:
{{"category": "sales|manual|policy"}}
"""
    
    result = await genai_generate_text(prompt)
    parsed = json.loads(result)
    
    state["category"] = parsed["category"]
    print(f"🔍 [Router] 질문 카테고리: {parsed['category']}")
    llm = ChatOpenAI(model="gpt-4o", temperature=0)
    messages = [HumanMessage(content=prompt)]
    response = await llm.ainvoke(messages)
    
    content = response.content.replace("```json", "").replace("```", "").strip()
    try:
        data = json.loads(content)
        category = data.get("category", "sales") # 기본값 sales
    except:
        category = "sales"
        
    print(f"🔀 [Router] Category Decision: {category} (Reason: {data.get('reason', 'N/A') if 'data' in locals() else 'Parse Error'})")
    
    # State 업데이트
    state["category"] = category
    return state


# ===== Step 3: Diagnosis Node (Sales Analysis 2.0) =====
# ===== Step 3: Diagnosis Node (Multi-Store Support) =====
async def diagnosis_node(state: InquiryState) -> InquiryState:
    """
    [Sales Analysis V2] 
    1. 매장 Scope 확인 (서울/부산/강원/전체)
    2. 최근 데이터 기준일(Anchor Date) 산출
    3. 필요한 테이블만 골라서 동적 쿼리 (Orders / SalesDaily / Reviews)
    """
    if state["category"] != "sales":
        return state
        
    print(f"🕵️‍♀️ [Diagnosis V2] 분석 시작: {state['question']}")
    
    # 1. 검색 파라미터 추출 (LLM)
    search_params = await extract_search_params(state['question'])
    
    target_store_codes = search_params.get("target_store_codes", ["ALL"])
    required_tables = search_params.get("required_tables", [])
    date_range_str = search_params.get("date_range", "DATE(o.ordered_at) >= DATE('now', '-7 days')")
    reason = search_params.get("reason", "")
    
    print(f"   🎯 타겟(List): {target_store_codes}, Tables: {required_tables}")
    
    # Store ID Mapping
    collected_data = {
        "scope": ", ".join(target_store_codes),
        "tables_used": required_tables,
        "period": "최근 7일 (자동 설정)" if "7 days" in date_range_str else "사용자 지정",
        "reason": reason
    }
    
    try:
        # DB 연결 및 스토어 ID 조회 (공통)
        store_codes = []
        target_ids = []
        target_store_id = None # 단일 스토어용 (비전용)

        q_stores = "SELECT store_id, store_name, region FROM stores"
        all_stores = await fetch_all(q_stores)
        
        # Scope Resolution
        if "ALL" in target_store_codes:
            store_codes = [s['store_name'] for s in all_stores]
            target_ids = [s['store_id'] for s in all_stores]
        else:
            for code in target_store_codes:
                matched = [s for s in all_stores if code in s['store_name'] or code in s['region']]
                if matched:
                    for m in matched:
                        if m['store_id'] not in target_ids:
                            target_ids.append(m['store_id'])
                            store_codes.append(m['store_name'])
        
        # [Anchor Date Fix] 데이터가 존재하는 실제 마지막 날짜 확인
        # 현재 시스템 시간(2026년)과 데이터 시간(2025년) 불일치 해결
        anchor_date = None
        q_max_date = "SELECT MAX(sale_date) as last_date FROM sales_daily"
        if target_ids:
             ids_str = ",".join(map(str, target_ids))
             q_max_date += f" WHERE store_id IN ({ids_str})"
             
        try:
            date_rows = await fetch_all(q_max_date)
            if date_rows and date_rows[0]['last_date']:
                anchor_date = date_rows[0]['last_date']
                
                # date 객체 확인 및 변환
                if isinstance(anchor_date, str):
                    curr_date = datetime.strptime(anchor_date, "%Y-%m-%d").date()
                else:
                    curr_date = anchor_date
                    
                start_date = curr_date - timedelta(days=6) # 1주일
                # [CRITICAL FIX] Postgres 호환을 위해 명시적 날짜 문자열 사용
                date_range_str = f"'{start_date}' AND '{curr_date}'"
                print(f"📅 [Smart Period] 데이터 기반 기간 재설정: {start_date} ~ {curr_date}")
            else:
                print("⚠️ [Smart Period] 데이터가 없어 기본 기간(최근 7일) 사용")
                # Fallback: Postgres Syntax
                date_range_str = "CURRENT_DATE - INTERVAL '7 days' AND CURRENT_DATE"
        except Exception as e:
            print(f"⚠️ [Smart Period] Error: {e}")
            
        print(f"🔍 [Diagnosis] Effective Date Range: {date_range_str}")

        # (A) Sales Daily (매출 추이)
        if "sales_daily" in required_tables:
            where_sql = f"DATE(s.sale_date) BETWEEN {date_range_str}"
            if target_ids:
                ids_str = ",".join(map(str, target_ids))
                where_sql += f" AND s.store_id IN ({ids_str})"
            
            q_sales = f"""
                SELECT s.sale_date, st.store_name, SUM(s.total_sales) as total_sales, SUM(s.total_orders) as total_orders, MAX(s.weather_info) as weather_info
                FROM sales_daily s
                JOIN stores st ON s.store_id = st.store_id
                WHERE {where_sql}
                GROUP BY s.sale_date, st.store_name
                ORDER BY s.sale_date ASC
            """
            rows = await fetch_all(q_sales)
            collected_data["daily_trend"] = rows
            
            # Chart Data
            chart_data = []
            for r in rows:
                chart_data.append({
                    "date": r['sale_date'],
                    "store": r['store_name'],
                    "sales": float(r['total_sales']) if r['total_sales'] else 0,
                    "orders": int(r['total_orders']) if r['total_orders'] else 0
                })
            collected_data["chart_data"] = chart_data

        # (B) Orders (메뉴 분석)
        # [Safety Lock] 메뉴 분석(Orders) 시 리뷰 강제 추가
        if "orders" in required_tables:
            if "reviews" not in required_tables:
                print("⚠️ [Auto-Fix] 메뉴 분석을 위해 Reviews 테이블 강제 추가")
                required_tables.append("reviews")
                
            where_sql = f"DATE(o.ordered_at) BETWEEN {date_range_str}"
            if target_ids:
                 ids_str = ",".join(map(str, target_ids))
                 where_sql += f" AND o.store_id IN ({ids_str})"
            
            q_menu = f"""
                SELECT 
                    m.menu_id,
                    m.menu_name, 
                    m.category, 
                    SUM(o.quantity) as qty, 
                    SUM(o.total_price) as rev
                FROM orders o
                JOIN menus m ON o.menu_id = m.menu_id
                WHERE {where_sql}
                GROUP BY m.menu_id, m.menu_name, m.category
                ORDER BY qty DESC
                LIMIT 5
            """
            # 1. Top 5 Fetch
            rows_top = await fetch_all(q_menu)
            print(f"📊 [Diagnosis] Top Menus Fetched: {len(rows_top)}")
            
            # 2. Worst 5 Fetch
            q_worst = q_menu.replace("DESC", "ASC").replace("LIMIT 5", "LIMIT 5")
            rows_worst = await fetch_all(q_worst)
            print(f"📊 [Diagnosis] Worst Menus Fetched: {len(rows_worst)}")
            
            # 3. Review Binding Logic
            all_target_menus = rows_top + rows_worst
            target_menu_ids = [r['menu_id'] for r in all_target_menus]
            
            menu_review_map = {} 
            
            if target_menu_ids:
                 ids_str_menu = ",".join(map(str, set(target_menu_ids)))
                 q_deep = f"""
                    SELECT o.menu_id, r.rating, r.review_text, o.ordered_at
                    FROM reviews r
                    JOIN orders o ON r.order_id = o.order_id
                    WHERE o.menu_id IN ({ids_str_menu}) 
                    AND DATE(o.ordered_at) BETWEEN {date_range_str}
                    ORDER BY r.created_at DESC
                 """
                 deep_reviews = await fetch_all(q_deep)
                 print(f"💬 [Diagnosis] Bound Reviews Fetched: {len(deep_reviews)}")
                 
                 # UI 증거용 저장
                 collected_data["menu_specific_reviews"] = deep_reviews
                 
                 for dr in deep_reviews:
                     mid = dr['menu_id']
                     if mid not in menu_review_map:
                         menu_review_map[mid] = []
                     menu_review_map[mid].append(f"⭐{dr['rating']}: {dr['review_text']}")
            
            # 4. Attach to Menu Data
            for r in rows_top:
                r['related_reviews'] = menu_review_map.get(r['menu_id'], [])[:10]
            for r in rows_worst:
                r['related_reviews'] = menu_review_map.get(r['menu_id'], [])[:10]

            collected_data["top_selling_menus"] = rows_top
            collected_data["low_selling_menus"] = rows_worst

        # (C) Reviews (일반 조회)
        if "reviews" in required_tables:
            # Join with orders to get date & store filtering
            where_sql = f"DATE(o.ordered_at) BETWEEN {date_range_str}"
            if target_ids:
                ids_str = ",".join(map(str, target_ids))
                where_sql += f" AND o.store_id IN ({ids_str})"
            
            q_review = f"""
                SELECT s.store_name, r.rating, r.review_text, o.ordered_at
                FROM reviews r
                JOIN orders o ON r.order_id = o.order_id
                JOIN stores s ON o.store_id = s.store_id
                WHERE {where_sql}
                ORDER BY o.ordered_at DESC
                LIMIT 500
            """
            rows = await fetch_all(q_review)
            collected_data["recent_reviews"] = rows
            print(f"💬 [Diagnosis] Recent Reviews Fetched: {len(rows)}")

    except Exception as e:
        print(f"❌ [Diagnosis] Critical Error: {e}")
        collected_data["error"] = str(e)
        collected_data["summary_text"] = f"데이터 조회 중 심각한 오류가 발생했습니다: {e}"
        
    # 3. Summary Generation (LLM을 위한 요약 텍스트)
    # [Contextual Binding] 메뉴와 리뷰를 함께 제공
    summary_text = f"=== 📊 분석 리포트 ({', '.join(store_codes)}) ===\n"
    summary_text += f"기간: {date_range_str}\n\n"
    
    if "daily_trend" in collected_data:
        summary_text += "[일별 매출 데이터 (지점별 구분)]\n"
        for r in collected_data["daily_trend"]:
            sales_val = float(r['total_sales']) if r['total_sales'] else 0
            weather = r.get('weather_info', '-')
            summary_text += f"- [{r['sale_date']}] {r['store_name']}: {sales_val:,.0f}원 (주문 {r['total_orders']}건, 날씨 {weather})\n"

    if "top_selling_menus" in collected_data:
        summary_text += "\n[통합 인기 메뉴 Top 5 (Best)]\n"
        for m in collected_data["top_selling_menus"]:
            summary_text += f"- {m['menu_name']} ({m['category']}): {m['qty']}개 판매, {int(m['rev']):,}원\n"
            if 'related_reviews' in m and m['related_reviews']:
                reviews_str = " / ".join(m['related_reviews'])
                summary_text += f"  (🔍 고객 리뷰: {reviews_str})\n"

    if "low_selling_menus" in collected_data:
        summary_text += "\n[통합 판매 저조 메뉴 Top 5 (Worst)]\n"
        for m in collected_data["low_selling_menus"]:
            summary_text += f"- {m['menu_name']} ({m['category']}): {m['qty']}개 판매, {int(m['rev']):,}원\n"
            if 'related_reviews' in m and m['related_reviews']:
                reviews_str = " / ".join(m['related_reviews'])
                summary_text += f"  (🔍 고객 리뷰: {reviews_str})\n"
                
    if "recent_reviews" in collected_data and isinstance(collected_data["recent_reviews"], list):
        summary_text += "\n[최근 고객 리뷰 데이터 (매장 전체)]\n"
        for r in collected_data["recent_reviews"][:20]: # 상위 20개만
            s_name = r.get('store_name', '')
            summary_text += f"- [{s_name}] ⭐{r.get('rating')}: {r.get('review_text')}\n"

    collected_data["summary_text"] = summary_text
    
    # 5. Result for Chat UI Chart (Chart Data Formatting)
    if "daily_trend" in collected_data:
        collected_data["chart_setup"] = {"title": f"지점별 매출 추이 비교 ({', '.join(store_codes)})"}
        total_sales = sum([float(r['total_sales']) for r in collected_data["daily_trend"] if r['total_sales']])
        total_orders = sum([int(r['total_orders']) for r in collected_data["daily_trend"] if r['total_orders']])
        
        collected_data["key_metrics"] = {
            "period": "최근 7일",
            "total_sales": total_sales,
            "total_orders": total_orders
        }

    # 간단 진단 코멘트 (타이틀용)
    collected_data["diagnosis_result"] = f"분석 완료: {', '.join(store_codes)} (최근 7일)"

    state["sales_data"] = collected_data
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
    LIMIT 5
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
    LIMIT 5
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
        "1. **Reference Citation (출처 명시)**: 답변 시 반드시 **참고한 매뉴얼/규정의 제목**과 핵심 내용을 인용해서 답변하세요. 예: '참고하신 [환불 규정 가이드]에 따르면...'\n"
        "2. **Evidence Based**: [분석용 데이터]에 있는 내용을 최우선으로 근거로 삼으세요. 유사도가 높게 나온 문서가 있다면 해당 내용을 바탕으로 답변을 구성하세요.\n"
        "3. **Markdown Table 필수**: Best/Worst 메뉴, 지점 비교 등 리스트 형태의 데이터는 **반드시 Markdown 표(Table)**로 작성하여 가독성을 높이세요. (컬럼 예: 순위, 메뉴명, 판매량, 매출액가, 리뷰 요약)\n"
        "4. **화폐 단위**: 반드시 **원(KRW)**을 사용하세요.\n"
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
    
    # 4. 결과 저장 (Structured JSON 생성)
    # UI가 차트, 메트릭, 리뷰 근거를 렌더링할 수 있도록 JSON 구조화
    final_output = {
        "answer": response.content,
        "category": category
    }
    
    if category == "sales" and "sales_data" in state:
        sd = state["sales_data"]
        final_output["chart_data"] = sd.get("chart_data")
        final_output["chart_setup"] = sd.get("chart_setup")
        final_output["key_metrics"] = sd.get("key_metrics")
        
        # [Evidence] 분석에 사용된 리뷰 데이터 전달 (메뉴별 + 전체 최신)
        # 중복 제거를 위해 리스트 합치기
        all_reviews = sd.get("recent_reviews", []) + sd.get("menu_specific_reviews", [])
        # 간단한 중복 제거 (내용 기준)
        seen = set()
        unique_reviews = []
        for r in all_reviews:
            if r.get('review_text') and r['review_text'] not in seen:
                seen.add(r['review_text'])
                unique_reviews.append(r)
                
        final_output["used_reviews"] = unique_reviews
        
        # UI는 'summary' 키가 없으면 'answer'를 텍스트로 출력하지 않음? 
        # detail에 답변 내용 저장
        final_output["detail"] = response.content
    else:
        final_output["detail"] = response.content

    def json_serial(obj):
        if isinstance(obj, (datetime, date)):
            return obj.isoformat()
        raise TypeError(f"Type {type(obj)} not serializable")

    state["final_answer"] = json.dumps(final_output, ensure_ascii=False, default=json_serial)
    
    print(f"✅ [Analyst Answer] 분석 보고서 생성 완료 (Structured)")
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
        # [NEW] 여기서 diagnosis_node를 실행해서 search_param 결과까지 state에 담김
        state = await diagnosis_node(state)
        # 매출은 유사도 개념이 아니므로 100% 신뢰로 간주
        min_dist = 0.0
        # Sales Data에서 요약 정보 추출
        sales_info = state.get("sales_data", {})
        top_doc = {
            "title": "매출 데이터 분석", 
            "content": sales_info.get("summary_text", "분석 결과 없음"),
            # 프론트엔드 전달용 메타데이터 추가
            "search_params": {
                "scope": sales_info.get("scope"),
                "tables_used": sales_info.get("tables_used"),
                "period": sales_info.get("period")
            }
        }
        
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

    # [Feature] AI Recommender: 후보군 중 유저가 볼만한 문서 추천
    recommendation = {"indices": [0], "comment": "가장 유사도가 높은 문서입니다."}
    if search_results and category != "sales":
        try:
            # 후보군 제목만 추출
            titles = [c.split('\n')[0] for c in search_results]
            
            rec_prompt = f"""
            질문: "{question}"
            
            검색된 문서 목록:
            {json.dumps(titles, ensure_ascii=False)}
            
            위 목록 중 질문과 가장 관련성이 높은 문서를 1개 이상 선택하세요.
            그리고 그 이유를 한 문장으로 설명하세요.
            
            [출력 포맷(JSON)]
            {{
                "recommended_indices": [0, 2],
                "comment": "질문하신 '환불'과 관련된 규정은 1번과 3번 문서에 잘 나와 있습니다."
            }}
            """
            rec_res = await genai_generate_text(rec_prompt)
            rec_data = json.loads(rec_res.replace("```json", "").replace("```", "").strip())
            
            recommendation["indices"] = rec_data.get("recommended_indices", [0])
            recommendation["comment"] = rec_data.get("comment", "관련된 문서를 선택했습니다.")
        except Exception as e:
            print(f"⚠️ 추천 로직 에러: {e}")

    return {
        "category": category,
        "min_distance": min_dist,
        "similarity_score": round((1 - min_dist) * 100, 1), # 0~100 점수
        "top_document": top_doc,
        "candidates": search_results, # List of strings (formatted)
        "context_data": search_results if category != "sales" else [],
        "recommendation": recommendation, # AI 추천 정보 추가
        "sales_data": state.get("sales_data", {}) # [NEW] Sales Meta Data 전달
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
 