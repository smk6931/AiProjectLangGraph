import asyncio
import random
from datetime import datetime, date, timedelta
from faker import Faker
from sqlalchemy import select
from app.core.db import SessionLocal, init_pool, close_pool
from app.store.store_schema import Store
from app.menu.menu_schema import Menu
from app.review.review_schema import Review
from app.order.order_schema import Order

fake = Faker('ko_KR')

# 1. 매장 더미 데이터
STORES_DATA = [
    {"name": "강남본점", "region": "서울", "city": "서울 강남구",
        "lat": 37.4979, "lon": 127.0276},
    {"name": "홍대입구점", "region": "서울", "city": "서울 마포구",
        "lat": 37.5575, "lon": 126.9245},
    {"name": "여의도점", "region": "서울", "city": "서울 영등포구",
        "lat": 37.5219, "lon": 126.9242},
    {"name": "판교점", "region": "경기", "city": "성남시 분당구",
        "lat": 37.3948, "lon": 127.1111},
    {"name": "부산서면점", "region": "부산", "city": "부산 부산진구",
        "lat": 35.1578, "lon": 129.0600},
    {"name": "해운대점", "region": "부산", "city": "부산 해운대구",
        "lat": 35.1631, "lon": 129.1636},
    {"name": "대구동성로점", "region": "대구", "city": "대구 중구",
        "lat": 35.8714, "lon": 128.5911},
    {"name": "대전둔산점", "region": "대전", "city": "대전 서구",
        "lat": 36.3504, "lon": 127.3845},
    {"name": "광주상무점", "region": "광주", "city": "광주 서구",
        "lat": 35.1548, "lon": 126.8533},
    {"name": "제주공항점", "region": "제주", "city": "제주 제주시",
        "lat": 33.5104, "lon": 126.4913},
]

# 2. 메뉴 더미 데이터 (커피 10개, 디저트 5개)
MENUS_DATA = [
    # Coffee
    {"name": "아메리카노", "cat": "coffee", "price": 4500, "desc": "깊고 진한 풍미의 에스프레소"},
    {"name": "카페라떼", "cat": "coffee", "price": 5000, "desc": "부드러운 우유와 에스프레소의 조화"},
    {"name": "바닐라라떼", "cat": "coffee", "price": 5500, "desc": "천연 바닐라 빈이 들어간 달콤한 라떼"},
    {"name": "카푸치노", "cat": "coffee", "price": 5000, "desc": "풍성한 우유 거품을 즐기는 커피"},
    {"name": "콜드브루", "cat": "coffee", "price": 4800,
        "desc": "차가운 물로 장시간 추출한 깔끔한 커피"},
    {"name": "돌체라떼", "cat": "coffee", "price": 5800, "desc": "연유의 달콤함이 느껴지는 라떼"},
    {"name": "아인슈페너", "cat": "coffee", "price": 6000, "desc": "진한 커피 위에 달콤한 크림"},
    {"name": "헤이즐넛 라떼", "cat": "coffee", "price": 5500, "desc": "고소한 헤이즐넛 향이 가득"},
    {"name": "에스프레소", "cat": "coffee", "price": 4000, "desc": "커피 본연의 강렬한 맛"},
    {"name": "카라멜 마키아또", "cat": "coffee",
        "price": 5900, "desc": "달콤한 카라멜 소스와 부드러운 거품"},
    # Dessert
    {"name": "치즈 케이크", "cat": "dessert", "price": 6500, "desc": "진한 치즈 풍미가 가득한 케이크"},
    {"name": "티라미수", "cat": "dessert", "price": 7000, "desc": "마스카포네 치즈와 에스프레소의 조화"},
    {"name": "초코 머핀", "cat": "dessert", "price": 3500, "desc": "진한 초콜릿 칩이 박힌 머핀"},
    {"name": "크로플", "cat": "dessert", "price": 4500, "desc": "버터 향 가득한 크루아상 와플"},
    {"name": "마카롱 세트", "cat": "dessert", "price": 12000, "desc": "달콤하고 쫀득한 프랑스 디저트"},
]

# 3. 리뷰용 문구 템플릿
REVIEW_TEMPLATES = [
    "맛있어요! 다음에도 또 주문할게요.",
    "배달이 빨라서 좋았습니다. 커피 향이 진해요.",
    "디저트가 너무 달지 않고 딱 좋네요.",
    "매번 시켜먹는데 실망시키지 않아요.",
    "사장님이 친절하시고 포장도 깔끔합니다.",
    "아메리카노 맛집이네요. 원두가 신선한 느낌이에요.",
    "아이들이 너무 좋아해요. 간식용으로 최고입니다.",
    "조금 늦게 왔지만 맛있어서 참습니다 ㅎㅎ",
    "가성비가 아주 좋습니다.",
    "매장 분위기도 좋을 것 같아요. 배달 추천합니다.",
    "포장이 아주 정성스럽네요.",
    "부모님도 좋아하셔요.",
    "양이 생각보다 많아서 놀랐어요.",
    "커피 산미가 딱 적당해서 제 스타일이에요.",
    "여기 크로플 진짜 예술입니다..."
]


