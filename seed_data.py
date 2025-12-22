import asyncio
import random
from datetime import datetime, date, timedelta
from faker import Faker
from sqlalchemy import select, delete
from app.core.db import SessionLocal, init_pool, close_pool
from app.store.store_schema import Store
from app.menu.menu_schema import Menu
from app.review.review_schema import Review
from app.order.order_schema import Order
from app.sales.sales_schema import SalesDaily
from app.report.report_schema import StoreReport

fake = Faker('ko_KR')

# --- 데이터 설정 ---
STORES_DATA = [
    {"name": "강남본점", "region": "서울", "city": "서울 강남구", "lat": 37.4979, "lon": 127.0276},
    {"name": "홍대입구점", "region": "서울", "city": "서울 마포구", "lat": 37.5575, "lon": 126.9245},
    {"name": "여의도점", "region": "서울", "city": "서울 영등포구", "lat": 37.5219, "lon": 126.9242},
    {"name": "판교점", "region": "경기", "city": "성남시 분당구", "lat": 37.3948, "lon": 127.1111},
    {"name": "부산서면점", "region": "부산", "city": "부산 부산진구", "lat": 35.1578, "lon": 129.0600},
    {"name": "해운대점", "region": "부산", "city": "부산 해운대구", "lat": 35.1631, "lon": 129.1636},
    {"name": "대구동성로점", "region": "대구", "city": "대구 중구", "lat": 35.8714, "lon": 128.5911},
    {"name": "대전둔산점", "region": "대전", "city": "대전 서구", "lat": 36.3504, "lon": 127.3845},
    {"name": "광주상무점", "region": "광주", "city": "광주 서구", "lat": 35.1548, "lon": 126.8533},
    {"name": "제주공항점", "region": "제주", "city": "제주 제주시", "lat": 33.5104, "lon": 126.4913},
]

MENUS_DATA = [
    # (이름, 카테고리, 가격, 가중치) - 가중치가 높을수록 더 많이 팔림
    {"name": "아메리카노", "cat": "coffee", "price": 4500, "weight": 50, "desc": "깊고 진한 풍미의 에스프레소"},
    {"name": "카페라떼", "cat": "coffee", "price": 5000, "weight": 30, "desc": "부드러운 우유와 에스프레소의 조화"},
    {"name": "바닐라라떼", "cat": "coffee", "price": 5500, "weight": 20, "desc": "천연 바닐라 빈이 들어간 달콤한 라떼"},
    {"name": "카푸치노", "cat": "coffee", "price": 5000, "weight": 10, "desc": "풍성한 우유 거품을 즐기는 커피"},
    {"name": "콜드브루", "cat": "coffee", "price": 4800, "weight": 15, "desc": "차가운 물로 장시간 추출한 깔끔한 커피"},
    {"name": "돌체라떼", "cat": "coffee", "price": 5800, "weight": 10, "desc": "연유의 달콤함이 느껴지는 라떼"},
    {"name": "아인슈페너", "cat": "coffee", "price": 6000, "weight": 8, "desc": "진한 커피 위에 달콤한 크림"},
    {"name": "헤이즐넛 라떼", "cat": "coffee", "price": 5500, "weight": 10, "desc": "고소한 헤이즐넛 향이 가득"},
    {"name": "에스프레소", "cat": "coffee", "price": 4000, "weight": 5, "desc": "커피 본연의 강렬한 맛"},
    {"name": "카라멜 마키아또", "cat": "coffee", "price": 5900, "weight": 8, "desc": "달콤한 카라멜 소스와 부드러운 거품"},
    {"name": "치즈 케이크", "cat": "dessert", "price": 6500, "weight": 15, "desc": "진한 치즈 풍미가 가득한 케이크"},
    {"name": "티라미수", "cat": "dessert", "price": 7000, "weight": 12, "desc": "마스카포네 치즈와 에스프레소의 조화"},
    {"name": "초코 머핀", "cat": "dessert", "price": 3500, "weight": 8, "desc": "진한 초콜릿 칩이 박힌 머핀"},
    {"name": "크로플", "cat": "dessert", "price": 4500, "weight": 20, "desc": "버터 향 가득한 크루아상 와플"},
    {"name": "마카롱 세트", "cat": "dessert", "price": 12000, "weight": 5, "desc": "달콤하고 쫀득한 프랑스 디저트"},
]

POSITIVE_REVIEWS = [
    "맛있어요! 다음에도 또 주문할게요.", "배달이 빨라서 좋았습니다. 커피 향이 진해요.",
    "디저트가 너무 달지 않고 딱 좋네요.", "매번 시켜먹는데 실망시키지 않아요.",
    "사장님이 친절하시고 포장도 깔끔합니다.", "아메리카노 맛집이네요. 원두가 신선한 느낌이에요.",
    "양도 많고 맛도 좋습니다.", "여기 크로플이 진짜 맛있어요!", "인생 커피집 찾았습니다."
]

NEGATIVE_REVIEWS = [
    "커피가 조금 밍밍해요.", "배달이 생각보다 늦었네요.", "디저트가 좀 눅눅해서 아쉬웠어요.",
    "가격 대비 양이 적은 것 같아요.", "얼음이 너무 많아서 음료 양이 적어요.",
    "지난번보다는 맛이 덜한 것 같네요."
]

