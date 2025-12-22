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


async def select_menu_sales_comparison(store_id: int, days: int = 7):
    """
    최근 N일 vs 이전 N일 메뉴별 판매량/매출 비교
    Args:
        store_id (int): 매장 ID
        days (int): 비교할 기간 (기본 7일)
    """
    sql = """
        SELECT 
            m.menu_name, 
            m.category,
            SUM(CASE WHEN o.ordered_at >= CURRENT_DATE - INTERVAL '%s days' THEN o.total_price ELSE 0 END) as recent_revenue,
            COUNT(CASE WHEN o.ordered_at >= CURRENT_DATE - INTERVAL '%s days' THEN 1 ELSE NULL END) as recent_count,
            SUM(CASE WHEN o.ordered_at < CURRENT_DATE - INTERVAL '%s days' AND o.ordered_at >= CURRENT_DATE - INTERVAL '%s days' THEN o.total_price ELSE 0 END) as prev_revenue,
            COUNT(CASE WHEN o.ordered_at < CURRENT_DATE - INTERVAL '%s days' AND o.ordered_at >= CURRENT_DATE - INTERVAL '%s days' THEN 1 ELSE NULL END) as prev_count
        FROM orders o
        JOIN menus m ON o.menu_id = m.menu_id
        WHERE o.store_id = %s
        AND o.ordered_at >= CURRENT_DATE - INTERVAL '%s days'
        GROUP BY m.menu_name, m.category
        ORDER BY recent_revenue DESC
    """
    # 파라미터 바인딩: days, days, days, 2*days, days, 2*days, store_id, 2*days
    # 주의: SQL string formatting을 사용하거나 파라미터로 넘겨야 함. 
    # 여기서는 %s 포매팅을 사용하므로, 쿼리 내 %s 자리에 값을 순서대로 넣어준다.
    # 하지만 interval 문법이 dialect에 따라 다를 수 있음. Postgres 기준 'INTERVAL '7 days'' 형태.
    # 안전하게 파라미터로 처리하기 위해 쿼리를 조금 수정.
    
    sql = """
        SELECT 
            m.menu_name, 
            m.category,
            COALESCE(SUM(CASE WHEN o.ordered_at >= CURRENT_DATE - make_interval(days => %s) THEN o.total_price ELSE 0 END), 0) as recent_revenue,
            COUNT(CASE WHEN o.ordered_at >= CURRENT_DATE - make_interval(days => %s) THEN 1 ELSE NULL END) as recent_count,
            COALESCE(SUM(CASE WHEN o.ordered_at < CURRENT_DATE - make_interval(days => %s) AND o.ordered_at >= CURRENT_DATE - make_interval(days => %s) THEN o.total_price ELSE 0 END), 0) as prev_revenue,
            COUNT(CASE WHEN o.ordered_at < CURRENT_DATE - make_interval(days => %s) AND o.ordered_at >= CURRENT_DATE - make_interval(days => %s) THEN 1 ELSE NULL END) as prev_count
        FROM orders o
        JOIN menus m ON o.menu_id = m.menu_id
        WHERE o.store_id = %s
        AND o.ordered_at >= CURRENT_DATE - make_interval(days => %s)
        GROUP BY m.menu_name, m.category
        ORDER BY recent_revenue DESC
    """
    
    # recent(days), recent(days), prev_start(days), prev_end(days*2), prev_start(days), prev_end(days*2), store_id, limit(days*2)
    params = (days, days, days, days * 2, days, days * 2, store_id, days * 2)
    
    rows = await fetch_all(sql, params)
    return rows


async def select_sales_by_day_type(store_id: int, days: int = 7):
    """
    최근 N일 vs 이전 N일의 '평일(Weekday)' vs '주말(Weekend)' 매출 비교
    """
    sql = """
        SELECT 
            CASE WHEN EXTRACT(ISODOW FROM ordered_at) IN (6, 7) THEN 'Weekend' ELSE 'Weekday' END as day_type,
            
            SUM(CASE WHEN ordered_at >= CURRENT_DATE - make_interval(days => %s) THEN total_price ELSE 0 END) as recent_revenue,
            COUNT(CASE WHEN ordered_at >= CURRENT_DATE - make_interval(days => %s) THEN 1 ELSE NULL END) as recent_count,
            
            SUM(CASE WHEN ordered_at < CURRENT_DATE - make_interval(days => %s) AND ordered_at >= CURRENT_DATE - make_interval(days => %s) THEN total_price ELSE 0 END) as prev_revenue,
            COUNT(CASE WHEN ordered_at < CURRENT_DATE - make_interval(days => %s) AND ordered_at >= CURRENT_DATE - make_interval(days => %s) THEN 1 ELSE NULL END) as prev_count
        
        FROM orders
        WHERE store_id = %s
        AND ordered_at >= CURRENT_DATE - make_interval(days => %s)
        GROUP BY 1
    """
    params = (days, days, days, days * 2, days, days * 2, store_id, days * 2)
    rows = await fetch_all(sql, params)
    return rows
