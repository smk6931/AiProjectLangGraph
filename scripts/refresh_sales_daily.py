import sys
import os
import asyncio
from sqlalchemy import text
import subprocess

# 프로젝트 루트 경로 추가
sys.path.append(os.getcwd())

from app.core.db import SessionLocal

def main():
    print("🚀 Sales Data Refresh Process Started")
    
    # 1. sales_daily 테이블 초기화 (기존 데이터 삭제)
    print("\n🧹 1. Clearing 'sales_daily' table...")
    with SessionLocal() as session:
        try:
            # PostgreSQL에서 테이블 비우기
            session.execute(text("TRUNCATE TABLE sales_daily RESTART IDENTITY CASCADE"))
            session.commit()
            print("✅ 'sales_daily' table cleared successfully.")
        except Exception as e:
            print(f"⚠️ Error clearing table (trying DELETE): {e}")
            session.rollback()
            try:
                session.execute(text("DELETE FROM sales_daily"))
                session.commit()
                print("✅ 'sales_daily' records deleted successfully.")
            except Exception as e2:
                print(f"❌ Failed to clear table: {e2}")
                return

    # 2. 집계 스크립트 실행 (aggregate_sales_and_weather.py)
    print("\n🔄 2. Running aggregation script (Orders -> SalesDaily)...")
    try:
        result = subprocess.run(
            [sys.executable, "scripts/aggregate_sales_and_weather.py"],
            capture_output=False,
            text=True,
            check=True
        )
        print("✅ Aggregation script finished.")
    except subprocess.CalledProcessError as e:
        print(f"❌ Aggregation script failed: {e}")

    print("\n🎉 All Done! Please refresh the dashboard.")

if __name__ == "__main__":
    main()
