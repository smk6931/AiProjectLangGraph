import asyncio
import sys
import os
import random

sys.path.append(os.path.dirname(os.path.abspath(os.path.dirname(__file__))))

from app.core.db import init_pool, close_pool, execute

async def main():
    await init_pool()
    try:
        # 광주지점(ID=2로 가정) 데이터 갱신
        # 랜덤하게 매출을 0.8~1.2배로 튀게 만들어서 확실히 다르게 보이게 함
        print("UPDATE Store 2 data...")
        await execute("""
            UPDATE sales_daily 
            SET total_sales = total_sales * (0.5 + random()),
                total_orders = total_orders * (0.5 + random())
            WHERE store_id = 2
        """)
        print("Done.")
    except Exception as e:
        print(f"Error: {e}")
    finally:
        await close_pool()

if __name__ == "__main__":
    asyncio.run(main())
