import asyncio
import random
from datetime import date, timedelta
from faker import Faker
from sqlalchemy import select
from app.core.db import SessionLocal, init_pool, close_pool
from app.store.store_schema import Store
from app.menu.menu_schema import Menu

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
        print("✅ 더미 데이터 생성 완료!")

    except Exception as e:
        print(f"❌ 오류 발생: {e}")
        session.rollback()
    finally:
        session.close()

if __name__ == "__main__":
    asyncio.run(seed_data())