async def seed_data():
    session = SessionLocal()
    try:
        print("🗑️ 기존 데이터 삭제 중... (완전 초기화)")
        session.query(Review).delete()
        session.query(Order).delete()
        session.query(SalesDaily).delete()
        session.query(StoreReport).delete()
        session.commit()

        print("🌱 매장 및 메뉴 데이터 확인/생성...")
        # 매장 생성
        for data in STORES_DATA:
            if not session.query(Store).filter_by(store_name=data["name"]).first():
                session.add(Store(
                    store_name=data["name"], region=data["region"], city=data["city"],
                    lat=data["lat"], lon=data["lon"],
                    open_date=fake.date_between(start_date='-5y', end_date='-1y'),
                    franchise_type=random.choice(["직영", "가맹"]),
                    population_density_index=round(random.uniform(0.8, 2.5), 2)
                ))
        
        # 메뉴 생성
        for data in MENUS_DATA:
            if not session.query(Menu).filter_by(menu_name=data["name"]).first():
                session.add(Menu(
                    menu_name=data["name"], category=data["cat"],
                    list_price=data['price'], cost_price=round(data["price"] * 0.3, -1),
                    description=data["desc"], is_seasonal=False
                ))
        session.commit()

        # DB에서 다시 조회 (ID 포함)
        stores = session.query(Store).all()
        menus = session.query(Menu).all()
        menu_weights = [next(m["weight"] for m in MENUS_DATA if m["name"] == menu.menu_name) for menu in menus]

        print("🛒 현실적인 주문 데이터 생성 중 (최근 30일)...")
        total_orders_count = 0
        
        # 최근 30일치 데이터 생성
        days_range = 30
        end_date = date.today()
        start_date = end_date - timedelta(days=days_range)

        for day_offset in range(days_range + 1):
            current_date = start_date + timedelta(days=day_offset)
            weekday = current_date.weekday() # 0=월, 6=일
            is_weekend = weekday >= 5

            for store in stores:
                # 1. 일일 주문 수량 결정 (사용자 요청: 20개 내외로 가볍게)
                base_orders = random.randint(15, 25) if not is_weekend else random.randint(20, 30)
                
                # 매장별 편차 (강남, 홍대는 조금 더)
                if "강남" in store.store_name or "홍대" in store.store_name:
                    base_orders = int(base_orders * 1.2)
                
                daily_orders_num = int(base_orders * random.uniform(0.9, 1.1))

                for _ in range(daily_orders_num):
                    # 2. 메뉴 선택 (가중치 기반 랜덤)
                    menu = random.choices(menus, weights=menu_weights, k=1)[0]
                    
                    # 3. 주문 시간 결정 (점심/저녁 피크 타임 반영)
                    hour_prob = random.random()
                    if hour_prob < 0.4: # 40%는 점심시간 (11~14시)
                        hour = random.randint(11, 13)
                    elif hour_prob < 0.7: # 30%는 오후/저녁 (14~20시)
                        hour = random.randint(14, 19)
                    else: # 나머지 30%는 그 외 시간
                        hour = random.choice([9, 10, 20, 21])
                    
                    minute = random.randint(0, 59)
                    order_time = datetime.combine(current_date, datetime.min.time()) + timedelta(hours=hour, minutes=minute)

                    # 4. 수량 (대부분 1개, 가끔 2~3개)
                    quantity = random.choices([1, 2, 3, 4], weights=[80, 15, 4, 1], k=1)[0]
                    
                    # 주문 저장
                    new_order = Order(
                        store_id=store.store_id,
                        menu_id=menu.menu_id,
                        quantity=quantity,
                        total_price=float(menu.list_price) * quantity,
                        ordered_at=order_time
                    )
                    session.add(new_order)
                    total_orders_count += 1
            
            # 하루치 커밋 (메모리 절약)
            if day_offset % 5 == 0:
                print(f"   -> {current_date} 데이터 생성 완료...")
        
        session.commit()
        print(f"✅ 총 {total_orders_count}건의 주문 데이터 생성 완료!")

        # 리뷰 데이터 생성
        print("📝 주문 기반 리뷰 데이터 생성 (약 15% 확률)...")
        
        # 방금 생성한 주문들을 대상으로 리뷰 생성 (너무 많으면 느리니 최근 주문 위주로 쿼리해도 됨)
        # 여기서는 전체 주문 대상으로 하되, 쿼리 최적화 생략 (Batch 처리 권장되지만 간단히 구현)
        # 효율을 위해 방금 생성된 주문 ID 범위를 알면 좋지만, 간단히 다시 조회
        all_order_ids = [row.order_id for row in session.query(Order.order_id).all()]
        
        # 15% 샘플링
        review_order_ids = random.sample(all_order_ids, int(len(all_order_ids) * 0.15))
        
        count_reviews = 0
        for order_id in review_order_ids:
            # 주문 정보 조회 불필요, ID만 있으면 됨 (store_id, menu_id는 Join으로 알 수 있으나 Review 테이블 구조상 필요하다면 채워야 함)
            order = session.query(Order).get(order_id) # 성능상 아쉬우나 정확성을 위해
            
            if order:
                # 긍정 리뷰 확률 85%
                is_positive = random.random() < 0.85
                rating = random.randint(4, 5) if is_positive else random.randint(1, 3)
                text = random.choice(POSITIVE_REVIEWS) if is_positive else random.choice(NEGATIVE_REVIEWS)

                review_time = order.ordered_at + timedelta(hours=random.randint(1, 48))

                session.add(Review(
                    store_id=order.store_id,
                    order_id=order.order_id,
                    menu_id=order.menu_id,
                    rating=rating,
                    review_text=text,
                    delivery_app=random.choice(["배달의민족", "쿠팡이츠", "요기요", None]),
                    created_at=review_time
                ))
                count_reviews += 1
        
        session.commit()
        print(f"✅ 총 {count_reviews}건의 리뷰 데이터 생성 완료!")
        print("🎉 모든 데이터 준비가 완료되었습니다.")

    except Exception as e:
        print(f"❌ 오류 발생: {e}")
        session.rollback()
    finally:
        session.close()

if __name__ == "__main__":
    asyncio.run(seed_data())
