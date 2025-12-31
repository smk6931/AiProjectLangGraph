import sys
import os
import asyncio
from sqlalchemy import text
from dotenv import load_dotenv
from langchain_openai import OpenAIEmbeddings

# Add project root to sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.db import engine, base, SessionLocal
from app.manual.manual_schema import Manual
# Menu import Removed to prevent accidental modification

load_dotenv()
embeddings_model = OpenAIEmbeddings(model="text-embedding-3-small")

async def get_embedding(text: str):
    try:
        return await embeddings_model.aembed_query(text)
    except Exception as e:
        print(f"⚠️ 임베딩 실패: {e}")
        return None

def init_db():
    print("🔄 Initializing Manuals Table (Only)...")
    try:
        with engine.connect() as conn:
            # Only Drop Manuals
            conn.execute(text("DROP TABLE IF EXISTS manuals CASCADE"))
            conn.commit()
            print("   - Old manuals table dropped. (Menus table is SAFE)")
    except Exception as e:
        print(f"   - Warning during drop: {e}")

    # Create new tables (SQLAlchemy checks existence so it's safe)
    base.metadata.create_all(bind=engine)
    print("✅ Manuals table ready.")

async def seed_data():
    session = SessionLocal()
    try:
        print("🌱 Seeding Data (Manuals - 30 Items)...")

        # 30 Manual Items
        manuals_list = [
            # --- 기기 관리 (Equipment) ---
            {"cat": "기기 관리", "title": "에스프레소 머신 일일 청소 (백플러싱)", "content": "주기: 매일 마감 시.\n방법: 1. 포터필터에 블라인드 바스켓 장착. 2. 전용 세정제 3g 투입. 3. 그룹헤드에 장착 후 추출 버튼 10초 가동, 5초 정지 (5회 반복). 4. 세정제 없이 물로만 동일 과정 5회 반복하여 헹굼."},
            {"cat": "기기 관리", "title": "그라인더 날(Burr) 교체 주기 및 관리", "content": "기준: 원두 500kg 사용 시 또는 6개월 경과 시.\n증상: 분쇄 입도가 불규칙하거나 채널링 발생 시 날 상태 점검 요망."},
            {"cat": "기기 관리", "title": "제빙기 필터 청소 및 소독", "content": "주기: 월 2회 (격주 월요일).\n방법: 1. 제빙기 전원 OFF. 2. 얼음을 모두 비움. 3. 내부 물탱크 및 분사 노즐 분리 세척. 4. 식용 소독제로 내부 닦음. 5. 깨끗한 물로 3회 이상 헹굼."},
            {"cat": "기기 관리", "title": "오븐 예열 및 온도 설정", "content": "사용 전 최소 15분 예열 필수. 베이커리류: 180도, 샌드위치 워밍: 160도 설정. 온도 도달 알림음 확인 후 투입."},
            {"cat": "기기 관리", "title": "식기세척기 세제 교체 방법", "content": "세제 경고음 발생 시: 1. 하단 캐비닛 오픈. 2. 빈 세제통 수거. 3. 새 세제통 캡 제거 후 노즐 삽입. 4. 누수 여부 확인."},
            {"cat": "기기 관리", "title": "냉장고/냉동고 적정 온도 관리", "content": "냉장: 2~4도, 냉동: -18도 이하 유지. 일 2회(오픈, 마감) 온도계 확인 후 기록지에 기입. 이상 온도 발견 시 즉시 매니저 보고."},
            {"cat": "기기 관리", "title": "포스기(POS) 재부팅 절차", "content": "시스템 느려짐 발생 시: 1. 영업 프로그램 종료. 2. 윈도우 종료. 3. 본체 전원 버튼 5초간 누름. 4. 1분 후 재가동. (영업 중 강제 종료 지양)"},
            {"cat": "기기 관리", "title": "정수 필터 교체 주기", "content": "주기: 6개월. 방법: 1. 원수 밸브 잠금. 2. 필터 카트리지 회전 분리. 3. 새 카트리지 장착 후 5분간 물 흘려보내기(플러싱)."},
            {"cat": "기기 관리", "title": "블렌더(믹서기) 칼날 세척", "content": "사용 직후 미온수로 헹굼. 마감 시 분해하여 칼날 사이 이물질 제거. 고무링 분실 주의. 칼날 마모 시 즉시 교체."},
            {"cat": "기기 관리", "title": "쇼케이스 성에 제거", "content": "성에가 1cm 이상 끼면 냉각 효율 저하. 주 1회 물건을 빼고 전원 OFF 후 녹여 제거. 날카로운 도구 사용 금지."},

            # --- 매장 운영 (Operations) ---
            {"cat": "매장 운영", "title": "오픈 준비 체크리스트", "content": "1. 보안 해제 및 환기. 2. 조명/음악 ON. 3. 머신/그라인더 전원 ON. 4. 시재금 준비. 5. 행주 소독 및 비치. 6. 재고(우유, 원두) 채우기."},
            {"cat": "매장 운영", "title": "마감 정산 절차", "content": "1. 포스 마감 정산. 2. 카드 단말기 집계 출력. 3. 현금 시재 확인 (오차 발생 시 사유서). 4. 당일 매출 장부 기록. 5. 현금 금고 보관."},
            {"cat": "매장 운영", "title": "재고 발주 가이드", "content": "발주 시간: 매일 오후 2시 마감. 품목별 적정 재고량(Par Level) 확인 후 부족분 신청. 주말 대비 금요일은 1.5배 발주."},
            {"cat": "매장 운영", "title": "유통기한 관리 원칙 (FIFO)", "content": "선입선출(First In First Out) 원칙 준수. 신규 입고 상품은 뒤쪽에 진열. 개봉한 식자재는 반드시 '개봉일/폐기일' 라벨 부착."},
            {"cat": "매장 운영", "title": "음악(BGM) 선곡 가이드", "content": "오전: 활기차고 밝은 재즈/팝. 오후(피크): 템포가 빠른 음악. 저녁: 차분한 어쿠스틱/Lofi. 가사 없는 연주곡 권장."},
            {"cat": "매장 운영", "title": "화장실 청소 및 점검", "content": "점검 주기: 2시간 간격. 체크사항: 휴지/핸드타월 보충, 세면대 물기 제거, 휴지통 비우기, 방향제 확인."},
            {"cat": "매장 운영", "title": "냉난방기 운영 기준", "content": "여름: 실내 24~25도. 겨울: 실내 20~22도. 손님 밀집도에 따라 유동적 조절. 마감 시 반드시 전원 OFF 확인."},
            {"cat": "매장 운영", "title": "분리수거 및 쓰레기 처리", "content": "일반쓰레기: 종량제 봉투. 재활용: 등급별 분류 후 투명 봉투. 음식물: 물기 제거 후 전용 용기. 박스는 테이프 제거 후 압착 배출."},
            {"cat": "매장 운영", "title": "소화기 위치 및 사용법", "content": "위치: 카운터 하단 1개, 주방 입구 1개. 사용법: 1. 안전핀 뽑기. 2. 노즐 화재 방향 조준. 3. 손잡이 움켜쥐기. (월 1회 압력게이지 점검)"},
            {"cat": "매장 운영", "title": "배달 앱 주문 접수 및 거절", "content": "접수: 주문 알림 시 1분 내 수락. 조리 예상 시간 여유있게 설정. 품절 메뉴 포함 시 고객 통화 후 부분 취소 또는 대체 안내."},

            # --- CS 및 고객 응대 (Customer Service) ---
            {"cat": "CS 응대", "title": "음료 컴플레인 처리 (이물질)", "content": "1. 즉시 정중히 사과. 2. 음료 회수 및 확인. 3. 즉시 재제조 또는 전액 환불. 4. 고객 안심 차원에서 쿠폰 증정."},
            {"cat": "CS 응대", "title": "음료 맛 불만족 대응", "content": "고객 입맛 차이일 수 있으나 즉시 교환 제안. '연하게/진하게' 등 상세 요구사항 재확인 후 제조. 논쟁 금지."},
            {"cat": "CS 응대", "title": "매장 내 분실물 습득 시", "content": "1. 습득 시간, 장소, 물품 특징 기록(사진 촬영). 2. 포스기 '분실물' 탭에 등록. 3. 1주일 보관 후 찾아가지 않으면 경찰서 인계."},
            {"cat": "CS 응대", "title": "진동벨 분실 예방", "content": "음료 제공 시 진동벨 회수 필수 확인. 바쁠 때 회수 누락 주의. 마감 시 진동벨 개수 총점검(총 20개)."},
            {"cat": "CS 응대", "title": "노키즈존/펫티켓 안내 가이드", "content": "원칙적으로 키즈/반려동물 동반 가능. 단, 다른 고객에게 방해될 경우(소음, 뛰어다님) 정중하게 제지 및 케어 요청."},
            {"cat": "CS 응대", "title": "단체 주문(10잔 이상) 응대", "content": "대기 시간 길어짐을 사전 안내. 캐리어 필요 여부 확인. 필요 시 레시피 간소화(통일) 유도 정중히 제안."},
            {"cat": "CS 응대", "title": "영수증 재발행 및 주차 등록", "content": "영수증: 결제 시간 또는 승인번호로 이전 내역 조회 후 재출력. 주차: 차량번호 뒷 4자리 확인 후 1시간 무료 적용 (중복 불가)."},
            {"cat": "CS 응대", "title": "Wi-Fi 연결 문의", "content": "ID: HappyCafe_5G / PW: happy1234!! 영수증 하단 및 픽업대 와이파이 안내판에 기재되어 있음을 안내."},
            {"cat": "CS 응대", "title": "외부 음식 반입 규정", "content": "원칙적 금지. 이유식, 환자식, 생일 케이크(취식 불가, 초만 부는 경우 허용)는 예외적으로 허용."},
            {"cat": "CS 응대", "title": "라스트 오더(Last Order) 안내", "content": "마감 30분 전 주문 마감. 매장 이용 고객에게는 마감 10분 전까지 정리 부탁 정중히 멘트. 포장은 마감 직전까지 가능."}
        ]

        manuals_db = []
        print("🧠 Generating Manual Embeddings...")
        for item in manuals_list:
            m = Manual(
                category=item["cat"],
                title=item["title"],
                content=item["content"]
            )
            # 임베딩 생성 (비동기)
            text_to_embed = f"매뉴얼: {m.title}\n{m.content}"
            emb = await get_embedding(text_to_embed)
            m.embedding = emb
            manuals_db.append(m)

        session.add_all(manuals_db)
        
        session.commit()
        print(f"✅ Inserted {len(manuals_db)} Manuals")
        print("🎉 Manual Seeding Completed Successfully!")
        
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
