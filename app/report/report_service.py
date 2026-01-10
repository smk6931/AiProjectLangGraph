import json
import asyncio
import time
import traceback

from datetime import date, datetime, timedelta
from sqlalchemy import func
from app.core.db import SessionLocal, fetch_all
from app.report.report_schema import StoreReport
from app.clients.genai import genai_generate_text
from app.order.order_service import select_daily_sales_by_store
from app.review.review_service import select_reviews_by_store
from app.core.cache import get_report_cache, set_report_cache, get_report_object_cache
from app.report.report_graph import report_graph_app


# ------------------------------------------------------------------
# [Portfolio] Redis vs DB Speed Race Helper Functions (Flattened)
# ------------------------------------------------------------------

async def _measure_redis_speed(s_id: int, check_date: date):
    """Redis 조회 속도 측정"""
    start = time.perf_counter()
    data = await get_report_cache(s_id, check_date)
    dur = time.perf_counter() - start
    return dur, data


async def _measure_db_speed(s_id: int, check_date: date):
    """DB 조회 속도 측정"""
    start = time.perf_counter()
    row = await select_latest_report(s_id)
    data = None
    if row and str(row['report_date']) == str(check_date):
        data = row
    dur = time.perf_counter() - start
    return dur, data


async def race_condition_check(s_id: int, t_date: str):
    """
    Redis와 DB의 조회 속도를 경쟁(Race)시키는 메인 로직.
    asyncio.gather를 사용하여 두 태스크를 동시에 실행함.
    """
    logs = []
    
    if t_date:
        check_date = datetime.strptime(t_date, "%Y-%m-%d").date()
    else:
        check_date = date.today()

    # Async Execution (Race Start!) 🔫
    # 헬퍼 함수들을 동시에 호출
    (redis_time, redis_data), (db_time, db_data) = await asyncio.gather(
        _measure_redis_speed(s_id, check_date), 
        _measure_db_speed(s_id, check_date)
    )
    
    data_found = redis_data if redis_data else db_data
    
    # 데이터가 어딘가에 있다면 Race Log 생성
    if data_found:
        winner = "Redis" if redis_time < db_time else "DB"
        gap = db_time / redis_time if redis_time > 0 else 99.9
        
        logs.append(f"🏎️ [Race] {winner} Win! (Redis: {redis_time:.4f}s vs DB: {db_time:.4f}s)")
        logs.append(f"⚡ [속도 비교] Redis가 DB보다 {gap:.1f}배 더 빠릅니다!")
        
        # DB 데이터만 있는 경우 포맷 맞춤 (UI 호환성)
        if not redis_data and db_data:
                # DB Row를 Dict 구조로 감싸기
                data_found = {"report": db_data, "logs": [], "mode": "sequential"}

    return data_found, logs


# ------------------------------------------------------------------
# Main Service Function
# ------------------------------------------------------------------

async def generate_ai_store_report(store_id: int, store_name: str, mode: str = "sequential", target_date: str = None):
    """
    LangGraph 프로세스 실행 (Sequential Graph)
    캐시 확인 → 없으면 생성 → 캐시 저장
    """
    try:
        print(f"🚀 [Service] '{store_name}' 리포트 생성 시작 ({target_date if target_date else 'Today'})...")

        # 1. [Race] 캐시/DB 경쟁 조회 (Flattened 구조)
        cached_data, race_logs = await race_condition_check(store_id, target_date)
        
        if cached_data:
            print(f"♻️ [Service] '{store_name}' 리포트 조회 성공! (Race Winner Logic)")
            
            # 기존 로그에 레이스 로그 병합
            final_logs = race_logs + cached_data.get("logs", [])
            cached_data["logs"] = final_logs
            cached_data["cached"] = True
            return cached_data

        # 2. 리포트 생성 (데이터 없음 -> AI 실행)
        initial_state = {
            "store_id": store_id,
            "store_name": store_name,
            "target_date": target_date, # [NEW] 분석 대상 날짜
            "execution_logs": race_logs # Race 결과(없음)도 로그에 남김
        }

        # LangGraph 실행 (미리 컴파일된 싱글톤 앱 사용)
        final_state = await report_graph_app.ainvoke(initial_state)

        # DB에서 저장된 리포트 조회
        report = await select_latest_report(store_id)

        # 실행 로그 수집
        logs = race_logs + final_state.get("execution_logs", [])

        result = {
            "report": report,
            "logs": logs,
            "mode": mode,
            "cached": False
        }

        # 3. 생성된 리포트를 캐시에 저장 (Redis + DB는 이미 위에서 됨)
        # target_date가 있으면 그걸로, 없으면 오늘 날짜로 key 생성
        save_date = datetime.strptime(target_date, "%Y-%m-%d").date() if target_date else date.today()
        
        # [Prevent Caching Bad Data] 불량 리포트(Risk Score=0)는 Redis 저장 건너뛰기
        risk_check = report.get("risk_assessment") if report else None
        risk_score = risk_check.get("risk_score") if risk_check else 0
        
        if risk_score and risk_score > 0:
            await set_report_cache(store_id, result, save_date)
        else:
            print("⚠️ [Cache Skip] 불량 리포트라 Redis 캐싱을 생략합니다.")

        return result

    except Exception as e:
        print(f"❌ [Service] 에러 발생: {str(e)}")
        traceback.print_exc()
        return None


async def select_latest_report(store_id: int):
    """
    지점의 가장 최신 리포트 조회 (DB Only)
    """
    sql = "SELECT * FROM store_reports WHERE store_id = %s ORDER BY report_date DESC, report_id DESC LIMIT 1"
    rows = await fetch_all(sql, (store_id,))
    return rows[0] if rows else None
