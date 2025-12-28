import asyncio
import os
import sys
import random
import json
from datetime import datetime, timedelta
from typing import List, Dict

# 프로젝트 루트
sys.path.append(os.getcwd())

from app.core.db import execute, fetch_all, init_pool, close_pool
from app.clients.genai import genai_generate_text
from dotenv import load_dotenv
from langchain_openai import OpenAIEmbeddings

load_dotenv()

# OpenAI 임베딩 모델 (1536차원)
embeddings_model = OpenAIEmbeddings(model="text-embedding-3-small")

# 동시 실행 제한 (Rate Limit 방지)
SEM = asyncio.Semaphore(10)

async def get_embedding(text: str):
    """Generate embedding using OpenAI text-embedding-3-small"""
    if not text:
        return None
    try:
        return await embeddings_model.aembed_query(text)
    except Exception as e:
        # print(f"⚠️ 임베딩 실패: {e}")
        return None

async def generate_review_content_with_sem(store_name: str, menu_list: List[str], weather: str, ordered_at: datetime, rating: int) -> str:
    async with SEM:
        # 다양한 리뷰 스타일 랜덤 선택
        styles = [
            "감성적인 (비오는 날 창밖을 보며 먹는 느낌)",
            "직설적인 (맛 평가 위주)",
            "이모지 뿜뿜 😋✨",
            "짧고 굵은 (쿨한 말투)",
            "구체적인 맛 표현 (식감, 향)",
            "재주문 의사 강력 어필"
        ]
        style = random.choice(styles)
        
        prompt = f"""
        당신은 배달 앱 헤비유저입니다. 
        아래 상황에 맞춰 **'{style}'** 스타일로 자연스러운 리뷰를 작성해주세요.

        [주문 맥락]
        - 매장: {store_name}
        - 메뉴: {', '.join(menu_list)} (이 중 하나를 콕 집어 언급)
        - 날씨: {weather} (날씨와 음식의 조화 언급)
        - 시간: {ordered_at.strftime('%H시')}
        - 별점: {rating}점

        [작성 가이드]
        - 5점: "인생 맛집", "단골 확정", "사장님 최고" 텐션으로 극찬.
        - 4점: 맛은 좋은데 사소한 아쉬움(양, 가격 등) 살짝 언급.
        - 3점: "그냥 그래요", "평범해요" 금지. 구체적으로 뭐가 아쉬운지 적을 것.
        - 1~2점: 배달 지연, 포장 상태, 식은 음식 등에 대해 확실하게 불만 표출.
        - **"무난하네요", "맛있어요" 같은 뻔한 멘트 절대 금지!** 
        - 50자 이내로 짧게.

        Output JSON: {{ "review_text": "리뷰 내용" }}
        """
        try:
            resp = await genai_generate_text(prompt)
            data = json.loads(resp)
            return data.get("review_text", f"{menu_list[0]} 잘 먹었습니다.")
        except Exception as e:
            return f"{menu_list[0]} 배달 빨라서 좋네요."

async def process_batch(batch_items, store_id):
    """배치 단위로 처리 후 DB 저장"""
    tasks = []
    
    # 1. 리뷰 텍스트 생성 (병렬)
    for item in batch_items:
        # 별점 로직: 1.0~5.0점까지 0.5 단위로 세분화하여 긍정/부정 리뷰 다각화
        rating = random.choices(
            [5.0, 4.5, 4.0, 3.5, 3.0, 2.5, 2.0, 1.5, 1.0],
            weights=[40, 15, 15, 10, 8, 5, 3, 2, 2]
        )[0]
        item['rating'] = rating
        
        task = generate_review_content_with_sem(
            item['store_name'],
            [item['menu_name']],
            item['weather_info'] or "맑음",
            item['ordered_at'],
            rating
        )
        tasks.append(task)
    review_texts = await asyncio.gather(*tasks)
    
    # 2. 임베딩 생성 (병렬 - 세마포어 필요할 수 있으나 임베딩은 빠름)
    # 임베딩도 별도 세마포어 적용 권장이지만 여기선 순차 처리 또는 통으로 묶음
    embedding_tasks = []
    for txt in review_texts:
        embedding_tasks.append(get_embedding(txt))
        
    embeddings = await asyncio.gather(*embedding_tasks)
    
    # 3. DB Insert
    for i, item in enumerate(batch_items):
        review_txt = review_texts[i]
        emb = embeddings[i]
        
        # 리뷰 작성 시간은 주문 후 30분 ~ 12시간 사이 랜덤
        created_at = item['ordered_at'] + timedelta(minutes=random.randint(30, 720))
        
        await execute("""
            INSERT INTO reviews (store_id, menu_id, order_id, rating, review_text, created_at, embedding)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        """, (
            store_id,
            item['menu_id'],
            item['order_id'],
            item['rating'],
            review_txt,
            created_at,
            str(emb) if emb else None
        ))
    
    # print(f"  ✅ {len(batch_items)}개 리뷰 저장 완료 (Store {store_id})")

