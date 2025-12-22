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
STORE_ID = 1
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
        print("🧹 기존 주문/리뷰 데이터 삭제 중...")
        session.execute(text(f"DELETE FROM reviews WHERE store_id = {STORE_ID}"))
        session.execute(text(f"DELETE FROM orders WHERE store_id = {STORE_ID}"))
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

        for d in dates:
            d_str = str(d)
            weather = weather_map.get(d_str, "알수없음")
            weekday = d.weekday() # 0:Mon, 6:Sun
            is_weekend = weekday >= 5
            
            # --- 시뮬레이션 로직 ---
            daily_factor = 1.0
            
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
            
            # (특수 시나리오: 특정 메뉴 급감 연출을 위해 최근 3일간 특정 메뉴 판매 확률을 낮춤)
            # 예: 최근 3일간 '치즈케이크' 재고 부족 시나리오
            is_recent = (today - d).days <= 3
            
            for _ in range(target_count):
                # 메뉴 선택
                if is_recent and random.random() < 0.7: 
                    # 최근엔 커피 위주로만 팔림 (디저트 제외)
                    # 만약 카테고리 정보가 있다면 좋겠지만, 여기선 랜덤하게 일부 메뉴를 제외
                    # 간단히: 메뉴 ID 홀수만 선택 (가정)
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
                
                # 주문 객체 생성 (일단 DB에 넣어서 ID를 받아야 리뷰를 연결할 수 있는데, Bulk Insert라 ID를 모름)
                # 여기선 리뷰 연결을 위해 flush를 쓰거나, 그냥 order_id 없이 review만 store_id로 연결해도 됨 (리뷰 스키마 보니 order_id Nullable임)
                # 하지만 정확성을 위해 하나씩 add하거나 flush? 너무 느림.
                # 그냥 order_id 연결은 생략하거나(null), bulk save 후 id를 가져오는 복잡한 로직 대신
                # 리뷰 생성 시 "어떤 메뉴를 먹었다" 정도만 남김.
                
                new_order = Order(
                    store_id=STORE_ID,
                    menu_id=mid,
                    quantity=qty,
                    total_price=price,
                    ordered_at=order_dt
                )
                orders_to_add.append(new_order)
                
                # 리뷰 생성 확률 (10%)
                if random.random() < 0.1:
                    # 평점 로직
                    if "비" in weather: 
                        # 비오는 날은 배달 늦어서 평점 안좋음
                        rating = random.choices([1, 2, 3, 4, 5], weights=[0.2, 0.2, 0.3, 0.2, 0.1])[0]
                    else:
                        rating = random.choices([3, 4, 5], weights=[0.1, 0.4, 0.5])[0]
                        
                    if rating >= 4:
                        txt = random.choice(POSITIVE_REVIEWS)
                    elif rating == 3:
                        txt = random.choice(NEUTRAL_REVIEWS)
                    else:
                        txt = random.choice(NEGATIVE_REVIEWS)
                    
                    new_review = Review(
                        store_id=STORE_ID,
                        menu_id=mid,
                        rating=rating,
                        review_text=txt,
                        created_at=order_dt + timedelta(hours=1), # 주문 1시간 후
                        delivery_app=random.choice(["배달의민족", "쿠팡이츠", "요기요"])
                    )
                    reviews_to_add.append(new_review)

        # Bulk save
        session.bulk_save_objects(orders_to_add)
        session.bulk_save_objects(reviews_to_add)
        session.commit()
        
        print(f"✅ 생성 완료: 주문 {len(orders_to_add)}건, 리뷰 {len(reviews_to_add)}건")
        print(f"📅 기간: {dates[0]} ~ {dates[-1]}")

if __name__ == "__main__":
    asyncio.run(main())