async def seed_data():
    # 동기식 세션 사용 (간단한 스크립트 실행을 위해)
    session = SessionLocal()
    try:
        print("🌱 데이터 생성 시작...")

        # 1. 매장 생성
        for data in STORES_DATA:
            # 중복 체크
            exists = session.query(Store).filter_by(
                store_name=data["name"]).first()
            if not exists:
                store = Store(
                    store_name=data["name"],
                    region=data["region"],
                    city=data["city"],
                    lat=data["lat"],
                    lon=data["lon"],
                    open_date=fake.date_between(
                        start_date='-5y', end_date='-1y'),
                    franchise_type=random.choice(["직영", "가맹"]),
                    population_density_index=round(random.uniform(0.8, 2.5), 2)
                )
                session.add(store)

        # 2. 메뉴 생성
        for data in MENUS_DATA:
            exists = session.query(Menu).filter_by(
                menu_name=data["name"]).first()
            if not exists:
                cost = round(data["price"] * 0.3, -1)  # 원가는 정가의 약 30%
                menu = Menu(
                    menu_name=data["name"],
                    category=data["cat"],
                    list_price=data["price"],
                    cost_price=cost,
                    description=data["desc"],
                    is_seasonal=random.choice(
                        [True, False]) if "딸기" in data["name"] else False
                )
                session.add(menu)

        session.commit()

        # 3. 리뷰 생성 (지점별로 5~10개)
        print("📝 리뷰 생성 중...")
        stores = session.query(Store).all()
        menus = session.query(Menu).all()

        if not stores or not menus:
            print("⚠️ 매장이나 메뉴 데이터가 없어 리뷰를 생성할 수 없습니다.")
            return

        for store in stores:
            # 해당 지점에 이미 리뷰가 있는지 확인 (중복 생성 방지)
            existing_count = session.query(Review).filter_by(
                store_id=store.store_id).count()
            if existing_count > 0:
                continue

            num_reviews = random.randint(5, 10)
            for _ in range(num_reviews):
                menu = random.choice(menus)
                review = Review(
                    store_id=store.store_id,
                    menu_id=menu.menu_id,
                    rating=random.randint(3, 5),  # 평점 3~5 사이
                    review_text=random.choice(REVIEW_TEMPLATES),
                    delivery_app=random.choice(["배달의민족", "쿠팡이츠", "요기요"]),
                    created_at=fake.date_time_between(
                        start_date='-1m', end_date='now')
                )
                session.add(review)

        session.commit()

        # 4. 주문 데이터 생성 (지점별 일주일치)
        print("🛒 주문 데이터 생성 중...")
        for store in stores:
            # 해당 지점에 이미 주문 데이터가 있는지 확인 (중복 생성 방지용이나 일주일치라 그냥 추가하거나 기간 체크 가능)
            # 여기서는 간단히 오늘 기준 7일전 데이터가 있는지 확인
            seven_days_ago = datetime.now() - timedelta(days=7)
            exists = session.query(Order).filter(
                Order.store_id == store.store_id,
                Order.ordered_at >= seven_days_ago
            ).first()

            if exists:
                continue

            for day_offset in range(7):
                current_date = date.today() - timedelta(days=day_offset)
                # 하루에 10~30건의 주문 발생
                num_orders = random.randint(10, 30)

                for _ in range(num_orders):
                    menu = random.choice(menus)
                    quantity = random.randint(1, 3)
                    total_price = float(menu.list_price) * quantity

                    # 주문 시간 랜덤 (09:00 ~ 22:00)
                    order_time = datetime.combine(
                        current_date,
                        datetime.min.time()
                    ) + timedelta(hours=random.randint(9, 21), minutes=random.randint(0, 59))

                    order = Order(
                        store_id=store.store_id,
                        menu_id=menu.menu_id,
                        quantity=quantity,
                        total_price=total_price,
                        ordered_at=order_time
                    )
                    session.add(order)

        session.commit()
        print("✅ 모든 더미 데이터 생성 완료!")

    except Exception as e:
        print(f"❌ 오류 발생: {e}")
        session.rollback()
    finally:
        session.close()


if __name__ == "__main__":
    asyncio.run(seed_data())