async def seed_reviews_monthly():
    await init_pool()
    
    print("🧹 기존 리뷰 데이터 전체 삭제 중...")
    await execute("TRUNCATE TABLE reviews CASCADE")

    print("📅 최근 30일 주문 데이터 수집 중...")
    start_date = datetime.now() - timedelta(days=32)
    
    query = """
    SELECT o.order_id, o.store_id, o.menu_id, o.ordered_at, m.menu_name, s.store_name, sd.weather_info
    FROM orders o
    JOIN menus m ON o.menu_id = m.menu_id
    JOIN stores s ON o.store_id = s.store_id
    LEFT JOIN sales_daily sd ON o.store_id = sd.store_id AND DATE(o.ordered_at) = sd.sale_date
    WHERE o.ordered_at >= %s
    ORDER BY o.ordered_at ASC
    """
    
    orders = await fetch_all(query, (start_date,))
    print(f"📦 총 주문 {len(orders)}건 조회됨.")
    
    # Store -> Date 별로 그룹핑
    # 구조: groups[store_id][date_str] = [order_row, ...]
    groups = {}
    for row in orders:
        sid = row['store_id']
        date_key = row['ordered_at'].strftime('%Y-%m-%d')
        
        if sid not in groups:
            groups[sid] = {}
        if date_key not in groups[sid]:
            groups[sid][date_key] = []
        
        groups[sid][date_key].append(row)
        
    total_reviews_generated = 0
    all_target_items = []

    print("🎲 날짜별 리뷰 타겟 선정 중...")
    for sid, date_map in groups.items():
        for date_key, daily_orders in date_map.items():
            # 주문 수 대비 리뷰 수 결정 (최대 10개 또는 주문수의 50%, 최소 1개)
            max_reviews = min(10, len(daily_orders))
            if max_reviews < 1:
                continue
                
            # 1~10개 사이 랜덤 (주문이 적다면 그만큼만)
            num_reviews = random.randint(1, max_reviews)
            
            # 랜덤 샘플링
            targets = random.sample(daily_orders, num_reviews)
            all_target_items.extend(targets)
            
    print(f"🚀 총 {len(all_target_items)}개의 리뷰를 생성합니다. (GenAI 호출 시작)")
    
    # 전체를 배치 크기(예: 20개)로 나누어 처리하여 진행상황 표시
    batch_size = 20
    for i in range(0, len(all_target_items), batch_size):
        batch = all_target_items[i:i+batch_size]
        # store_id가 섞여있으므로 process_batch 내부의 logging은 store_id를 대표로 쓰기 애매함
        # 그냥 함수 인자 store_id는 무시하고 item['store_id'] 사용
        
        # 병렬 처리
        await process_batch(batch, batch[0]['store_id']) # store_id 인자는 로깅용이었으나 일단 넘김
        
        current_count = min(i + batch_size, len(all_target_items))
        print(f"   [{current_count}/{len(all_target_items)}] 처리 완료... ({current_count/len(all_target_items)*100:.1f}%)")
        
    await close_pool()
    print("🎉 모든 리뷰 데이터 생성 완료!")

if __name__ == "__main__":
    if os.name == 'nt':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(seed_reviews_monthly())
