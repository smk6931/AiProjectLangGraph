import json
from datetime import date, datetime, timedelta
from sqlalchemy import func
from app.core.db import SessionLocal, fetch_all
from app.report.report_schema import StoreReport
from app.clients.genai import genai_generate_text
from app.order.order_service import select_daily_sales_by_store
from app.review.review_service import select_reviews_by_store
from app.core.cache import get_report_cache, set_report_cache, get_report_object_cache

from app.report.report_graph import create_report_graph


async def generate_ai_store_report(store_id: int, store_name: str, mode: str = "sequential"):
    """
    LangGraph 프로세스 실행 (Sequential Graph)
    캐시 확인 → 없으면 생성 → 캐시 저장
    """
    try:
        print(f"🚀 [Service] '{store_name}' 리포트 생성 시작...")

        today = date.today()

        # 1. 캐시 확인
        # cached_report = await get_report_cache(store_id, today)
        # if cached_report:
        #     cached_report["mode"] = mode
        #     return cached_report

        # 2. 캐시 없으면 리포트 생성
        initial_state = {
            "store_id": store_id,
            "store_name": store_name,
            "messages": [],
            "execution_logs": []
        }

        # LangGraph 실행 (순차적 그래프 고정)
        final_state = await create_report_graph().ainvoke(initial_state)

        # DB에서 저장된 리포트 조회
        report = await select_latest_report(store_id)

        # 실행 로그 수집
        logs = final_state.get("execution_logs", [])

        result = {
            "report": report,
            "logs": logs,
            "mode": mode,
            "cached": False
        }

        # 3. 생성된 리포트를 캐시에 저장
        await set_report_cache(store_id, result, today)

        return result

    except Exception as e:
        print(f"❌ [Service] 에러 발생: {str(e)}")
        return None


async def select_latest_report(store_id: int):
    """
    지점의 가장 최신 리포트 조회
    캐시 확인 → 없으면 DB 조회
    """
    from datetime import date
    
    # 1. 캐시 확인 (오늘 날짜 리포트)
    # today = date.today()
    # cached_report = await get_report_object_cache(store_id, today)
    # if cached_report:
    #     return cached_report
    
    # 2. 캐시 없으면 DB 조회
    sql = "SELECT * FROM store_reports WHERE store_id = %s ORDER BY report_date DESC, report_id DESC LIMIT 1"
    rows = await fetch_all(sql, (store_id,))
    return rows[0] if rows else None
