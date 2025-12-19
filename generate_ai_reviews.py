import asyncio
import json
import random
import selectors
from datetime import datetime, date, timedelta
from sqlalchemy import func
from app.core.db import SessionLocal, init_pool, close_pool
from app.store.store_schema import Store
from app.menu.menu_schema import Menu
from app.order.order_schema import Order
from app.review.review_schema import Review
from app.clients.genai import genai_generate_text

# 동시 요청 수를 조절하는 세마포어
MAX_CONCURRENT_REQUESTS = 15
semaphore = asyncio.Semaphore(MAX_CONCURRENT_REQUESTS)

async def generate_and_append_negative_reviews(store_id, store_name, order_date, sample_orders):
    """
    기존 데이터에 '부정적/쓴소리' 리뷰를 추가로 생성
    """
    if not sample_orders:
        return

    async with semaphore:
        order_details = []
        for o in sample_orders:
            order_details.append({
                "id": o.order_id, 
                "menu": o.temp_menu_name,
                "time": o.ordered_at.strftime('%H:%M')
            })

        order_count = len(sample_orders)
        
        # 이번엔 대놓고 '부정적'이거나 '아쉬운' 피드백을 유도하는 프롬프트
        prompt = f"""
        너는 카페 고객이야. 아래 주문 목록({len(order_details)}건)에 대해 각각 '솔직하고 조금 까칠한' 영수증 리뷰를 작성해줘.
        
        [매장: {store_name}, 날짜: {order_date}]

        [작성 가이드라인 - 필독!]
        1. 이번 리뷰들은 평점 1점~3점 사이의 '불만 사항'이나 '아쉬운 점' 위주로 작성하세요.
        2. 구체적인 사유를 들어 비판하세요. 
           예: "커피에서 탄 맛이 너무 나요", "포장이 부실해서 커피가 다 샜어요", "배달이 1시간이나 걸려서 다 식었어요", "직원이 불친절해요" 등.
        3. 모든 리뷰가 최악일 필요는 없지만, 최소한 '아쉬움'이 한두 가지는 섞여 있어야 합니다.
        4. 실제 영수증 리뷰처럼 줄임말이나 약간의 오타를 섞어주면 더 좋습니다.

        주문 목록: {json.dumps(order_details, ensure_ascii=False)}

        응답은 반드시 아래 형식의 JSON 리스트로만 할 것:
        [
            {{"order_id": 1, "rating": 2, "review_text": "내용", "delivery_app": "배민"}},
            ...
        ]
        """
        
        try:
            print(f"� [부정 리뷰 추가중] {store_name} - {order_date} ({len(order_details)}건)")
            ai_response_json = await genai_generate_text(prompt)
            
            if "[" in ai_response_json and "]" in ai_response_json:
                ai_response_json = ai_response_json[ai_response_json.find("["):ai_response_json.rfind("]")+1]
            
            reviews_list = json.loads(ai_response_json)
            
            with SessionLocal() as session:
                for r_data in reviews_list:
                    # 다시 한번 실제 주문 데이터와 매칭
                    target_order = next((o for o in sample_orders if o.order_id == r_data['order_id']), None)
                    if target_order:
                        # 이미 다른 리뷰가 생겼을 수도 있으니 최종 체크 (중복 방지)
                        existing = session.query(Review).filter_by(order_id=target_order.order_id).first()
                        if existing: continue

                        created_at = target_order.ordered_at + timedelta(hours=random.randint(1, 4))
                        new_review = Review(
                            store_id=store_id,
                            order_id=target_order.order_id,
                            menu_id=target_order.menu_id,
                            rating=r_data['rating'],
                            review_text=r_data['review_text'],
                            delivery_app=r_data.get('delivery_app', random.choice(["배달의민족", "쿠팡이츠", "요기요"])),
                            created_at=created_at
                        )
                        session.add(new_review)
                session.commit()
                print(f"✅ [저장 완료] {store_name} ({len(reviews_list)}건 추가됨)")
        except Exception as e:
            print(f"❌ [에러] {store_name} {order_date}: {e}")

async def run_append_generation():
    await init_pool()
    session = SessionLocal()
    
    try:
        print("⚡ 부정적 데이터 추가 엔진 가동 (기존 데이터 유지)")
        
        stores = session.query(Store).all()
        menus = {m.menu_id: m.menu_name for m in session.query(Menu).all()}
        
        tasks = []
        for store in stores:
            for day_offset in range(7):
                target_date = date.today() - timedelta(days=day_offset)
                
                # ★ 중요: 아직 리뷰가 없는 주문들만 골라냄 (중복 방지)
                reviewed_order_ids = session.query(Review.order_id).filter(Review.store_id == store.store_id).all()
                reviewed_order_ids = [r[0] for r in reviewed_order_ids if r[0] is not None]
                
                orders_no_review = session.query(Order).filter(
                    Order.store_id == store.store_id,
                    func.date(Order.ordered_at) == target_date,
                    Order.order_id.not_in(reviewed_order_ids) if reviewed_order_ids else True
                ).all()
                
                if not orders_no_review:
                    continue

                # 남은 주문 중 소량(약 5~10%)만 부정 리뷰로 생성
                sample_size = max(1, int(len(orders_no_review) * 0.1))
                sample_orders = random.sample(orders_no_review, sample_size)
                
                for o in sample_orders:
                    o.temp_menu_name = menus.get(o.menu_id, "인기 메뉴")

                tasks.append(generate_and_append_negative_reviews(
                    store.store_id, store.store_name, str(target_date), sample_orders
                ))

        print(f"⏳ 총 {len(tasks)}개의 묶음에 대해 부정적 리뷰 보충을 시작합니다...")
        await asyncio.gather(*tasks)
        print(f"✨ 쓰디쓴 피드백들이 성공적으로 추가되었습니다!")

    except Exception as e:
        print(f"❌ 프로세스 오류: {e}")
    finally:
        session.close()
        await close_pool()

if __name__ == "__main__":
    # Windows 호환성 패치
    try:
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    except:
        pass
    asyncio.run(run_append_generation())
