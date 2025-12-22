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
STORE_ID = 1

async def main():
    print("🚀 일별 매출 집계 및 날씨 정보 병합 시작...")

    with SessionLocal() as session:
        # 1. DB 스키마 마이그레이션 (임시)
        # weather_info 컬럼 없으면 추가
        try:
            session.execute(text("ALTER TABLE sales_daily ADD COLUMN weather_info VARCHAR(50)"))
            session.commit()
            print("✅ 'weather_info' 컬럼 추가 완료")
        except Exception:
            session.rollback()
            print("ℹ️ 'weather_info' 컬럼이 이미 존재하거나 추가에 실패했습니다.")

        # 2. 집계할 주문 데이터 조회 (최근 30일)
        today = date.today()
        start_date = today - timedelta(days=35) # 여유있게

        print(f"📅 {start_date} 이후 데이터 집계 중...")

        # 날짜별 매출/주문수 집계
        # SELECT DATE(ordered_at), SUM(total_price), COUNT(*) FROM orders ... GROUP BY DATE(...)
        results = session.query(
            func.date(Order.ordered_at).label("order_date"),
            func.sum(Order.total_price).label("total_rev"),
            func.count(Order.order_id).label("total_cnt")
        ).filter(
            Order.store_id == STORE_ID,
            Order.ordered_at >= start_date
        ).group_by(
            func.date(Order.ordered_at)
        ).all()

        if not results:
            print("❌ 집계할 주문 데이터가 없습니다.")
            return

        # 3. 날씨 데이터 조회
        dates_to_fetch = [r.order_date for r in results]
        print(f"🌤️ {min(dates_to_fetch)} ~ {max(dates_to_fetch)} 날씨 API 조회...")
        weather_map = await fetch_weather_data(dates_to_fetch)

        # 4. SalesDaily 테이블 업데이트 (Upsert)
        for row in results:
            # row.order_date, row.total_rev, row.total_cnt
            curr_date = row.order_date
            weather = weather_map.get(str(curr_date), "알수없음")
            
            # 기존 레코드 확인
            daily_record = session.query(SalesDaily).filter_by(
                store_id=STORE_ID, 
                sale_date=curr_date
            ).first()
            
            if daily_record:
                daily_record.total_sales = row.total_rev
                daily_record.total_orders = row.total_cnt
                daily_record.weather_info = weather
            else:
                new_record = SalesDaily(
                    store_id=STORE_ID,
                    sale_date=curr_date,
                    total_sales=row.total_rev,
                    total_orders=row.total_cnt,
                    weather_info=weather
                )
                session.add(new_record)
        
        session.commit()
        print(f"✅ {len(results)}일치 매출/날씨 데이터 갱신 완료!")

if __name__ == "__main__":
    asyncio.run(main())
