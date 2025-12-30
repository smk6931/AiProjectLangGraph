from app.core.db import fetch_all


async def select_orders_by_store(store_id: int):
    sql = """
        SELECT o.*, m.menu_name, m.category
        FROM orders o
        JOIN menus m ON o.menu_id = m.menu_id
        WHERE o.store_id = %s
        ORDER BY o.ordered_at DESC
    """
    rows = await fetch_all(sql, (store_id,))
    return rows


async def select_daily_sales_by_store(store_id: int):
    sql = """
        SELECT sale_date as order_date, total_sales as daily_revenue, total_orders as order_count, COALESCE(weather_info, '알수없음') as weather_info
        FROM sales_daily
        WHERE store_id = %s
        ORDER BY sale_date ASC
    """
    rows = await fetch_all(sql, (store_id,))
    return rows


async def select_menu_sales_comparison(store_id: int, days: int = 7, target_date: str = None):
    """
    최근 N일 vs 이전 N일 메뉴별 판매량/매출 비교
    Args:
        store_id (int): 매장 ID
        days (int): 비교할 기간 (기본 7일)
        target_date (str): 기준 날짜 (YYYY-MM-DD), 없으면 CURRENT_DATE 사용
    """
    # 기준 날짜 처리 (SQL Injection 방지를 위해 파라미터 바인딩 사용)
    base_date_expr = "CAST(%s AS DATE)" if target_date else "CURRENT_DATE"

    sql = f"""
        SELECT 
            m.menu_name, 
            m.category,
            COALESCE(SUM(CASE WHEN o.ordered_at >= {base_date_expr} - make_interval(days => %s) AND o.ordered_at < {base_date_expr} + interval '1 day' THEN o.total_price ELSE 0 END), 0) as recent_revenue,
            COUNT(CASE WHEN o.ordered_at >= {base_date_expr} - make_interval(days => %s) AND o.ordered_at < {base_date_expr} + interval '1 day' THEN 1 ELSE NULL END) as recent_count,
            COALESCE(SUM(CASE WHEN o.ordered_at < {base_date_expr} - make_interval(days => %s) AND o.ordered_at >= {base_date_expr} - make_interval(days => %s) THEN o.total_price ELSE 0 END), 0) as prev_revenue,
            COUNT(CASE WHEN o.ordered_at < {base_date_expr} - make_interval(days => %s) AND o.ordered_at >= {base_date_expr} - make_interval(days => %s) THEN 1 ELSE NULL END) as prev_count
        FROM orders o
        JOIN menus m ON o.menu_id = m.menu_id
        WHERE o.store_id = %s
        AND o.ordered_at >= {base_date_expr} - make_interval(days => %s)
        AND o.ordered_at < {base_date_expr} + interval '1 day'
        GROUP BY m.menu_name, m.category
        ORDER BY recent_revenue DESC
    """
    
    # 파라미터 리스트 구성
    # target_date가 있으면 SQL 앞부분에 바인딩 필요
    # 순서: (target_date...) -> days -> (target_date...) ...
    # 복잡하므로, target_date를 params에 n번 넣어주는 방식보다는
    # f-string으로 base_date_expr를 넣었지만, 안전하게 파라미터로 처리하려면 로직이 복잡해짐.
    # 여기서는 target_date가 검증된 YYYY-MM-DD 문자열이라고 가정하고,
    # 쿼리 파라미터 순서를 맞추는 정공법 사용.
    
    # Parameter order depends on how many times base_date_expr appears with %s.
    # If target_date is None, base_date_expr is "CURRENT_DATE" (no param).
    # If target_date is set, base_date_expr is "CAST(%s AS DATE)" (1 param).
    
    # Let's simplify: Use a CTE or variable in logic? No, simple param construction.
    
    p_date = [target_date] if target_date else []
    
    # Params corresponding to the SQL placeholders (%s)
    # 1. recent_rev start: days
    # 2. recent_cnt start: days
    # 3. prev_rev end: days, start: days*2
    # 4. prev_cnt end: days, start: days*2
    # 5. WHERE store_id
    # 6. WHERE start: days*2
    
    # Wait, because of base_date_expr expansion, we need to inject params properly.
    # If target_date:
    # SELECT ... CASE WHEN ... >= CAST(%s AS DATE) - ...
    # This interleaving is tricky.
    
    # Alternative: Use a WITH clause to define the anchor date once.
    
    sql = """
        WITH anchor AS (
            SELECT CAST(%s AS DATE) as ref_date
        )
        SELECT 
            m.menu_name, 
            m.category,
            COALESCE(SUM(CASE WHEN o.ordered_at >= (SELECT ref_date FROM anchor) - make_interval(days => %s) 
                              AND o.ordered_at < (SELECT ref_date FROM anchor) + interval '1 day' THEN o.total_price ELSE 0 END), 0) as recent_revenue,
            COUNT(CASE WHEN o.ordered_at >= (SELECT ref_date FROM anchor) - make_interval(days => %s) 
                              AND o.ordered_at < (SELECT ref_date FROM anchor) + interval '1 day' THEN 1 ELSE NULL END) as recent_count,
            COALESCE(SUM(CASE WHEN o.ordered_at < (SELECT ref_date FROM anchor) - make_interval(days => %s) 
                              AND o.ordered_at >= (SELECT ref_date FROM anchor) - make_interval(days => %s) THEN o.total_price ELSE 0 END), 0) as prev_revenue,
            COUNT(CASE WHEN o.ordered_at < (SELECT ref_date FROM anchor) - make_interval(days => %s) 
                              AND o.ordered_at >= (SELECT ref_date FROM anchor) - make_interval(days => %s) THEN 1 ELSE NULL END) as prev_count
        FROM orders o
        JOIN menus m ON o.menu_id = m.menu_id
        WHERE o.store_id = %s
        AND o.ordered_at >= (SELECT ref_date FROM anchor) - make_interval(days => %s)
        AND o.ordered_at < (SELECT ref_date FROM anchor) + interval '1 day'
        GROUP BY m.menu_name, m.category
        ORDER BY recent_revenue DESC
    """
    
    # If target_date is None, use current date string
    if not target_date:
        from datetime import date
        target_date = str(date.today())
        
    # Query structure analysis:
    # 1. WITH anchor: %s (target_date)
    # 2. recent_rev: %s (days)
    # 3. recent_cnt: %s (days)
    # 4. prev_rev: %s (days), %s (days*2)
    # 5. prev_cnt: %s (days), %s (days*2)
    # 6. WHERE store_id: %s
    # 7. WHERE start: %s (days*2)
    
    params = (target_date, days, days, days, days * 2, days, days * 2, store_id, days * 2)
    
    rows = await fetch_all(sql, params)
    return rows


