import asyncio
import os
import sys

# 프로젝트 루트 경로 추가
sys.path.append(os.getcwd())

from app.core.db import execute, fetch_all, init_pool, close_pool

async def cleanup_table():
    await init_pool() # Connection Pool 초기화 필수
    
    print("🗑️ 'review_analysis' 테이블 삭제 시도 중...")
    try:
        # CASCADE 옵션으로 연관된 객체까지 강제 삭제
        await execute("DROP TABLE IF EXISTS review_analysis CASCADE;")
        print("✅ DROP 쿼리 실행 완료.")
    except Exception as e:
        print(f"❌ 테이블 삭제 중 오류: {e}")

    # 검증
    print("🔎 테이블 존재 여부 확인 중...")
    check_query = """
    SELECT table_name 
    FROM information_schema.tables 
    WHERE table_schema = 'public' 
    AND table_name = 'review_analysis';
    """
    result = await fetch_all(check_query)
    
    if not result:
        print("🎉 확인 결과: 'review_analysis' 테이블이 완전히 삭제되었습니다! (Result: None)")
    else:
        print(f"⚠️ 경고: 테이블이 아직 존재합니다: {result}")
        
    await close_pool()

if __name__ == "__main__":
    if os.name == 'nt':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(cleanup_table())
