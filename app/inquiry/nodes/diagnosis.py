import json
from datetime import date
from app.clients.openai import client
from app.core.db import fetch_all
from app.inquiry.state import InquiryState

async def diagnosis_node(state: InquiryState) -> InquiryState:
    """
    [Diagnosis Node]
    매출/메뉴 관련 질문에 대해 SQL을 생성하고 DB 데이터를 조회합니다.
    """
    question = state["question"]
    store_id = state.get("store_id", 1)
    
    print(f"📊 [Diagnosis] Start Analysis for Store ID: {store_id}")
    
    # 1. DB 스키마 정보
    schema_info = """
    Target Table: sales_daily
    - date (YYYY-MM-DD): 매출 날짜
    - store_id (int): 지점 ID (1: 강남, 2: 부산, 3: 속초)
    - total_sales (int): 일 매출
    - total_orders (int): 주문 건수
    - weather_info (text): 날씨 (맑음, 비 등)

    Target Table: orders (상세 주문)
    - order_id, store_id, menu_id, ordered_at (timestamp), quantity
    
    Target Table: menus
    - menu_id, menu_name, category, price
    
    Target Table: reviews
    - review_id, order_id, rating, review_text
    """
    
    # 2. 최신 데이터 날짜 확인
    try:
        last_date_row = await fetch_all("SELECT MAX(date) as last_date FROM sales_daily WHERE store_id = $1", store_id)
        ref_date = last_date_row[0]['last_date'] if last_date_row and last_date_row[0]['last_date'] else date.today()
    except:
        ref_date = date.today()
        
    ref_date_str = ref_date.strftime("%Y-%m-%d")
    
    # 3. SQL 생성 (OpenAI)
    system_prompt = f"""
    당신은 PostgreSQL 전문 DBA입니다.
    사용자의 질문을 분석하여 올바른 SQL 쿼리를 작성하세요.
    
    [Schema]
    {schema_info}
    
    [Reference Date]
    현재 DB의 최신 데이터 날짜는 '{ref_date_str}'입니다.
    "최근 1주일", "지난달" 등의 기간 표현은 이 날짜를 기준으로 계산하세요.
    
    [Requirements]
    - 오직 SELECT 문 하나만 출력하세요. (SQL 코드 블록 없이 순수 쿼리만)
    - 반드시 `store_id = {store_id}` 조건을 포함하세요.
    """
    
    generated_sql = ""
    collected_data = {}

    try:
        res = await client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": question}
            ],
            temperature=0
        )
        generated_sql = res.choices[0].message.content.replace("```sql", "").replace("```", "").strip()
        print(f"💻 [Gen SQL] {generated_sql}")
        
        # 4. SQL 실행
        rows = await fetch_all(generated_sql)
        collected_data["sql_result"] = rows
        
        # 추가 데이터: 리뷰
        if "review" in question or "평가" in question:
            review_q = f"""
                SELECT r.rating, r.review_text, m.menu_name, o.ordered_at
                FROM reviews r
                JOIN orders o ON r.order_id = o.order_id
                JOIN menus m ON o.menu_id = m.menu_id
                WHERE o.store_id = {store_id}
                ORDER BY o.ordered_at DESC LIMIT 10
            """
            reviews = await fetch_all(review_q)
            collected_data["recent_reviews"] = reviews
            
    except Exception as e:
        print(f"❌ [SQL/DB Error] {e}")
        collected_data["error"] = str(e)
        
    return {
        "sql_query": generated_sql,
        "sales_data": collected_data
    }