async def select_sales_by_day_type(store_id: int, days: int = 7, target_date: str = None):
    """
    최근 N일 vs 이전 N일의 '평일(Weekday)' vs '주말(Weekend)' 매출 비교
    """
    if not target_date:
        from datetime import date
        target_date = str(date.today())

    sql = """
        WITH anchor AS (
            SELECT CAST(%s AS DATE) as ref_date
        )
        SELECT 
            CASE WHEN EXTRACT(ISODOW FROM ordered_at) IN (6, 7) THEN 'Weekend' ELSE 'Weekday' END as day_type,
            
            SUM(CASE WHEN ordered_at >= (SELECT ref_date FROM anchor) - make_interval(days => %s) 
                     AND ordered_at < (SELECT ref_date FROM anchor) + interval '1 day' THEN total_price ELSE 0 END) as recent_revenue,
            COUNT(CASE WHEN ordered_at >= (SELECT ref_date FROM anchor) - make_interval(days => %s) 
                     AND ordered_at < (SELECT ref_date FROM anchor) + interval '1 day' THEN 1 ELSE NULL END) as recent_count,
            
            SUM(CASE WHEN ordered_at < (SELECT ref_date FROM anchor) - make_interval(days => %s) 
                     AND ordered_at >= (SELECT ref_date FROM anchor) - make_interval(days => %s) THEN total_price ELSE 0 END) as prev_revenue,
            COUNT(CASE WHEN ordered_at < (SELECT ref_date FROM anchor) - make_interval(days => %s) 
                     AND ordered_at >= (SELECT ref_date FROM anchor) - make_interval(days => %s) THEN 1 ELSE NULL END) as prev_count
        
        FROM orders
        WHERE store_id = %s
        AND ordered_at >= (SELECT ref_date FROM anchor) - make_interval(days => %s)
        AND ordered_at < (SELECT ref_date FROM anchor) + interval '1 day'
        GROUP BY 1
    """
    
    # Query structure analysis:
    # 1. WITH anchor: %s (target_date)
    # 2. recent_rev: %s (days)
    # 3. recent_cnt: %s (days)
    # 4. prev_rev: %s (days), %s (days*2)
    # 5. prev_cnt: %s (days), %s (days*2)
    # 6. WHERE store_id: %s
    # 7. WHERE start: %s (days*2)
    
    params = (target_date, days, days, days, days * 2, days, days * 2, store_id, days * 2)
    rows = await fetch_all(sql, params)
    return rows
