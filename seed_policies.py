import asyncio
import os
from dotenv import load_dotenv

# .env 로드 (가장 먼저)
load_dotenv()

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import text
from langchain_openai import OpenAIEmbeddings

# Circular Import 방지를 위해 db 모듈을 먼저 로드
from app.core.db import database_url
from app.policy.policy_schema import Policy

# 비동기 엔진 생성
engine = create_async_engine(database_url.replace("postgresql://", "postgresql+asyncpg://"))
AsyncSessionLocal = sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)

# 임베딩 모델
embeddings_model = OpenAIEmbeddings(model="text-embedding-3-small")

# 정책 데이터 (총 22개 - 기존 12개 + 신규 10개)
POLICY_DATA = [
     # 1. 복장 및 용모 규정
    {
        "category": "복장 규정",
        "title": "유니폼 및 용모 단정 가이드",
        "content": "모든 근무자는 본사 지정 유니폼(상의, 앞치마, 모자)을 착용해야 합니다. \n1. 유니폼은 항상 청결하게 유지하며, 구겨짐이 없어야 합니다.\n2. 머리카락은 모자 밖으로 나오지 않도록 단정하게 정리합니다(긴 머리는 묶을 것).\n3. 귀걸이, 목걸이 등 과도한 액세서리 착용은 금지됩니다(결혼반지 제외).\n4. 네일아트는 허용되지 않으며, 손톱은 짧게 관리해야 합니다."
    },
    {
        "category": "복장 규정",
        "title": "근무화 및 개인 위생",
        "content": "1. 근무화는 미끄럼 방지 기능이 있는 검정색 단화나 운동화를 착용해야 합니다(슬리퍼, 샌들 절대 금지).\n2. 근무 시작 전 손 세정제와 소독제를 사용하여 30초 이상 손을 씻어야 합니다.\n3. 근무 중 마스크 착용은 방역 지침에 따르되, 조리 시에는 투명 마스크 또는 위생 마스크 착용을 권장합니다."
    },

    # 2. 근태 및 운영 규정
    {
        "category": "근태 규정",
        "title": "출퇴근 및 지각 관리",
        "content": "1. 근무 시작 10분 전 매장에 도착하여 유니폼 착용 및 근무 준비를 완료해야 합니다.\n2. 지각 시 점장에게 즉시 보고해야 하며, 3회 이상 지각 시 시말서를 제출해야 합니다.\n3. 무단 결근은 즉시 계약 해지 사유가 될 수 있으며, 사전에 대체 근무자를 확보해야 합니다."
    },
    {
        "category": "운영 규정",
        "title": "매장 오픈 및 마감 절차",
        "content": "1. [오픈] 포스기 부팅, 시재금 확인, 에스프레소 머신 예열 및 테스트 추출(크레마 확인).\n2. [마감] 마감 30분 전부터 라스트 오더 안내, 에스프레소 머신 약품 청소(백플러싱), 시재 정산 및 금고 보관.\n3. 쓰레기 분리수거 및 음식물 쓰레기 처리는 당일 마감을 원칙으로 합니다."
    },

    # 3. 위생 및 안전 관리
    {
        "category": "위생 관리",
        "title": "본사 위생 점검 및 패널티",
        "content": "본사 QSC(Quality, Service, Cleanliness) 팀은 월 1회 불시 점검을 실시합니다.\n1. 위생 등급 C등급 이하 시 1차 경고 및 재교육.\n2. 2회 연속 C등급 이하 시 해당 지점 영업 정지 3일 및 개선 명령.\n3. 유통기한 경과 식자재 사용 적발 시 즉시 계약 해지 및 법적 조치가 취해질 수 있습니다."
    },
    {
        "category": "안전 관리",
        "title": "화재 및 응급 상황 대응",
        "content": "1. 화재 발생 시 즉시 '불이야'를 외치고 고객을 대피시킨 후 119에 신고합니다.\n2. 소화기는 조리 공간과 홀에 각 1개 이상 비치해야 하며, 매월 압력을 점검합니다.\n3. 화상 사고 발생 시 즉시 흐르는 찬물에 15분 이상 식히고, 구급상자의 화상 연고를 도포합니다."
    },

    # 4. 고객 응대 (CS)
    {
        "category": "CS 규정",
        "title": "고객 클레임 및 환불 처리 기준",
        "content": "1. 음료 제조 실수(이물질, 메뉴 오제조) 시 즉시 사과 후 재제조 및 환불을 원칙으로 합니다.\n2. 고객의 단순 변심이나 '맛이 없다'는 주관적 불만은 원칙적으로 환불 불가하나, 점장 재량하에 1회에 한해 교환 가능합니다.\n3. 배달 앱 리뷰 악성 댓글 발생 시 본사 CS팀에 보고하여 대응 가이드를 받으십시오."
    },
    {
        "category": "CS 규정",
        "title": "진상 고객(악성 민원) 대응 매뉴얼",
        "content": "1. 욕설, 고성, 난동 등 업무 방해 행위 시 즉시 녹음을 고지하고 녹음을 시작하십시오.\n2. 3회 이상 경고에도 중단하지 않을 경우 경찰(112)에 신고하고 퇴거를 요청하십시오.\n3. 절대 고객과 언쟁하거나 감정적으로 대응하지 말고, '규정상 어렵습니다'라고 단호하게 안내하십시오."
    },
    
    # 5. 계약 및 페널티
    {
        "category": "계약 규정",
        "title": "경고 누적 및 계약 해지 사유",
        "content": "다음의 경우 본사는 가맹 계약을 해지할 수 있습니다.\n1. 월 매출 로열티 2개월 연속 미납.\n2. 본사 사입 필수 식자재(원두, 소스 등) 외 타사 제품 사용 적발 시.\n3. 브랜드 이미지를 심각하게 훼손하는 행위(언론 보도 등)."
    },
    {
        "category": "계약 규정",
        "title": "영업 시간 준수 의무",
        "content": "1. 본사와 협의된 영업 시간(예: 08:00 ~ 22:00)을 준수해야 합니다.\n2. 개인 사정으로 인한 임시 휴무는 최소 3일 전 본사 승인을 받아야 합니다(긴급 상황 제외).\n3. 무단 휴무 적발 시 일 위약금 50만원이 부과됩니다."
    },
    
    # 6. 기타 (재고/보안)
    {
        "category": "재고 관리",
        "title": "발주 및 반품 규정",
        "content": "1. 발주는 매일 오전 10시까지 전산 시스템(SCM)을 통해 마감됩니다.\n2. 배송된 물품 검수는 당일 배송 기사 입회 하에 진행하며, 파손/누락 시 현장에서 즉시 반품 접수해야 합니다.\n3. 단순 오발주로 인한 반품은 반품 배송비(박스당 5,000원)가 청구됩니다."
    },
    {
        "category": "보안 규정",
        "title": "CCTV 및 매장 보안",
        "content": "1. 매장 내 CCTV는 24시간 녹화되어야 하며, 최소 30일간 영상을 보관해야 합니다.\n2. POS 비밀번호는 매월 변경하며, 타인과 공유하지 않습니다.\n3. 매장 마감 시 반드시 보안 시스템(세콤/캡스)을 작동시키고 출입문을 잠가야 합니다."
    },

    # === [NEW] 추가된 정책 데이터 10개 ===
    # 7. 마케팅 및 프로모션
    {
        "category": "마케팅 정책",
        "title": "전단지 배포 및 현수막 게시 규정",
        "content": "1. 모든 오프라인 홍보물(전단지, 배너)은 본사 디자인실의 승인을 받아야 합니다(CI 준수).\n2. 지정된 구역 외에 무단으로 전단지를 배포하여 민원이 발생할 경우, 과태료는 가맹점이 전액 부담합니다.\n3. 현수막은 지자체 신고 후 지정 게시대에만 설치해야 합니다."
    },
    {
        "category": "마케팅 정책",
        "title": "SNS 채널 운영 가이드",
        "content": "1. 지점별 인스타그램/유튜브 운영은 권장 사항입니다.\n2. 단, 본사 브랜드 이미지를 훼손하는 콘텐츠(정치적 발언, 비속어 등) 게시 시 삭제 요청 및 경고 조치됩니다.\n3. 해시태그에 필수 키워드(#브랜드명, #메뉴명)를 포함해야 합니다."
    },
    {
        "category": "마케팅 정책",
        "title": "쿠폰 및 포인트 적립 정책",
        "content": "1. 스탬프 10개 적립 시 아메리카노 1잔 무료 제공(전 지점 교차 사용 불가).\n2. 무료 음료 비용은 가맹점이 100% 부담하나, 시즌 프로모션 쿠폰은 본사가 50% 지원합니다.\n3. 포인트 유효 기간은 적립일로부터 1년입니다."
    },

    # 8. 시설 및 인테리어
    {
        "category": "시설 규정",
        "title": "매장 인테리어 리뉴얼 기준",
        "content": "1. 가맹 계약 후 5년 도래 시 환경 개선(부분 리뉴얼)을 권장합니다.\n2. 본사 승인 없이 매장 구조를 변경하거나 사설 업체를 통한 인테리어 공사는 금지됩니다.\n3. 간판 조명이 나간 경우 48시간 이내에 보수해야 합니다."
    },
    {
        "category": "시설 규정",
        "title": "매장 음악(BGM) 저작권 준수",
        "content": "1. 매장에서 재생하는 음악은 저작권료 납부 대상입니다 (멜론, 벅스 개인 계정 사용 불가).\n2. 본사가 계약한 매장 음악 서비스를 이용하거나, 저작권협회에 공연권료를 별도 납부해야 합니다.\n3. 위반 시 발생하는 법적 책임은 점주에게 있습니다."
    },

    # 9. 행정 및 법적 의무
    {
        "category": "행정 규정",
        "title": "보건증 갱신 및 위생 교육",
        "content": "1. 점주 및 모든 아르바이트생은 근무 시작 전 보건증을 발급받아야 합니다.\n2. 보건증 유효 기간은 1년이며, 만료 전 갱신해야 합니다. (미갱신 적발 시 과태료)\n3. 점주는 매년 식품위생교육(온라인)을 반드시 이수해야 합니다."
    },
    {
        "category": "행정 규정",
        "title": "화재 보험 가입 의무",
        "content": "1. 모든 가맹점은 '화재 배상 책임 보험'과 '재난 배상 책임 보험'에 가입해야 합니다.\n2. 보험 증권 사본을 매년 갱신 시 본사 담당자에게 제출해야 합니다.\n3. 미가입으로 인한 사고 발생 시 본사는 책임을 지지 않습니다."
    },

    # 10. 본사 지원 및 교육
    {
        "category": "지원 정책",
        "title": "슈퍼바이저(SV) 방문 및 지원",
        "content": "1. 담당 SV는 월 2회 매장을 정기 방문하여 QSC 점검 및 매출 상담을 진행합니다.\n2. 긴급 상황(기기 고장, 클레임) 발생 시 핫라인으로 연락하면 당일 또는 익일 방문 지원합니다."
    },
    {
        "category": "지원 정책",
        "title": "신메뉴 출시 및 교육",
        "content": "1. 본사는 분기별(3개월) 1회 신메뉴를 출시합니다.\n2. 신메뉴 레시피 영상은 인트라넷을 통해 제공되며, 점주는 출시 3일 전까지 직원 교육을 완료해야 합니다.\n3. 신메뉴 홍보물(포스터)은 본사에서 무상 지원합니다."
    },

    # 11. 양도양수 및 폐업
    {
        "category": "계약 변동",
        "title": "매장 양도양수 및 폐업 절차",
        "content": "1. [양도] 양수 희망자가 본사 면접 및 교육을 통과해야 승인됩니다. 양도비(가맹비) 50%가 부과됩니다.\n2. [폐업] 폐업 1개월 전 서면으로 통보해야 합니다.\n3. 폐업 시 간판 및 상표물은 즉시 철거해야 하며, 인테리어 원상 복구 의무가 있습니다."
    }
]

