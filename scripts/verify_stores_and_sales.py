import asyncio
import sys
import os

sys.path.append(os.path.dirname(os.path.abspath(os.path.dirname(__file__))))

from app.core.db import init_pool, close_pool, fetch_all

async def main():
    await init_pool()
    try:
        # 1. Store ID Mapping Check
        print("--- Store IDs ---")
        stores = await fetch_all("SELECT store_id, store_name, city FROM stores")
        for s in stores:
            print(f"ID {s['store_id']}: {s['store_name']} ({s['city']})")
            
        # 2. Sales Aggregation Check (Last 30 days)
        print("\n--- Sales Data Check (Last 7 days) ---")
        for s in stores:
            sid = s['store_id']
            res = await fetch_all(f"""
                SELECT SUM(total_sales) as sum_sales, SUM(total_orders) as sum_orders 
                FROM sales_daily 
                WHERE store_id = {sid} 
                  AND sale_date >= (CURRENT_DATE - INTERVAL '7 days')
            """)
            row = res[0]
            print(f"ID {sid} ({s['store_name']}): Sales={row['sum_sales']}, Orders={row['sum_orders']}")

    except Exception as e:
        print(f"Error: {e}")
    finally:
        await close_pool()

if __name__ == "__main__":
    asyncio.run(main())
