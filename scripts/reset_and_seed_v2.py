import asyncio
import os
import sys
import random
from datetime import datetime, timedelta
from decimal import Decimal

# 프로젝트 루트 경로 추가
sys.path.append(os.getcwd())

from app.core.db import execute, fetch_all, init_pool, close_pool

# --- 설정 ---
SURVIVOR_LOCATIONS = ["서울 강남구", "부산 부산진구", "강원도 속초시"] # 남길 지점 위치 키워드
TARGET_DAYS = 30 # 생성할 데이터 기간 (일)
MENU_PRICES = {} # 메뉴 가격 캐싱

async def get_menu_prices():
    """메뉴 가격 정보 로드"""
    rows = await fetch_all("SELECT menu_id, list_price FROM menus")
    return {row['menu_id']: row['list_price'] for row in rows}

async def restructure_stores():
    print("🏗️ [1/4] 지점 구조조정 시작...")
    
    # 1. 생존할 지점 확인 또는 생성
    survivor_ids = []
    
    # 강남(서울), 서면(부산), 속초(강원) 매핑
    # 강남(서울), 서면(부산), 속초(강원) 매핑
    target_map = {
        "서울": {"name": "강남본점", "region": "서울", "city": "서울 강남구", "lat": 37.4979, "lon": 127.0276},
        "부산": {"name": "부산서면점", "region": "부산", "city": "부산진구", "lat": 35.1578, "lon": 129.0600},
        "강원": {"name": "강원속초점", "region": "강원", "city": "속초시", "lat": 38.2070, "lon": 128.5918}
    }
    
    # 기존 지점 싹 다 조회
    existing_stores = await fetch_all("SELECT store_id, store_name FROM stores")
    
    # 전략: 그냥 싹 지우고 새로 만드는게 ID 관리상 깔끔함 (FK CASCADE 가정)
    # 하지만 FK가 걸려있으니, 먼저 다 지우고 새로 3개를 만듭니다.
    print("   - 기존 데이터(주문, 리뷰, 매출) 및 지점 삭제 중...")
    await execute("TRUNCATE TABLE stores RESTART IDENTITY CASCADE;") 
    
    print("   - 정예 지점 3곳 신규 등록 중...")
    new_ids = []
    for key, info in target_map.items():
        # 지점 생성
        insert_query = """
            INSERT INTO stores (store_name, region, city, lat, lon, open_date, franchise_type)
            VALUES (%s, %s, %s, %s, %s, '2020-01-01', '가맹') RETURNING store_id
        """
        res = await fetch_all(insert_query, (info['name'], info['region'], info['city'], info['lat'], info['lon']))
        new_id = res[0]['store_id']
        new_ids.append(new_id)
        print(f"     ✅ {info['name']} (ID: {new_id}) 생성 완료")
        
    return new_ids

async def generate_daily_data(store_ids, menu_ids):
    print(f"📅 [2/4] 최근 {TARGET_DAYS}일치 데이터 생성 시작...")
    
    end_date = datetime.now().date()
    start_date = end_date - timedelta(days=TARGET_DAYS)
    
    # 날씨 더미 데이터
    weathers = ["맑음", "구름조금", "흐림", "비", "눈", "맑음", "맑음"]
    
    total_orders_count = 0
    
    for day_offset in range(TARGET_DAYS + 1):
        curr_date = start_date + timedelta(days=day_offset)
        is_weekend = curr_date.weekday() >= 5 # 5:토, 6:일
        
        # 날씨 랜덤 (계절감 무시하고 랜덤)
        weather = random.choice(weathers)
        
        for store_id in store_ids:
            # 1. 주문 생성 (일일 주문 수: 평일 10~20건, 주말 20~40건)
            daily_order_cnt = random.randint(20, 40) if is_weekend else random.randint(10, 20)
            
            daily_total_rev = 0
            
            for _ in range(daily_order_cnt):
                # 주문 시각 (11:00 ~ 22:00)
                hour = random.randint(11, 21)
                minute = random.randint(0, 59)
                order_time = datetime.combine(curr_date, datetime.min.time()).replace(hour=hour, minute=minute)
                
                # 메뉴 선택 (1~3개)
                items_cnt = random.randint(1, 3)
                selected_menus = random.choices(menu_ids, k=items_cnt)
                
                order_total = 0
                for mid in selected_menus:
                    price = MENU_PRICES.get(mid, 10000)
                    order_total += price
                    
                    # orders 테이블 insert (주문 1건당 메뉴 1개 row로 들어가는 구조라면 반복, 
                    # 현재 스키마는 'orders'가 개별 아이템 단위인지 주문 1건 단위인지 확인 필요.
                    # 보통 주문-주문상세가 나뉘지만, 여기선 orders가 단일 테이블로 개별 아이템을 담는다고 가정하거나
                    # 스키마 상 orders 하나에 menu_id가 있다면 '주문내역'테이블임.
                    # 확인 결과: orders 테이블에 menu_id가 있음 -> 개별 아이템 단위 저장)
                    
                    await execute("""
                        INSERT INTO orders (store_id, menu_id, quantity, total_price, ordered_at)
                        VALUES (%s, %s, 1, %s, %s)
                    """, (store_id, mid, price, order_time))
                
                daily_total_rev += order_total
            
            total_orders_count += daily_order_cnt
            
            # 2. 일매출(sales_daily) 집계 저장
            # sales_daily 테이블이 존재한다면 insert
            await execute("""
                INSERT INTO sales_daily (store_id, sale_date, total_sales, total_orders, weather_info)
                VALUES (%s, %s, %s, %s, %s)
            """, (store_id, curr_date, daily_total_rev, daily_order_cnt, weather))

            # 3. 리뷰 생성 (주문의 30% 확률)
            if random.random() < 0.3:
                # 랜덤 메뉴평
                mid = random.choice(menu_ids)
                rating = random.choices([5, 4, 3, 2, 1], weights=[50, 30, 10, 5, 5])[0]
                texts = {
                    5: ["최고예요", "맛있어요", "또 시킬게요", "강추!", "배달 빠름"],
                    4: ["괜찮아요", "맛은 있는데 좀 식음", "무난함"],
                    3: ["그저 그래요", "보통", "양이 적음"],
                    1: ["별로예요", "다신 안시킴", "최악"]
                }
                txt = random.choice(texts.get(rating, ["보통"]))
                
                await execute("""
                    INSERT INTO reviews (store_id, menu_id, rating, review_text, created_at)
                    VALUES (%s, %s, %s, %s, %s)
                """, (store_id, mid, rating, txt, datetime.combine(curr_date, datetime.min.time())))
                
    print(f"✅ 데이터 생성 완료! (총 주문 항목: {total_orders_count}건)")

