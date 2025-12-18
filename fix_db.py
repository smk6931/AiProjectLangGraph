import asyncio
from app.core.db import execute, init_pool, close_pool


async def fix_db():
    await init_pool()
    try:
        # order_id 컬럼 추가
        await execute("ALTER TABLE reviews ADD COLUMN IF NOT EXISTS order_id INTEGER REFERENCES orders(order_id)")
        print("✅ reviews 테이블에 order_id 컬럼이 성공적으로 추가되었습니다.")
    except Exception as e:
        print(f"❌ 오류 발생: {e}")
    finally:
        await close_pool()

if __name__ == "__main__":
    asyncio.run(fix_db())
