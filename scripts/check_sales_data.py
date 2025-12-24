import asyncio
import sys
import os

sys.path.append(os.path.dirname(os.path.abspath(os.path.dirname(__file__))))

from app.core.db import fetch_all, init_pool, close_pool

async def main():
    await init_pool()
    try:
        res1 = await fetch_all("SELECT sale_date, total_sales FROM sales_daily WHERE store_id=1 ORDER BY sale_date DESC LIMIT 3")
        res2 = await fetch_all("SELECT sale_date, total_sales FROM sales_daily WHERE store_id=2 ORDER BY sale_date DESC LIMIT 3")
        print(f"Store 1 (Recent 3 days): {res1}")
        print(f"Store 2 (Recent 3 days): {res2}")
    except Exception as e:
        print(f"Error: {e}")
    finally:
        await close_pool()

if __name__ == "__main__":
    asyncio.run(main())
