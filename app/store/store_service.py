from app.core.db import fetch_all

async def select_stores_all():
    sql = "SELECT * FROM stores"
    rows = await fetch_all(sql)
    return rows