async def seed_policies():
    print("🚀 정책/규정 데이터 시딩 및 임베딩 시작...")
    
    async with AsyncSessionLocal() as session:
        # 1. 테이블 생성 (직접 쿼리 실행) - alembic 대용
        print("🛠️ policies 테이블 생성 중...")
        await session.execute(text("""
            CREATE TABLE IF NOT EXISTS policies (
                policy_id SERIAL PRIMARY KEY,
                category VARCHAR(50) NOT NULL,
                title VARCHAR(200) NOT NULL,
                content TEXT NOT NULL,
                embedding Vector(1536),
                created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                updated_at TIMESTAMP WITH TIME ZONE
            );
        """))
        # 벡터 인덱스 생성 (속도 향상)
        await session.execute(text("CREATE INDEX IF NOT EXISTS policy_embedding_idx ON policies USING ivfflat (embedding vector_cosine_ops);"))
        await session.commit()
    
        # 2. 기존 데이터 삭제 (중복 방지)
        await session.execute(text("TRUNCATE TABLE policies RESTART IDENTITY;"))
        
        # 3. 데이터 삽입 & 임베딩
        count = 0
        for item in POLICY_DATA:
            # 임베딩 생성
            text_to_embed = f"{item['title']}\n{item['content']}"
            vector = await embeddings_model.aembed_query(text_to_embed)
            
            policy = Policy(
                category=item["category"],
                title=item["title"],
                content=item["content"],
                embedding=vector
            )
            session.add(policy)
            count += 1
            print(f"✅ [Policy] 추가: {item['title']}")
            
        await session.commit()
        print(f"🎉 총 {count}개의 정책/규정 데이터가 성공적으로 저장되었습니다.")

if __name__ == "__main__":
    asyncio.run(seed_policies())