async def main():
    await init_pool()
    
    # 0. 메뉴 ID 가져오기 (가정: 메뉴 데이터는 보존되어 있다고 가정. 만약 TRUNCATE CASCADE로 지워졌으면 다시 넣어야 함)
    # TRUNCATE stores CASCADE를 하면 menus가 store에 종속되어 있으면 지워짐.
    # 스키마상 menus는 store_id가 없을 수도 있음 (본사 공통 메뉴).
    # 확인: menus 테이블은 store_id를 가지고 있나? 보통 프랜차이즈 메뉴는 공통.
    # 만약 menus가 살아있다면 다행. 아니면 다시 넣어야 함.
    # 안전하게 메뉴도 다시 넣자.
    
    print("🧹 [0/4] 전체 데이터 초기화 (TRUNCATE)...")
    try:
        # FK 제약조건 때문에 순서 중요. stores를 날리면 orders, reviews, sales_daily 등 다 날아감 (ON DELETE CASCADE 설정 시)
        # 만약 설정 안되어있으면 개별 삭제 필요. 안전하게 개별 삭제.
        await execute("TRUNCATE TABLE reviews CASCADE")
        await execute("TRUNCATE TABLE orders CASCADE") 
        await execute("TRUNCATE TABLE sales_daily CASCADE")
        await execute("TRUNCATE TABLE store_reports CASCADE")
        await execute("TRUNCATE TABLE store_inquiries CASCADE")
        # await execute("TRUNCATE TABLE menus CASCADE") # 메뉴는 살려볼까? -> store_id가 종속적이면 날아감.
        # 일단 stores를 날리기 전에 메뉴 백업? 귀찮으니 메뉴도 다시 넣음.
        await execute("TRUNCATE TABLE menus CASCADE")
        await execute("TRUNCATE TABLE stores CASCADE")
    except Exception as e:
        print(f"⚠️ 초기화 중 경고 (테이블 없을 수 있음): {e}")

    # 1. 지점 생성
    survivor_ids = await restructure_stores()
    
    # 2. 메뉴 생성 (공통 메뉴 15종)
    print("🍔 [3/4] 메뉴 데이터 복구 (15종)...")
    menu_items = [
        # Coffee (10)
        ("아메리카노", 4500, "COFFEE"),
        ("카페라떼", 5000, "COFFEE"),
        ("바닐라라떼", 5500, "COFFEE"),
        ("콜드브루", 4800, "COFFEE"),
        ("카푸치노", 5000, "COFFEE"),
        ("카페모카", 5500, "COFFEE"),
        ("카라멜마키아또", 5800, "COFFEE"),
        ("에스프레소", 4000, "COFFEE"),
        ("아인슈페너", 6000, "COFFEE"),
        ("돌체라떼", 5800, "COFFEE"),
        # Dessert (5)
        ("치즈케이크", 6500, "DESSERT"),
        ("티라미수", 7000, "DESSERT"),
        ("초코쿠키", 3500, "DESSERT"),
        ("크로플", 4000, "DESSERT"),
        ("마카롱", 3000, "DESSERT")
    ]
    menu_ids = []
    for name, price, cat in menu_items:
        # description, image_url 등은 생략 또는 더미
        res = await fetch_all("""
            INSERT INTO menus (menu_name, list_price, category, description, is_seasonal)
            VALUES (%s, %s, %s, '맛있는 메뉴', false) RETURNING menu_id
        """, (name, price, cat))
        mid = res[0]['menu_id']
        menu_ids.append(mid)
        MENU_PRICES[mid] = price
        
    # 3. 데이터 생성
    await generate_daily_data(survivor_ids, menu_ids)
    
    await close_pool()
    print("🎉 모든 작업 완료! 이제 '강남본점', '부산서면점', '강원속초점'만 남았습니다.")

if __name__ == "__main__":
    if os.name == 'nt':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(main())
