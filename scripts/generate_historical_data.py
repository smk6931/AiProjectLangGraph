import asyncio
import random
from datetime import date, timedelta, datetime
import sys
import os

# Add project root to path
sys.path.append(os.getcwd())

from sqlalchemy import text
from app.core.db import SessionLocal
from app.order.order_schema import Order
from app.review.review_schema import Review
from app.menu.menu_schema import Menu
from app.clients.weather import fetch_weather_data

# ----- Config -----
# ----- Config -----
STORE_IDS = [1, 2, 3] # 서울, 부산, 강원
DAYS_TO_GENERATE = 30
BASE_DAILY_ORDERS = 40  # 일 평균 주문 수

# 리뷰 텍스트 템플릿
POSITIVE_REVIEWS = ["맛있어요", "최고에요", "사장님이 친절해요", "매장이 깔끔해요", "재주문 의사 100%", "커피 향이 좋아요", "디저트 맛집 인정"]
NEUTRAL_REVIEWS = ["무난해요", "그냥 그래요", "보통입니다", "나쁘지 않아요", "배달이 조금 늦었지만 맛은 괜찮아요"]
NEGATIVE_REVIEWS = ["너무 늦게 왔어요", "디저트가 다 부서져서 옴", "맛이 변한 것 같아요", "커피가 식어서 왔어요", "별로에요"]

async def main():
    print(f"🚀 {DAYS_TO_GENERATE}일치 과거 데이터(주문/리뷰) 생성 시작...")
    
    with SessionLocal() as session:
        # 0. 기존 데이터 초기화 (Orders, Reviews only)
        # SalesDaily는 나중에 다시 채울 것이므로 일단 놔두거나 같이 지워야 함. 
        # 사용자가 "SalesDaily는 아직 정리 안했다"고 했으므로 Orders/Reviews만 다시 만듦.
        print("🧹 기존 주문/리뷰 데이터 전체 삭제 중...")
        session.execute(text("DELETE FROM reviews"))
        session.execute(text("DELETE FROM orders"))
        session.commit()

        # 1. 메뉴 정보 가져오기
        menus = session.query(Menu).all()
        if not menus:
            print("❌ 메뉴 데이터가 없습니다. 메뉴부터 생성해주세요.")
            return
        
        menu_map = {m.menu_id: m for m in menus}
        menu_ids = list(menu_map.keys())

        # 2. 날짜 및 날씨 준비
        today = date.today()
        dates = [today - timedelta(days=i) for i in range(1, DAYS_TO_GENERATE + 1)] # 어제부터 30일 전까지
        dates.sort()
        
        print(f"🌤️ {dates[0]} ~ {dates[-1]} 날씨 데이터 조회 중...")
        # 실제 날씨 API 호출 (비동기)
        weather_map = await fetch_weather_data(dates)
        
        orders_to_add = []
        reviews_to_add = []
        
        total_order_count = 0

        # 3. 매장별 데이터 생성 Loop
        for store_id in STORE_IDS:
            print(f"🏢 Store {store_id} 데이터 생성 중...")
            
            for d in dates:
                d_str = str(d)
                weather = weather_map.get(d_str, "알수없음")
                weekday = d.weekday() # 0:Mon, 6:Sun
                is_weekend = weekday >= 5
                
                # --- 시뮬레이션 로직 ---
                daily_factor = 1.0
                
                # 매장별 변수 (부산은 주말에 더 잘됨, 강원은 평일 비수기 등)
                if store_id == 2: # 부산
                    daily_factor *= 1.2
                elif store_id == 3: # 강원
                    daily_factor *= 0.9

                # 1) 요일 가중치
                if is_weekend:
                    daily_factor *= 1.3  # 주말엔 30% 더 잘됨
                
                # 2) 날씨 가중치
                if "비" in weather or "뇌우" in weather:
                    daily_factor *= 0.6  # 비오면 40% 감소
                elif "눈" in weather:
                    daily_factor *= 0.5  # 눈오면 50% 감소
                elif "맑음" in weather:
                    daily_factor *= 1.1  # 맑으면 10% 증가
                
                # 최종 주문 수 결정
                target_count = int(BASE_DAILY_ORDERS * daily_factor * random.uniform(0.9, 1.1))
                
                # (특수 시나리오: 최근 3일간 특정 메뉴 판매 확률을 낮춤)
                is_recent = (today - d).days <= 3
                
                for _ in range(target_count):
                    # 메뉴 선택
                    if is_recent and random.random() < 0.7: 
                        mid = random.choice([m for m in menu_ids if m % 2 != 0]) 
                    else:
                        mid = random.choice(menu_ids)
                    
                    menu = menu_map[mid]
                    qty = random.choices([1, 2, 3], weights=[0.7, 0.2, 0.1])[0]
                    price = (menu.list_price or 5000) * qty
                    
                    # 시간 랜덤 (11시~20시)
                    hour = random.randint(11, 20)
                    minute = random.randint(0, 59)
                    order_dt = datetime.combine(d, datetime.min.time()).replace(hour=hour, minute=minute)
                    
                    new_order = Order(
                        store_id=store_id, # Loop 변수 사용
                        menu_id=mid,
                        quantity=qty,
                        total_price=price,
                        ordered_at=order_dt
                    )
                    orders_to_add.append(new_order)
                    
                    # (리뷰 생성 로직은 seed_reviews_monthly.py가 담당하므로 여기선 생략해도 되지만, 
                    #  원래 코드 흐름 유지 차원에서 냅둠. 단, 나중에 seed_reviews가 덮어쓸 것임)
                    #  ... (생략) ... 
                    #  Generate Review Logic (Optional here, since we will overwrite)
                    #  But keeping it simple, let's just create Orders here.
                    #  Reviews generated here are DUMMY. User will overwrite them.


        # Bulk save
        session.bulk_save_objects(orders_to_add)
        session.bulk_save_objects(reviews_to_add)
        session.commit()
        
        print(f"✅ 생성 완료: 주문 {len(orders_to_add)}건, 리뷰 {len(reviews_to_add)}건")
        print(f"📅 기간: {dates[0]} ~ {dates[-1]}")

if __name__ == "__main__":
    asyncio.run(main())
