from app.core.db import fetch_all


async def select_menus_all():
    sql = "SELECT * FROM menus"
    rows = await fetch_all(sql)
    return rows
