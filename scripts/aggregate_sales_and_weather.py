import asyncio
import sys
import os
from datetime import date, timedelta
from sqlalchemy import text, func

# Add project root to path
sys.path.append(os.getcwd())

from app.core.db import SessionLocal
from app.order.order_schema import Order
from app.sales.sales_schema import SalesDaily
from app.clients.weather import fetch_weather_data

# ----- Config -----
# STORE_ID = 1  <-- 제거 (모든 매장 대상)

async def main():
    print("🚀 일별 매출 집계 및 날씨 정보 병합 시작 (전체 매장)...")

    with SessionLocal() as session:
        # 1. DB 스키마 마이그레이션 (임시)
        try:
            session.execute(text("ALTER TABLE sales_daily ADD COLUMN weather_info VARCHAR(50)"))
            session.commit()
            print("✅ 'weather_info' 컬럼 추가 완료")
        except Exception:
            session.rollback()
            print("ℹ️ 'weather_info' 컬럼 확인 완료")

        # 2. 집계할 주문 데이터 조회 (최근 30일)
        today = date.today()
        start_date = today - timedelta(days=35) 

        print(f"📅 {start_date} 이후 데이터 집계 중...")

        # 날짜별/매장별 매출/주문수 집계
        results = session.query(
            Order.store_id,
            func.date(Order.ordered_at).label("order_date"),
            func.sum(Order.total_price).label("total_rev"),
            func.count(Order.order_id).label("total_cnt")
        ).filter(
            Order.ordered_at >= start_date
        ).group_by(
            Order.store_id,
            func.date(Order.ordered_at)
        ).all()

        if not results:
            print("❌ 집계할 주문 데이터가 없습니다.")
            return

        # 3. 날씨 데이터 조회 (모든 날짜 한 번에 조회 - 서울 기준)
        # TODO: 매장별 위/경도 적용은 추후 개선 (현재는 기본값 서울)
        dates_to_fetch = list(set([r.order_date for r in results]))
        print(f"🌤️ 날씨 API 조회 ({len(dates_to_fetch)}일치)...")
        weather_map = await fetch_weather_data(dates_to_fetch)

        # 4. SalesDaily 테이블 업데이트 (Upsert)
        count = 0
        for row in results:
            curr_date = row.order_date
            weather = weather_map.get(str(curr_date), "알수없음")
            
            # 기존 레코드 확인
            daily_record = session.query(SalesDaily).filter_by(
                store_id=row.store_id, 
                sale_date=curr_date
            ).first()
            
            if daily_record:
                daily_record.total_sales = row.total_rev
                daily_record.total_orders = row.total_cnt
                daily_record.weather_info = weather
            else:
                new_record = SalesDaily(
                    store_id=row.store_id,
                    sale_date=curr_date,
                    total_sales=row.total_rev,
                    total_orders=row.total_cnt,
                    weather_info=weather
                )
                session.add(new_record)
            count += 1
        
        session.commit()
        print(f"✅ 총 {count}건의 일별 매출 데이터가 갱신되었습니다!")

if __name__ == "__main__":
    asyncio.run(main())
