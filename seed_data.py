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

fake = Faker('ko_KR')

# --- 기존 데이터들 ---
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

MENUS_DATA = [
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
    {"name": "치즈 케이크", "cat": "dessert", "price": 6500, "desc": "진한 치즈 풍미가 가득한 케이크"},
    {"name": "티라미수", "cat": "dessert", "price": 7000, "desc": "마스카포네 치즈와 에스프레소의 조화"},
    {"name": "초코 머핀", "cat": "dessert", "price": 3500, "desc": "진한 초콜릿 칩이 박힌 머핀"},
    {"name": "크로플", "cat": "dessert", "price": 4500, "desc": "버터 향 가득한 크루아상 와플"},
    {"name": "마카롱 세트", "cat": "dessert", "price": 12000, "desc": "달콤하고 쫀득한 프랑스 디저트"},
]

REVIEW_TEMPLATES = [
    "맛있어요! 다음에도 또 주문할게요.", "배달이 빨라서 좋았습니다. 커피 향이 진해요.",
    "디저트가 너무 달지 않고 딱 좋네요.", "매번 시켜먹는데 실망시키지 않아요.",
    "사장님이 친절하시고 포장도 깔끔합니다.", "아메리카노 맛집이네요. 원두가 신선한 느낌이에요.",
    "아이들이 너무 좋아해요. 간식용으로 최고입니다.", "조금 늦게 왔지만 맛있어서 참습니다 ㅎㅎ",
    "가성비가 아주 좋습니다.", "매장 분위기도 좋을 것 같아요.",
    "포장이 아주 정성스럽네요.", "부모님도 좋아하셔요.",
    "양이 생각보다 많아서 놀랐어요.", "커피 산미가 딱 적당해서 제 스타일이에요.",
    "여기 크로플 진짜 예술입니다..."
]


async def seed_data():
    session = SessionLocal()
    try:
        print("🌱 데이터 생성 시작...")

        # 1. 매장/메뉴 생성 (기장 로직 동일)
        for data in STORES_DATA:
            if not session.query(Store).filter_by(store_name=data["name"]).first():
                session.add(Store(
                    store_name=data["name"], region=data["region"], city=data["city"],
                    lat=data["lat"], lon=data["lon"],
                    open_date=fake.date_between(
                        start_date='-5y', end_date='-1y'),
                    franchise_type=random.choice(["직영", "가맹"]),
                    population_density_index=round(random.uniform(0.8, 2.5), 2)
                ))

        for data in MENUS_DATA:
            if not session.query(Menu).filter_by(menu_name=data["name"]).first():
                session.add(Menu(
                    menu_name=data["name"], category=data["cat"],
                    list_price=data['price'], cost_price=round(
                        data["price"] * 0.3, -1),
                    description=data["desc"], is_seasonal=False
                ))
        session.commit()

        # 2. 주문 데이터 생성 (일주일치)
        print("🛒 주문 데이터 생성 중...")
        stores = session.query(Store).all()
        menus = session.query(Menu).all()

        # 기존 주문이 있으면 일단 건너뜀 (중복 생성 방지)
        if session.query(Order).count() == 0:
            for store in stores:
                for day_offset in range(7):
                    current_date = date.today() - timedelta(days=day_offset)
                    for _ in range(random.randint(10, 20)):
                        menu = random.choice(menus)
                        quantity = random.randint(1, 2)
                        order_time = datetime.combine(current_date, datetime.min.time()) + \
                            timedelta(hours=random.randint(9, 21),
                                      minutes=random.randint(0, 59))
                        session.add(Order(
                            store_id=store.store_id, menu_id=menu.menu_id,
                            quantity=quantity, total_price=float(
                                menu.list_price) * quantity,
                            ordered_at=order_time
                        ))
            session.commit()

        # 3. 리뷰 데이터 생성 (★주문 기반으로 관계 형성★)
        print("📝 주문 기반 리뷰 생성 중...")
        # 기존 리뷰 삭제 (관계 갱신을 위해)
        session.query(Review).delete()

        all_orders = session.query(Order).all()
        # 전체 주문 중 약 20%만 리뷰를 남김
        review_orders = random.sample(all_orders, int(len(all_orders) * 0.2))

        for order in review_orders:
            # 리뷰 시간은 주문 시간으로부터 1시간 ~ 12시간 사이
            review_time = order.ordered_at + \
                timedelta(hours=random.randint(1, 12))

            session.add(Review(
                store_id=order.store_id,
                order_id=order.order_id,  # 주문과 연결!
                menu_id=order.menu_id,
                rating=random.randint(3, 5),
                review_text=random.choice(REVIEW_TEMPLATES),
                delivery_app=random.choice(["배달의민족", "쿠팡이츠", "요기요", None]),
                created_at=review_time
            ))

        session.commit()
        print("✅ 모든 데이터 간의 관계 형성이 완료되었습니다!")

    except Exception as e:
        print(f"❌ 오류 발생: {e}")
        session.rollback()
    finally:
        session.close()

if __name__ == "__main__":
    asyncio.run(seed_data())
