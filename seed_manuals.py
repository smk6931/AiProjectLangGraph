import asyncio
import os
import sys
from dotenv import load_dotenv

load_dotenv()

from app.core.db import SessionLocal, database_url
from app.manual.manual_schema import Manual
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import text
from langchain_openai import OpenAIEmbeddings

# 비동기 엔진 생성
engine = create_async_engine(database_url.replace("postgresql://", "postgresql+asyncpg://"))
AsyncSessionLocal = sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)

# OpenAI 임베딩 모델
embeddings_model = OpenAIEmbeddings(model="text-embedding-3-small")

# === 순수 매뉴얼 데이터 (How-To) ===
# 정책(Policy) 데이터는 seed_policies.py로 이동됨
MANUAL_DATA = [
    # 1. 커피 품질 & 추출
    {
        "category": "커피 품질",
        "title": "라떼 거품 품질 개선 (거품 꺼짐)",
        "content": "현상: 라떼 거품이 금방 꺼지거나 거침.\n해결: 스팀 노즐 팁을 우유 표면에 1cm만 담그고 공기를 주입(치치치 소리)한 뒤, 노브를 더 열어 강한 롤링을 만듭니다. 65도에서 멈추고 바닥에 피처를 탕탕 쳐 기포를 깹니다."
    },
    {
        "category": "커피 품질",
        "title": "에스프레소 과소 추출 (물처럼 나옴)",
        "content": "현상: 20초 이내로 빠르게 추출되고 묽음.\n해결: 분쇄도를 더 곱게(Fine) 조절하거나 원두 양을 1g 늘립니다. 탬핑 압력을 더 강하게 줍니다."
    },
    {
        "category": "커피 품질",
        "title": "에스프레소 과다 추출 (안 나옴)",
        "content": "현상: 40초 이상 걸리거나 방울방울 떨어짐.\n해결: 분쇄도를 더 굵게(Coarse) 조절하거나 원두 양을 0.5g 줄입니다. 샤워스크린이 막혔는지 확인하고 백플러싱을 합니다."
    },
    {
        "category": "커피 품질",
        "title": "크레마 상태 확인 기준",
        "content": "정상: 3~4mm 두께의 황금빛 갈색.\n불량: 1mm 미만이면 원두가 오래되었거나 추출압력이 낮음. 짙은 검은색이면 탄 원두거나 온도가 너무 높음(96도 이상)."
    },

    # 2. 기기 관리 & 청소
    {
        "category": "기기 관리",
        "title": "에스프레소 머신 백플러싱(약품 청소)",
        "content": "주기: 매일 마감 시.\n방법: 1. 포타필터에 블라인드 바스켓 장착. 2. 전용 세제 1스푼 넣음. 3. 추출 버튼 5초 켜고 5초 끔을 5회 반복. 4. 물로만 10회 반복 헹굼."
    },
    {
        "category": "기기 관리",
        "title": "그라인더 날(Burr) 교체 주기",
        "content": "기준: 원두 500kg 사용 시 또는 6개월 경과 시.\n증상: 분쇄 입자가 들쑥날쑥하거나 쓴맛이 강해짐.\n조치: 본사 AS팀에 교체 접수(점주 직접 교체 금지)."
    },
    {
        "category": "기기 관리",
        "title": "제빙기 필터 청소 및 소독",
        "content": "주기: 월 2회.\n방법: 1. 제빙기 전원 OFF 및 얼음 제거. 2. 내부를 희석된 소독제로 닦음. 3. 응축기 먼지 필터를 분리하여 물로 세척 후 건조."
    },
    {
        "category": "기기 관리",
        "title": "POS 프린터 용지 교체",
        "content": "방법: 1. 측면 버튼을 눌러 뚜껑 오픈. 2. 새 용지의 끝부분이 위로 오도록 삽입. 3. 뚜껑을 닫고 용지를 조금 찢어냄. 4. 테스트 출력 확인."
    },

    # 3. 레시피 (음료 제조법)
    {
        "category": "레시피",
        "title": "딸기 라떼 제조 레시피",
        "content": "재료: 딸기청 60g, 우유 200ml, 얼음 150g.\n방법: 1. 컵 바닥에 딸기청을 붓는다. 2. 얼음을 가득 채운다. 3. 우유를 천천히 부어 층이 생기게 한다(Layering). 4. 상단에 생딸기 슬라이스 1개 토핑."
    },
    {
        "category": "레시피",
        "title": "콜드브루 비율 및 희석",
        "content": "비율: 콜드브루 원액 1 : 물 3 : 얼음 2.\n주의: 원액은 개봉 후 냉장 보관하며 7일 이내 전량 사용해야 함. 산미가 강해지면 폐기."
    },
    {
        "category": "레시피",
        "title": "휘핑크림 제조 (카트리지)",
        "content": "비율: 휘핑용 크림 500ml + 바닐라 시럽 2펌프.\n방법: 1. 휘핑기에 재료를 넣고 뚜껑을 꽉 닫음. 2. 가스 카트리지 1개를 끼우고 소리 날 때까지 돌림. 3. 15회 이상 강하게 흔듦. 4. 냉장 보관."
    },
    {
        "category": "레시피",
        "title": "민트 초코 프라페 레시피",
        "content": "재료: 우유 100ml, 민트 파우더 30g, 초코 소스 20g, 얼음 200g.\n방법: 1. 블렌더에 모든 재료 투입. 2. 전용 블렌딩 모드(1번 버튼) 작동. 3. 컵에 담고 휘핑크림과 초코칩 토핑."
    }
]

async def seed_manuals():
    print("🚀 [Manual] 데이터 시딩 및 임베딩 시작...")
    
    async with AsyncSessionLocal() as session:
        # 1. 테이블 생성 (alembic 대용)
        await session.execute(text("""
            CREATE TABLE IF NOT EXISTS manuals (
                manual_id SERIAL PRIMARY KEY,
                category VARCHAR(50) NOT NULL,
                title VARCHAR(200) NOT NULL,
                content TEXT NOT NULL,
                embedding Vector(1536),
                created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
            );
        """))
        # 인덱스
        await session.execute(text("CREATE INDEX IF NOT EXISTS manual_embedding_idx ON manuals USING ivfflat (embedding vector_cosine_ops);"))
        await session.commit()
    
        # 2. 기존 데이터 삭제 (TRUNCATE)
        await session.execute(text("TRUNCATE TABLE manuals RESTART IDENTITY;"))
        
        # 3. 데이터 삽입
        count = 0
        for item in MANUAL_DATA:
            # 임베딩 생성
            text_to_embed = f"{item['title']}\n{item['content']}"
            vector = await embeddings_model.aembed_query(text_to_embed)
            
            manual = Manual(
                category=item["category"],
                title=item["title"],
                content=item["content"],
                embedding=vector
            )
            session.add(manual)
            count += 1
            print(f"✅ [Manual] 추가: {item['title']}")
            
        await session.commit()
        print(f"🎉 총 {count}개의 매뉴얼 데이터 저장 완료.")

if __name__ == "__main__":
    asyncio.run(seed_manuals())
