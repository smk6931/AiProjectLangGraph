import json
from datetime import date, datetime, timedelta
from sqlalchemy import func
from app.core.db import SessionLocal, fetch_all
from app.report.report_schema import StoreReport
from app.clients.genai import genai_generate_text
from app.order.order_service import select_daily_sales_by_store
from app.review.review_service import select_reviews_by_store

from app.report.report_autonomous import autonomous_report_app


async def generate_ai_store_report(store_id: int, store_name: str):
    """
    LangGraph 에이전트 기반의 자율형 리포트 생성 프로세스 실행
    """
    initial_state = {
        "store_id": store_id,
        "store_name": store_name,
        "messages": []
    }

    try:
        # 에이전트 실행
        await autonomous_report_app.ainvoke(initial_state)

        # 결과 조회
        report = await select_latest_report(store_id)
        if report:
            print(f"✅ [Service] 리포트 생성 완료")
            return report
        return None

    except Exception as e:
        print(f"❌ [Service] 에러 발생: {e}")
        return None


async def select_latest_report(store_id: int):
    """
    지점의 가장 최신 리포트 조회
    """
    sql = "SELECT * FROM store_reports WHERE store_id = %s ORDER BY report_date DESC, report_id DESC LIMIT 1"
    rows = await fetch_all(sql, (store_id,))
    return rows[0] if rows else None
