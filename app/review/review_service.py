from app.core.db import fetch_all


async def select_reviews_by_store(store_id: int):
    sql = """
        SELECT r.*, m.menu_name, o.ordered_at
        FROM reviews r
        JOIN menus m ON r.menu_id = m.menu_id
        LEFT JOIN orders o ON r.order_id = o.order_id
        WHERE r.store_id = %s
        ORDER BY r.created_at DESC
    """
    rows = await fetch_all(sql, (store_id,))
    return rows
