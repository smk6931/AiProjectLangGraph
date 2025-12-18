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
        SELECT DATE(ordered_at) as order_date, SUM(total_price) as daily_revenue, COUNT(*) as order_count
        FROM orders
        WHERE store_id = %s
        GROUP BY DATE(ordered_at)
        ORDER BY order_date ASC
    """
    rows = await fetch_all(sql, (store_id,))
    return rows
