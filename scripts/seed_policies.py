import sys
import os
import asyncio
from sqlalchemy import text
from dotenv import load_dotenv
from langchain_openai import OpenAIEmbeddings

# Add project root to sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.db import engine, base, SessionLocal
from app.policy.policy_schema import Policy

load_dotenv()
embeddings_model = OpenAIEmbeddings(model="text-embedding-3-small")

async def get_embedding(text: str):
    try:
        return await embeddings_model.aembed_query(text)
    except Exception as e:
        print(f"⚠️ 임베딩 실패: {e}")
        return None

def init_db():
    print("🔄 Initializing Policy Table...")
    try:
        with engine.connect() as conn:
            # Policy 테이블만 초기화 (CASCADE 조심할 필요 없음, 독립적임)
            conn.execute(text("DROP TABLE IF EXISTS policies CASCADE"))
            conn.commit()
            print("   - Old policies table dropped.")
    except Exception as e:
        print(f"   - Warning during drop: {e}")

    # Create new table (다른 테이블도 같이 create되지만 이미 있으면 패스됨)
    base.metadata.create_all(bind=engine)
    print("✅ Policy table created.")

async def seed_data():
    session = SessionLocal()
    try:
        print("🌱 Seeding Policy Data (30 Items)...")

        policy_items = [
            # --- 인사/복무 (HR & Attendance) - 10개 ---
            {"cat": "인사 규정", "title": "출근 및 근태 관리 규정", "content": "1. 근무 시작 10분 전 매장 도착 및 유니폼 환복 완료. 2. 도착 즉시 포스기 '출근' 버튼 터치. 3. 지각 시 30분 전 매니저에게 유선 연락 (문자/톡 금지). 3회 이상 지각 시 시말서 작성."},
            {"cat": "인사 규정", "title": "휴게 시간 운영 지침", "content": "4시간 근무 시 30분 휴게 시간 부여 (무급). 휴게 중에는 매장 밖 외출 가능하나 유니폼 탈의 필수. 휴게 종료 5분 전 복귀 준비."},
            {"cat": "인사 규정", "title": "연차 유급 휴가 사용", "content": "1년 미만 근속자: 1개월 만근 시 1일 유급휴가 발생. 사용 2주 전 휴가계 제출. 매장 스케줄에 따라 일자 조정 협의 가능."},
            {"cat": "인사 규정", "title": "복장 및 용모 단정 가이드", "content": "상의: 지급된 유니폼(티셔츠), 앞치마 착용. 하의: 검정색 슬랙스류 (반바지, 츄리닝 금지). 신발: 미끄럼 방지 주방화 또는 검정 운동화. 모자 필수 착용."},
            {"cat": "인사 규정", "title": "급여 지급 및 정산 기준", "content": "급여일: 매월 10일 (휴일인 경우 전일 지급). 시급: 최저시급 준수 + 주휴수당 별도 계산. 수습기간 3개월(업무 숙련도 평가 기간)."},
            {"cat": "인사 규정", "title": "퇴사/사직 통보 기간", "content": "퇴사 희망 시 최소 1개월 전 사직서 제출 원칙. 인수인계 기간 필수 준수. 무단 결근 및 연락 두절 시 법적 책임이 따를 수 있음."},
            {"cat": "인사 규정", "title": "초과 근무(OT) 규정", "content": "매장 상황에 따라 연장 근무 발생 시 1.5배 가산 수당 지급. 반드시 점장 승인 하에 진행된 시간만 인정."},
            {"cat": "인사 규정", "title": "직원 할인 혜택", "content": "근무 중 음료 1잔 무료 제공 (일부 고가 메뉴 제외). 본인 구매 시 전 메뉴 30% 할인. 가족/지인 할인 불가. 근무 외 시간 방문 시에도 할인 적용."},
            {"cat": "인사 규정", "title": "병가 및 경조사 휴가", "content": "본인 질병으로 인한 병가 시 진단서 제출 필수. 본인 결혼(5일), 직계가족 조문(3일) 등 경조 휴가는 유급으로 처리."},
            {"cat": "인사 규정", "title": "근무 중 휴대폰 사용 금지", "content": "근무 시간 중 개인 휴대폰 사용 및 소지 금지. 락커룸 보관. 긴급 연락 필요 시 매장 전화 사용 또는 매니저 허가 득후 사용."},

            # --- 위생/안전 (Hygiene & Safety) - 10개 ---
            {"cat": "위생/안전", "title": "보건증 관리 및 갱신", "content": "모든 근로자는 채용 전 보건증 제출 필수. 유효기간 1년 만료 1개월 전 갱신 검사 완료 및 제출. 미갱신 시 근무 불가."},
            {"cat": "위생/안전", "title": "손 씻기 및 개인 위생", "content": "출근 직후, 화장실 사용 후, 쓰레기 취급 후 등 수시로 30초 이상 흐르는 물에 비누 세척. 손 소독제 수시 사용. 손톱 매니큐어/네일아트 금지."},
            {"cat": "위생/안전", "title": "식중독 예방 및 식자재 관리", "content": "교차 오염 방지: 칼/도마 용도별(육류/야채/과일) 구분 사용. 유통기한 경과 식자재 즉시 전량 폐기. 냉장고 온도 기록지 매일 작성."},
            {"cat": "위생/안전", "title": "매장 내 안전사고 대응 (화상)", "content": "화상 발생 시 즉시 흐르는 찬물에 15분 이상 식힘. 화상 연고 도포 후 거즈 보호. 심할 경우 즉시 지정 병원 이송."},
            {"cat": "위생/안전", "title": "미끄럼 방지 및 바닥 관리", "content": "주방 바닥 물기 즉시 제거. '미끄럼 주의' 표지판 설치. 반드시 미끄럼 방지 기능이 있는 작업화 착용."},
            {"cat": "위생/안전", "title": "칼/가위 등 날카로운 도구 취급", "content": "사용 후 즉시 세척하여 거치대 보관. 설거지통에 칼을 담가두지 말 것 (손 베임 사고 원인 1위). 전달 시 손잡이 쪽으로 건넴."},
            {"cat": "위생/안전", "title": "전기 안전 및 화재 예방", "content": "문어발식 콘센트 사용 금지. 퇴근 시 오븐, 머신 전원 차단 확인. 소화기 위치 및 사용법 월 1회 숙지 교육."},
            {"cat": "위생/안전", "title": "유리 파손 시 대처 매뉴얼", "content": "파손 즉시 주변 고객 대피. 맨손으로 파편 수거 절대 금지. 빗자루/진공청소기 사용 후 젖은 걸레로 미세 파편 제거."},
            {"cat": "위생/안전", "title": "식품 알레르기 안내 의무", "content": "고객 문의 시 알레르기 유발 성분표(우유, 견과류, 밀 등) 반드시 확인 후 안내. '아마 없을 거예요' 추측성 답변 금지."},
            {"cat": "위생/안전", "title": "방역 및 해충 방제", "content": "매장 정기 소독(세스코) 월 1회 실시. 해충 발견 시 즉시 포획하지 말고 이동 경로 확인 후 방제 업체 신고."},

            # --- 윤리/보안 (Code & Security) - 10개 ---
            {"cat": "윤리/보안", "title": "개인정보 보호 정책 (CCTV)", "content": "매장 내 CCTV는 방범 및 화재 예방 목적으로만 운영. 영상 열람은 경찰 대동 시에만 가능. 근무자가 임의로 열람/유출 시 형사 처벌."},
            {"cat": "윤리/보안", "title": "고객 개인정보 취급 주의", "content": "포인트 적립을 위한 고객 전화번호는 마케팅 외 용도 사용 금지. 영수증 등 고객 정보가 담긴 종이는 반드시 파쇄 후 폐기."},
            {"cat": "윤리/보안", "title": "현금/시재 관리 및 횡령 금지", "content": "계산 실수 외 고의적인 시재 누락 및 횡령 적발 시 즉시 해고 및 민형사상 조치. 포인트 부정 적립(본인 번호로 적립) 절대 금지."},
            {"cat": "윤리/보안", "title": "매장 비품 및 자산 반출 금지", "content": "매장 소유의 식자재, 비품(휴지, 세제, 컵 등) 무단 반출 금지. 폐기 대상 음식물이라도 매니저 승인 없이 취식/반출 불가."},
            {"cat": "윤리/보안", "title": "사내 성희롱/괴롭힘 예방", "content": "직원 간 언어적/신체적 성희롱 및 폭언 금지. 위반 시 무관용 원칙 적용. 피해 발생 시 핫라인(점장/본사) 신고."},
            {"cat": "윤리/보안", "title": "비밀 유지 서약", "content": "매장의 레시피, 매출액, 고객 정보, 운영 노하우 등 영업 비밀을 경쟁사나 외부에 유출하지 않을 것을 서약함."},
            {"cat": "윤리/보안", "title": "SNS 활동 가이드라인", "content": "유니폼 착용 후 불건전한 행위나 매장 이미지를 훼손하는 영상 촬영 및 SNS 업로드 금지. 고객 몰래 촬영 금지."},
            {"cat": "윤리/보안", "title": "외부인 출입 통제 (주방/카운터)", "content": "관계자 외 주방 및 카운터 내부 출입 절대 금지. 지인 방문 시에도 홀에서만 만남 가능. 배달 기사님은 픽업대 대기 유도."},
            {"cat": "윤리/보안", "title": "분실물 습득 및 횡령 주의", "content": "고객이 두고 간 지갑, 현금, 귀중품 습득 시 사용하거나 가지면 점유이탈물횡령죄 성립. 즉시 cctv 사각지대가 아닌 곳에 보관."},
            {"cat": "윤리/보안", "title": "불법 소프트웨어 설치 금지", "content": "포스기 및 매장 PC에 게임, 불법 다운로드 사이트 접속, 개인 USB 연결 금지. 랜섬웨어 감염 예방 철저."}
        ]

        policies_db = []
        print("🧠 Generating Policy Embeddings...")
        for item in policy_items:
            # Pydantic이 아니라 바로 ORM 객체 매핑
            p = Policy(
                category=item["cat"],
                title=item["title"],
                content=item["content"]
            )
            # 임베딩
            text_to_embed = f"정책: {p.title}\n{p.content}"
            emb = await get_embedding(text_to_embed)
            p.embedding = emb
            
            policies_db.append(p)

        session.add_all(policies_db)
        session.commit()
        
        print(f"✅ Inserted {len(policies_db)} Policies with Embeddings.")
        print("🎉 Policy Seeding Completed!")
        
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
