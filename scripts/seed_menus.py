import sys
import os
import asyncio
from sqlalchemy import text
from dotenv import load_dotenv
from langchain_openai import OpenAIEmbeddings

# Add project root to sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.db import engine, base, SessionLocal
from app.menu.menu_schema import Menu

load_dotenv()
embeddings_model = OpenAIEmbeddings(model="text-embedding-3-small")

async def get_embedding(text: str):
    try:
        return await embeddings_model.aembed_query(text)
    except Exception as e:
        print(f"⚠️ 임베딩 실패: {e}")
        return None

def init_db():
    print("🔄 Initializing Menus Table...")
    try:
        with engine.connect() as conn:
            # 메뉴 테이블 초기화 (주문/리뷰 FK cascade로 인해 다 날아감 주의)
            conn.execute(text("DROP TABLE IF EXISTS menus CASCADE"))
            conn.commit()
            print("   - Old menus table dropped.")
    except Exception as e:
        print(f"   - Warning during drop: {e}")

    # Create new tables
    base.metadata.create_all(bind=engine)
    print("✅ Menus table ready.")

async def seed_data():
    session = SessionLocal()
    try:
        print("🌱 Seeding Data (Menus - 15 Items)...")

        # 1. Menus with Recipe Info (Total 15 Items)
        menu_items = [
             # --- COFFEE (6) ---
             {"name": "아이스 아메리카노", "cat": "coffee", "price": 4500, 
              "ing": "에스프레소 2샷 (60ml), 정수물 150ml, 얼음 200g", 
              "step": "1. 아이스컵에 얼음을 가득 채운다.\n2. 정수물 150ml를 붓는다.\n3. 에스프레소 2샷을 추출하여 위에 붓는다 (크레마 보존)."},
             
             {"name": "따뜻한 아메리카노", "cat": "coffee", "price": 4500,
              "ing": "에스프레소 2샷 (60ml), 온수 250ml",
              "step": "1. 머그잔에 뜨거운 물을 예열 후 버린다.\n2. 온수 250ml를 붓는다.\n3. 에스프레소 2샷을 추출하여 붓는다."},
             
             {"name": "카페 라떼", "cat": "coffee", "price": 5000,
              "ing": "에스프레소 2샷, 우유 200ml, 스팀밀크 폼 1cm",
              "step": "1. 피처에 우유 200ml를 담고 벨벳 밀크 폼을 만든다.\n2. 에스프레소 2샷을 잔에 받는다.\n3. 스팀 밀크를 붓고 얇은 폼(1cm)을 올린다."},
             
             {"name": "바닐라 라떼", "cat": "coffee", "price": 5500,
              "ing": "바닐라 시럽 3펌프(30g), 에스프레소 2샷, 우유 200ml",
              "step": "1. 잔에 바닐라 시럽 3펌프를 넣는다.\n2. 에스프레소 2샷을 추출하여 시럽과 섞는다.\n3. 스팀 우유(또는 차가운 우유+얼음)를 붓는다."},
             
             {"name": "카라멜 마키아또", "cat": "coffee", "price": 5800,
              "ing": "카라멜 시럽 2펌프, 바닐라 시럽 1펌프, 에스프레소 2샷, 우유 180ml, 카라멜 드리즐",
              "step": "1. 시럽을 넣고 스팀 우유를 붓는다.\n2. 에스프레소 샷을 중앙에 부어 점을 만든다.\n3. 거품 위에 카라멜 드리즐을 격자 무늬로 뿌린다."},

             {"name": "콜드브루 디카페인", "cat": "coffee", "price": 5500,
              "ing": "콜드브루 원액 60ml, 물 180ml, 얼음 200g",
              "step": "1. 잔에 얼음을 채운다.\n2. 물 180ml를 붓는다.\n3. 콜드브루 원액 60ml를 천천히 부어 그라데이션을 만든다."},

             # --- BEVERAGE & ADE (4) ---
             {"name": "초코 라떼 (Iced)", "cat": "beverage", "price": 5500,
              "ing": "초코 파우더 30g, 우유 200ml, 얼음 150g, 초코 드리즐",
              "step": "1. 소량의 뜨거운 물로 초코 파우더를 녹인다.\n2. 우유와 얼음을 넣고 섞는다.\n3. 컵 벽면에 초코 드리즐을 장식 후 음료를 담는다."},

             {"name": "딸기 라떼", "cat": "beverage", "price": 6000,
              "ing": "딸기청 60g, 우유 200ml, 얼음 150g, 건조 딸기 토핑",
              "step": "1. 잔 바닥에 딸기청 60g을 담는다.\n2. 얼음을 8부까지 채운다.\n3. 우유 200ml를 붓는다. (층 분리 유지)\n4. 건조 딸기 토핑을 올린다."},
             
             {"name": "자몽 에이드", "cat": "ade", "price": 5800,
              "ing": "자몽청 50g, 탄산수 150ml, 얼음 200g, 자몽 슬라이스, 로즈마리",
              "step": "1. 잔에 자몽청을 담는다.\n2. 얼음을 가득 채운다.\n3. 탄산수를 붓고 자몽 슬라이스와 로즈마리를 꽂아 장식한다."},

             {"name": "레몬 에이드", "cat": "ade", "price": 5500,
              "ing": "레몬청 50g, 탄산수 150ml, 얼음 200g, 레몬 슬라이스, 애플민트",
              "step": "1. 잔에 레몬청을 담는다.\n2. 얼음을 가득 채운다.\n3. 탄산수를 천천히 부어 청량감을 유지한다.\n4. 레몬 슬라이스와 애플민트를 올린다."},
             
             # --- DESSERT (5) ---
             {"name": "민트 초코 프라페", "cat": "dessert", "price": 6500,
              "ing": "우유 120ml, 민트 파우더 35g, 초코 소스 15g, 얼음 200g, 휘핑 크림",
              "step": "1. 블렌더에 우유, 민트 파우더, 얼음을 넣고 25초간 블렌딩.\n2. 잔 벽면에 초코 소스를 두른다.\n3. 음료를 따르고 휘핑 크림을 올린다.\n4. 초코 칩/시럽으로 토핑."},

             {"name": "뉴욕 치즈 케이크", "cat": "dessert", "price": 6500,
              "ing": "크림치즈, 설탕, 계란, 통밀 쿠키 시트",
              "step": "냉동 상태에서 꺼내 2시간 냉장 해동 후 제공. 슈가파우더를 살짝 뿌려 플레이팅."},
             
             {"name": "티라미수", "cat": "dessert", "price": 6800,
              "ing": "마스카포네 치즈, 에스프레소 시럽, 레이디핑거, 코코아 파우더",
              "step": "쇼케이스에서 꺼내 코코아 파우더를 듬뿍 뿌린 후 제공. (가루 날림 주의)"},

             {"name": "플레인 크로플", "cat": "dessert", "price": 4500,
              "ing": "크로와상 생지 1개, 메이플 시럽, 슈가파우더",
              "step": "1. 예열된 와플 기계에 해동된 생지를 넣고 3분간 굽는다.\n2. 접시에 담고 메이플 시럽과 슈가파우더를 뿌린다."},

             {"name": "햄치즈 샌드위치", "cat": "dessert", "price": 5500,
              "ing": "식빵 2장, 슬라이스 햄 2장, 체다치즈 1장, 양상추, 머스타드 소스",
              "step": "1. 주문 즉시 오븐 또는 팬에 30초간 워밍한다.\n2. 반으로 커팅하여 유산지에 싸서 제공한다."}
        ]

        menus_data = []
        print("🧠 Generating Menu Embeddings...")
        for item in menu_items:
            # 임베딩 텍스트: 이름 + 카테고리 + 재료 + 레시피
            text_to_embed = f"메뉴명: {item['name']}, 카테고리: {item['cat']}, 재료: {item['ing']}, 레시피: {item['step']}"
            emb = await get_embedding(text_to_embed)
            
            m = Menu(
                menu_name=item["name"],
                category=item["cat"],
                list_price=item["price"],
                ingredients=item["ing"],
                recipe_steps=item["step"],
                is_seasonal=False,
                embedding=emb # 벡터값 추가
            )
            menus_data.append(m)
            
        session.add_all(menus_data)
        session.commit()
        
        print(f"✅ Inserted {len(menus_data)} Menus")
        print("🎉 Menu Seeding Completed Successfully!")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        session.rollback()
    finally:
        session.close()

if __name__ == "__main__":
    init_db()
    asyncio.run(seed_data())
