import json
from datetime import datetime, timedelta
from typing import Dict, Any, List

# External App Imports
from app.clients.genai import genai_generate_text
from app.core.db import fetch_all
from app.inquiry.inquiry_schema import InquiryState

# ===== Search Param Extraction Helper =====
async def extract_search_params(question: str):
    """
    질문 분석 -> 분석 대상(매장들) & 필요한 데이터 소스(테이블) 결정
    """
    prompt = f"""
    당신은 질문에서 핵심 키워드를 '있는 그대로 추출'하는 AI입니다. (번역/해석 금지)
    질문을 분석하여 분석 대상 매장와 필요한 데이터를 JSON으로 반환하세요.
    
    질문: "{question}"
    
    [추출 규칙]
    
    1. target_store_codes: 분석 대상 매장명 (한글 키워드)
       - ❌ 절대 영어로 번역하지 마세요. (No English Codes like 'SEOUL_GANGNAM')
       - 질문에 있는 단어를 그대로 사용하세요.
       - "강남점 매출" -> ["강남"]
       - "서울이랑 부산 비교" -> ["서울", "부산"]
       - "전체", "모든" -> ["ALL"]
       
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
        "target_store_codes": ["강남"], 
        "required_tables": ["sales_daily", "reviews"],
        "reason": "강남점의 매출 추이와 리뷰를 분석하기 위함"
    }}
    """
    try:
        response = await genai_generate_text(prompt)
        clean_text = response.replace("```json", "").replace("```", "").strip()
        parsed = json.loads(clean_text)
        return parsed
    except:
        return {"target_store_codes": ["ALL"], "required_tables": ["sales_daily", "orders"], "reason": "Error parsing"}

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
        print(f"🕵️ [Debug] DB Stores: {all_stores}") # 실제 DB에 어떻게 저장되어 있는지 확인
        
        # Scope Resolution (AI-Powered Matching)
        if "ALL" in target_store_codes:
            store_codes = [s['store_name'] for s in all_stores]
            target_ids = [s['store_id'] for s in all_stores]
        else:
            # [AI Matcher] 단순 문자열 비교 대신 LLM이 판단 (한글/영어/별칭 완벽 대응)
            match_prompt = f"""
            당신은 데이터 매칭 전문가입니다. 
            사용자가 언급한 '키워드'와 실제 DB에 있는 '매장 목록'을 보고, 의도에 맞는 매장의 ID를 찾아주세요.

            1. 사용자 키워드: {target_store_codes}
            2. DB 매장 목록: {json.dumps(all_stores, ensure_ascii=False)}

            [매칭 규칙]
            - "강남" -> "서울 강남점" (O)
            - "SEOUL" -> "서울 강남점" (O)
            - "본점" -> "서울 강남점" (만약 강남이 본점이라면 문맥상 판단, 불확실하면 Skip)
            - "속초" -> "강원 속초점" (O)
            
            [Output JSON]
            반드시 매칭된 store_id 리스트만 반환하세요.
            {{"matched_ids": [1, 3]}}
            """
            try:
                m_res = await genai_generate_text(match_prompt)
                m_clean = m_res.replace("```json", "").replace("```", "").strip()
                m_data = json.loads(m_clean)
                target_ids = m_data.get("matched_ids", [])
                
                # 매칭된 ID로 이름 리스트 역추적
                store_codes = [s['store_name'] for s in all_stores if s['store_id'] in target_ids]
                print(f"🤖 [AI Matcher] Mapped {target_store_codes} -> IDs: {target_ids} ({store_codes})")
                
            except Exception as e:
                print(f"⚠️ [AI Matcher] Error: {e}")
                # Fallback: 기존 단순 매칭 (안전장치)
                for code in target_store_codes:
                    clean_code = code.replace(" ", "").strip()
                    for s in all_stores:
                        if clean_code and (clean_code in s['store_name'].replace(" ", "") or clean_code in (s['region'] or "")):
                             if s['store_id'] not in target_ids:
                                 target_ids.append(s['store_id'])
                                 store_codes.append(s['store_name'])
                            
        # [UI Fix] 실제 매칭된 매장명 전달 (중요)
        if store_codes:
            collected_data["target_store_name"] = ", ".join(store_codes)
        else:
            collected_data["target_store_name"] = "전체 지점 (식별 실패)" if "ALL" not in target_store_codes else "전체 지점"
        
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
                 """
                 
                 # [Critial Fix] 지점 필터링 누락 수정
                 if target_ids:
                     ids_str_store = ",".join(map(str, target_ids))
                     q_deep += f" AND o.store_id IN ({ids_str_store})"
                     
                 q_deep += " ORDER BY r.created_at DESC"
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
