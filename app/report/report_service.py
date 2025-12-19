import json
from datetime import date, datetime, timedelta
from sqlalchemy import func
from app.core.db import SessionLocal, fetch_all
from app.report.report_schema import StoreReport
from app.clients.genai import genai_generate_text
from app.order.order_service import select_daily_sales_by_store
from app.review.review_service import select_reviews_by_store

from app.report.report_graph import report_app

async def generate_ai_store_report(store_id: int, store_name: str):
    """
    LangGraph 기반의 AI 전략 리포트 생성 워크플로우 실행
    """
    initial_state = {
        "store_id": store_id,
        "store_name": store_name,
        "sales_data": [],
        "reviews_data": [],
        "raw_report_json": "",
        "final_report": {}
    }
    
    try:
        # 그래프 실행
        final_state = await report_app.ainvoke(initial_state)
        
        # UI에서 사용하기 좋게 결과 가공
        report_dict = final_state["final_report"]
        report_dict["store_id"] = store_id
        report_dict["report_date"] = str(date.today())
        
        return report_dict
        
    except Exception as e:
        print(f"❌ LangGraph 실행 실패: {e}")
        return None

    except Exception as e:
        print(f"❌ 리포트 생성 실패: {e}")
        return None

async def select_latest_report(store_id: int):
    """
    지점의 가장 최신 리포트 조회
    """
    sql = "SELECT * FROM store_reports WHERE store_id = %s ORDER BY report_date DESC, report_id DESC LIMIT 1"
    rows = await fetch_all(sql, (store_id,))
    return rows[0] if rows else None
